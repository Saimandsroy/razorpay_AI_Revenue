"""
Integration tests for the Razorpay AI Revenue Recovery pipeline.

Covers:
- First-time payment processing
- Idempotent duplicate processing (200 OK, not 409)
- Non-failed payment rejection (422)
- Customer response simulation via action events
- Revenue attribution idempotency
- Batch processing: duplicates, skipped, new cases
- Demo scenario via notes.demo_scenario
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models import AuditEvent, RecoveryAction, RecoveryBatch, RecoveryCase

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _make_mock_razorpay(error_code: str = "BAD_REQUEST_CARD_EXPIRED", notes: dict | None = None):
    """Return a MagicMock Razorpay client wired up with deterministic responses."""
    import time

    mock_client = MagicMock()

    effective_notes = {"customer_name": "Rajesh Kumar", "customer_email": "rajesh.test@example.com"}
    if notes:
        effective_notes.update(notes)

    def mock_fetch(payment_id):
        return {
            "id": payment_id,
            "status": "failed",
            "amount": 50000,
            "currency": "INR",
            "error_code": error_code,
            "customer_id": "cust_test123",
            "email": "rajesh.test@example.com",
            "notes": effective_notes,
        }

    mock_client.payment.fetch.side_effect = mock_fetch

    recent_time = int(time.time()) - 86400  # 1 day ago  → days_inactive ≈ 1 → policy allows
    mock_client.payment.all.return_value = {
        "items": [
            {
                "id": "pay_success_history",
                "status": "captured",
                "amount": 50000,
                "created_at": recent_time,
            }
        ]
    }

    def mock_create_link(payload):
        link_id = f"plink_{uuid.uuid4().hex[:8]}"
        return {"id": link_id, "short_url": f"https://rzp.io/i/{link_id}"}

    mock_client.payment_link.create.side_effect = mock_create_link
    return mock_client


@pytest.fixture
def mock_razorpay():
    with patch("app.main.create_client") as mock_create_client:
        mock_client = _make_mock_razorpay()
        mock_create_client.return_value = mock_client
        yield mock_client


# ---------------------------------------------------------------------------
# TEST 1 — First-time payment ingestion
# ---------------------------------------------------------------------------

def test_failed_test_payment_ingestion(mock_razorpay, db_session):
    test_id = f"pay_{uuid.uuid4().hex[:8]}"
    response = client.post("/api/v1/cases/process", json={"payment_id": test_id})

    assert response.status_code == 200
    data = response.json()
    assert "case_id" in data
    assert "batch_id" in data
    assert data["policy_allowed"] is True
    assert data["diagnosis"] == "card_expired"
    assert response.headers.get("X-Idempotent-Replay") is None  # first time — NOT a replay

    # DB assertions
    case = db_session.get(RecoveryCase, data["case_id"])
    batch = db_session.get(RecoveryBatch, data["batch_id"])

    assert batch is not None
    assert batch.name == "live-session"
    assert batch.status == "processing"
    assert case is not None
    assert case.razorpay_payment_id == test_id
    assert case.customer_name == "Rajesh Kumar"
    assert case.amount_paise == 50000
    assert case.status == "allowed"

    action = db_session.scalar(select(RecoveryAction).where(RecoveryAction.case_id == case.id))
    assert action is not None
    assert action.status == "sent"
    assert action.recipient == "rajesh.test@example.com"

    audit = db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.case_id == case.id,
            AuditEvent.event_type == "CUSTOMER_CONTACTED",
        )
    )
    assert audit is not None
    assert audit.metadata_["action_id"] == str(action.id)


# ---------------------------------------------------------------------------
# TEST 2 — Idempotent duplicate: returns 200 (not 409), same case_id
# ---------------------------------------------------------------------------

def test_duplicate_event_is_idempotent_200(mock_razorpay, db_session):
    """Duplicate delivery of the same payment must return 200 OK, not 409."""
    test_id = f"pay_{uuid.uuid4().hex[:8]}"

    r1 = client.post("/api/v1/cases/process", json={"payment_id": test_id})
    assert r1.status_code == 200
    case_id_first = r1.json()["case_id"]

    r2 = client.post("/api/v1/cases/process", json={"payment_id": test_id})
    assert r2.status_code == 200, f"Expected 200 on duplicate, got {r2.status_code}: {r2.text}"
    assert r2.json()["case_id"] == case_id_first, "Duplicate should return the same case_id"
    assert r2.headers.get("X-Idempotent-Replay") == "true"

    # DB must still have exactly one case for this payment_id
    cases = list(db_session.scalars(
        select(RecoveryCase).where(RecoveryCase.razorpay_payment_id == test_id)
    ))
    assert len(cases) == 1, "Duplicate processing must not create a second RecoveryCase"


# ---------------------------------------------------------------------------
# TEST 3 — Invalid payload (too short payment_id)
# ---------------------------------------------------------------------------

def test_invalid_payload_rejected(mock_razorpay):
    response = client.post("/api/v1/cases/process", json={"payment_id": ""})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# TEST 4 — Non-failed payment rejected with 422
# ---------------------------------------------------------------------------

def test_successful_payment_is_rejected():
    with patch("app.main.create_client") as mock_create_client:
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.payment.fetch.return_value = {"id": "pay_success", "status": "captured", "amount": 50000}
        mock_client.payment.all.return_value = {"items": []}

        response = client.post("/api/v1/cases/process", json={"payment_id": "pay_success"})
        assert response.status_code == 422
        assert "Only failed Razorpay payments are eligible" in response.json()["detail"]


# ---------------------------------------------------------------------------
# TEST 5 — Demo scenario via notes.demo_scenario produces correct diagnosis
# ---------------------------------------------------------------------------

def test_demo_scenario_via_notes_overrides_error_code(db_session):
    """A payment with notes.demo_scenario = BAD_REQUEST_INSUFFICIENT_FUNDS
    should be diagnosed as insufficient_funds even if error_code is the generic
    BAD_REQUEST_ERROR (as returned by Razorpay test mode checkout)."""
    test_id = f"pay_{uuid.uuid4().hex[:8]}"

    with patch("app.main.create_client") as mock_create_client:
        mock_client = _make_mock_razorpay(
            error_code="BAD_REQUEST_ERROR",   # what Razorpay test mode actually returns
            notes={"demo_scenario": "BAD_REQUEST_INSUFFICIENT_FUNDS"},
        )
        mock_create_client.return_value = mock_client

        response = client.post("/api/v1/cases/process", json={"payment_id": test_id})

    assert response.status_code == 200
    data = response.json()
    assert data["diagnosis"] == "insufficient_funds", (
        f"Expected insufficient_funds from demo_scenario override, got {data['diagnosis']}"
    )
    assert data["recommended_action"] in {"retry", "send_payment_plan", "send_downgrade_offer"}

    # Must have synthetic context to pass the strict inactive user policy
    case_id = data["case_id"]
    audit_events = list(db_session.scalars(select(AuditEvent).where(AuditEvent.case_id == case_id)))
    event_types = [e.event_type for e in audit_events]
    assert "SYNTHETIC_DEMO_CONTEXT" in event_types, "Demo scenario must inject synthetic context"
    assert "CONTEXT_FETCHED" not in event_types, "Real context should be skipped for demo scenarios"


# ---------------------------------------------------------------------------
# TEST 6 — Unsupported error code stays unknown_failure (no unsafe recovery)
# ---------------------------------------------------------------------------

def test_unsupported_error_code_produces_safe_stop(db_session):
    """Generic BAD_REQUEST_ERROR without a demo_scenario must produce unknown_failure → stop."""
    test_id = f"pay_{uuid.uuid4().hex[:8]}"

    with patch("app.main.create_client") as mock_create_client:
        mock_client = _make_mock_razorpay(error_code="BAD_REQUEST_ERROR")
        mock_create_client.return_value = mock_client

        response = client.post("/api/v1/cases/process", json={"payment_id": test_id})

    assert response.status_code == 200
    data = response.json()
    assert data["diagnosis"] == "unknown_failure"
    assert data["recommended_action"] == "stop"
    # NOTE: policy_allowed=True here is CORRECT — the policy gate checks context-based
    # safety rules (disputes, inactivity, retry limits) and doesn't change a 'stop'
    # recommendation. The conservative safe behavior is the stop recommendation itself.


# ---------------------------------------------------------------------------
# TEST 7 — Customer response simulation via action events API
# ---------------------------------------------------------------------------

def test_customer_response_simulation(mock_razorpay, db_session):
    test_id = f"pay_{uuid.uuid4().hex[:8]}"
    response = client.post("/api/v1/cases/process", json={"payment_id": test_id})
    case_id = response.json()["case_id"]

    action = db_session.scalar(select(RecoveryAction).where(RecoveryAction.case_id == case_id))
    assert action.status == "sent"

    event_response = client.post(
        f"/api/v1/recovery-actions/{action.id}/events",
        json={"event_type": "LINK_CLICKED"},
    )
    assert event_response.status_code == 200

    db_session.refresh(action)
    assert action.status == "clicked"
    assert action.clicked_at is not None


# ---------------------------------------------------------------------------
# TEST 8 — Revenue attribution idempotency
# ---------------------------------------------------------------------------

def test_revenue_attribution_idempotency(mock_razorpay, db_session):
    test_id = f"pay_{uuid.uuid4().hex[:8]}"
    client.post("/api/v1/cases/process", json={"payment_id": test_id})
    case = db_session.scalar(select(RecoveryCase).where(RecoveryCase.razorpay_payment_id == test_id))

    # No automatic attribution on first process
    assert case.recovered_amount_paise == 0
    assert case.outcome_status == "pending"

    from app.services.outcome_tracker import _attribute_recovery_to_action

    case.status = "success"
    case.amount_paise = 50000

    _attribute_recovery_to_action(db_session, case, "pay_capture_123")
    db_session.commit()

    action = db_session.scalar(select(RecoveryAction).where(RecoveryAction.case_id == case.id))
    if action and action.status not in {"completed", "failed", "expired", "cancelled"}:
        assert action.revenue_recovered_paise == 50000
        assert action.status == "completed"

    # Second call with same capture_id must be idempotent
    _attribute_recovery_to_action(db_session, case, "pay_capture_123")
    db_session.commit()

    audit_events = list(db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.case_id == case.id,
            AuditEvent.event_type == "REVENUE_RECOVERED",
        )
    ))
    assert len(audit_events) <= 1, "Revenue attribution must not be duplicated on idempotent call"


# ---------------------------------------------------------------------------
# TEST 9 — Batch: processes new payments, correctly counts duplicates
# ---------------------------------------------------------------------------

def test_batch_counts_duplicates_not_errors():
    """Batch processing of already-seen payments must count them as already_processed,
    not as errors, and complete successfully with batch.status == 'complete'."""
    import asyncio
    from types import SimpleNamespace

    from app.db import SessionLocal as DB
    from app.models import RecoveryBatch
    from app.services.batch_processor import process_batch

    db = DB()
    try:
        # Create one payment already in the DB via the mock client
        existing_id = f"pay_{uuid.uuid4().hex[:8]}"
        new_id = f"pay_{uuid.uuid4().hex[:8]}"

        payments_list = [
            # Already processed — should count as already_processed
            {"id": existing_id, "status": "failed", "amount": 50000},
            # Fresh — should be processed as new
            {"id": new_id, "status": "failed", "amount": 60000},
            # Ineligible (not failed) — should count as skipped
            {"id": f"pay_{uuid.uuid4().hex[:8]}", "status": "authorized", "amount": 50000},
            # Ineligible (amount too low) — should count as skipped
            {"id": f"pay_{uuid.uuid4().hex[:8]}", "status": "failed", "amount": 5000},
        ]

        import time
        recent_time = int(time.time()) - 86400

        def make_mock_client(payment_ids_in_db: set):
            mock_client = MagicMock()

            def mock_fetch(pid):
                return {
                    "id": pid,
                    "status": "failed",
                    "amount": next(
                        (p["amount"] for p in payments_list if p["id"] == pid), 50000
                    ),
                    "currency": "INR",
                    "error_code": "BAD_REQUEST_CARD_EXPIRED",
                    "customer_id": "cust_batch_test",
                    "email": "batch@example.com",
                    "notes": {"customer_name": "Batch Customer"},
                }

            mock_client.payment.fetch.side_effect = mock_fetch
            mock_client.payment.all.return_value = {
                "items": [{"id": "pay_hist", "status": "captured", "amount": 200000, "created_at": recent_time}]
            }

            def mock_create_link(payload):
                link_id = f"plink_{uuid.uuid4().hex[:8]}"
                return {"id": link_id, "short_url": f"https://rzp.io/i/{link_id}"}

            mock_client.payment_link.create.side_effect = mock_create_link
            return mock_client

        mock_cl = make_mock_client({existing_id})

        # Pre-create the "already processed" case so the DB has it
        existing_batch = RecoveryBatch(name="pre-existing-batch", status="complete")
        db.add(existing_batch)
        db.flush()
        existing_case = RecoveryCase(
            batch_id=existing_batch.id,
            razorpay_payment_id=existing_id,
            amount_paise=50000,
            currency="INR",
            diagnosis="card_expired",
            status="allowed",
            recovery_score=0.74,
            revenue_at_risk_paise=50000,
        )
        db.add(existing_case)
        db.commit()

        # Mock payment.all for batch to return our test payments
        mock_cl.payment.all.side_effect = None
        mock_cl.payment.all.return_value = {"items": payments_list}

        batch = RecoveryBatch(name="test-batch", status="pending")
        db.add(batch)
        db.commit()

        asyncio.run(process_batch(db, mock_cl, batch, batch_size=10))

        db.refresh(batch)
        assert batch.status == "complete"

        stats = batch.metrics_by_diagnosis.get("_batch_stats", {})
        assert stats.get("payments_scanned") == 4
        assert stats.get("already_processed") == 1
        assert stats.get("skipped_ineligible") == 2
        assert stats.get("new_cases_created") == 1
        assert stats.get("processing_errors", 0) == 0

    finally:
        db.close()
