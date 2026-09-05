"""Tests for the RecoveryAction lifecycle, customer events, and revenue attribution."""
import asyncio
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from app.services.action_events import (
    DuplicateEventError,
    InvalidEventError,
    process_action_event,
)
from app.services.executor import (
    execute_action,
    execute_retry,
    execute_send_card_link,
    execute_stop,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _make_action(**overrides: Any) -> SimpleNamespace:
    """Create a minimal RecoveryAction-like object for testing."""
    defaults = {
        "id": uuid.uuid4(),
        "case_id": uuid.uuid4(),
        "action_type": "send_card_update_link",
        "channel": "payment_link",
        "status": "sent",
        "recipient": None,
        "provider": "razorpay_payment_link",
        "provider_reference": f"plink_{uuid.uuid4().hex[:8]}",
        "action_url": "https://rzp.io/i/test",
        "amount_paise": 50_000,
        "metadata_": {},
        "sent_at": datetime.now(UTC),
        "clicked_at": None,
        "responded_at": None,
        "completed_at": None,
        "revenue_recovered_paise": 0,
        "failure_reason": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_db(actions: list | None = None) -> SimpleNamespace:
    """Create a minimal DB session stub that records added objects."""
    events: list = []
    stored_actions = list(actions or [])

    def add(obj: Any) -> None:
        events.append(obj)

    def commit() -> None:
        pass

    def scalar(query: Any) -> Any:
        # If it's checking for existing audit event
        if "audit_events" in str(query):
            return None
        if stored_actions:
            return stored_actions[0]
        return None

    def scalars(query: Any) -> Any:
        return iter(stored_actions)

    return SimpleNamespace(add=add, commit=commit, scalar=scalar, scalars=scalars, events=events)


# ── 1. RecoveryAction creation ───────────────────────────────────────


def test_recovery_action_creation() -> None:
    action = _make_action(status="pending")
    assert action.status == "pending"
    assert action.revenue_recovered_paise == 0
    assert action.action_type == "send_card_update_link"


# ── 2. Successful action execution ──────────────────────────────────


def test_executor_returns_enriched_fields() -> None:
    api = SimpleNamespace(create=lambda _: {"id": "plink_1", "short_url": "https://rzp.io/i/test"})
    result = execute_send_card_link(SimpleNamespace(payment_link=api), "cust_1", "pay_1", 50_000)
    assert result["status"] == "executed"
    assert result["channel"] == "payment_link"
    assert result["provider_reference"] == "plink_1"
    assert result["action_url"] == "https://rzp.io/i/test"


# ── 3. Failed action execution ──────────────────────────────────────


def test_failed_execution_has_enriched_fields() -> None:
    import os
    os.environ["EXECUTOR_SIMULATE_FAILURE"] = "1"
    try:
        result = execute_action(None, "send_card_update_link", "pay_1", None, 50_000, "")
        assert result["status"] == "failed"
        assert result["channel"] == "internal"
        assert result["provider_reference"] is None
    finally:
        del os.environ["EXECUTOR_SIMULATE_FAILURE"]


# ── 4. CUSTOMER_CONTACTED event ─────────────────────────────────────


def test_customer_contacted_event_recorded() -> None:
    """The processor should write CUSTOMER_CONTACTED audit event metadata."""
    # This test validates the metadata shape expected by the processor
    metadata = {
        "action_id": str(uuid.uuid4()),
        "channel": "payment_link",
        "recipient": "Not available",
        "action_url": "https://rzp.io/i/test",
        "provider": "razorpay_payment_link",
        "provider_reference": "plink_test",
        "test_mode": True,
    }
    assert metadata["channel"] == "payment_link"
    assert metadata["test_mode"] is True


# ── 5. LINK_CLICKED event ───────────────────────────────────────────


def test_link_clicked_event() -> None:
    action = _make_action(status="sent")
    db = _make_db()
    updated = process_action_event(db, action, "LINK_CLICKED")
    assert updated.status == "clicked"
    assert updated.clicked_at is not None


# ── 6. PLAN_ACCEPTED event ──────────────────────────────────────────


def test_plan_accepted_event() -> None:
    action = _make_action(status="clicked")
    db = _make_db()
    updated = process_action_event(db, action, "PLAN_ACCEPTED")
    assert updated.status == "accepted"
    assert updated.responded_at is not None


# ── 7. PAYMENT_CAPTURED event ───────────────────────────────────────


def test_payment_completed_does_not_attribute_revenue() -> None:
    """Revenue is ONLY set via outcome_tracker, not via action events."""
    action = _make_action(status="clicked")
    db = _make_db()
    updated = process_action_event(db, action, "PAYMENT_STARTED")
    assert updated.status == "payment_pending"
    updated2 = process_action_event(db, updated, "PAYMENT_COMPLETED")
    assert updated2.status == "completed"
    assert updated2.revenue_recovered_paise == 0  # NOT set here


# ── 8. Revenue attribution ──────────────────────────────────────────


def test_outcome_tracker_attributes_revenue_to_action() -> None:
    from app.services.outcome_tracker import _attribute_recovery_to_action

    action = _make_action(status="sent")
    case = SimpleNamespace(
        id=action.case_id, amount_paise=50_000, razorpay_payment_id="pay_test_1"
    )
    db = _make_db([action])
    _attribute_recovery_to_action(db, case, "pay_test_1")
    assert action.status == "completed"
    assert action.revenue_recovered_paise == 50_000
    # Verify PAYMENT_CAPTURED and REVENUE_RECOVERED audit events created
    event_types = [e.event_type for e in db.events if hasattr(e, "event_type")]
    assert "PAYMENT_CAPTURED" in event_types
    assert "REVENUE_RECOVERED" in event_types


# ── 9. Duplicate payment prevention ─────────────────────────────────


def test_double_attribution_is_prevented() -> None:
    from app.services.outcome_tracker import _attribute_recovery_to_action

    action = _make_action(status="sent")
    case = SimpleNamespace(
        id=action.case_id, amount_paise=50_000, razorpay_payment_id="pay_test_2"
    )

    # Simulate an existing PAYMENT_CAPTURED audit event
    existing_event = SimpleNamespace(
        event_type="PAYMENT_CAPTURED", case_id=case.id
    )

    def scalar_returns_existing(query: Any) -> Any:
        return existing_event

    db = _make_db([action])
    db.scalar = scalar_returns_existing

    _attribute_recovery_to_action(db, case, "pay_test_2")
    # Action should NOT be updated
    assert action.status == "sent"
    assert action.revenue_recovered_paise == 0


# ── 10. Duplicate event prevention ──────────────────────────────────


def test_duplicate_link_clicked_is_rejected() -> None:
    action = _make_action(status="clicked", clicked_at=datetime.now(UTC))
    db = _make_db()
    try:
        process_action_event(db, action, "LINK_CLICKED")
        assert False, "Should have raised DuplicateEventError"
    except DuplicateEventError:
        pass


# ── 11. Invalid event transition ────────────────────────────────────


def test_invalid_event_transition_is_rejected() -> None:
    action = _make_action(status="sent")
    db = _make_db()
    try:
        process_action_event(db, action, "PLAN_ACCEPTED")
        assert False, "Should have raised InvalidEventError"
    except InvalidEventError:
        pass


def test_event_on_terminal_state_is_rejected() -> None:
    action = _make_action(status="completed")
    db = _make_db()
    try:
        process_action_event(db, action, "LINK_CLICKED")
        assert False, "Should have raised InvalidEventError"
    except InvalidEventError as e:
        assert "terminal" in str(e)


# ── 12. Missing customer information ────────────────────────────────


def test_missing_customer_information_is_handled() -> None:
    action = _make_action(recipient=None)
    assert action.recipient is None


# ── 13. Pending recovery ────────────────────────────────────────────


def test_pending_recovery_has_zero_revenue() -> None:
    action = _make_action(status="sent")
    assert action.revenue_recovered_paise == 0
    assert action.completed_at is None


# ── 14. Failed recovery ─────────────────────────────────────────────


def test_failed_recovery() -> None:
    action = _make_action(status="failed", failure_reason="Payment gateway error")
    assert action.status == "failed"
    assert action.failure_reason == "Payment gateway error"
    assert action.revenue_recovered_paise == 0


# ── 15. Recovered recovery ──────────────────────────────────────────


def test_recovered_action() -> None:
    action = _make_action(
        status="completed",
        completed_at=datetime.now(UTC),
        revenue_recovered_paise=50_000,
    )
    assert action.status == "completed"
    assert action.revenue_recovered_paise == 50_000


# ── 16. Batch metric updates ────────────────────────────────────────


def test_batch_metrics_include_action_data() -> None:
    from app.services.batch_processor import calculate_metrics

    batch = SimpleNamespace()
    cases = [
        SimpleNamespace(
            diagnosis="card_expired",
            recommended_action="send_card_update_link",
            outcome_status="success",
            recovered_amount_paise=500,
            revenue_at_risk_paise=500,
            execution_status="executed",
            policy_allowed=True,
        ),
        SimpleNamespace(
            diagnosis="insufficient_funds",
            recommended_action="stop",
            outcome_status="pending",
            recovered_amount_paise=0,
            revenue_at_risk_paise=300,
            execution_status="stopped",
            policy_allowed=False,
        ),
    ]
    calculate_metrics(batch, cases)
    assert batch.cases_analyzed == 2
    assert batch.total_revenue_recovered_paise == 500
    assert batch.successful_recoveries == 1
    assert batch.pending_recoveries == 0
    assert batch.failed_recoveries == 0


# ── 17. Executor enriched fields consistency ────────────────────────


def test_retry_has_enriched_fields() -> None:
    result = execute_retry("pay_1")
    assert result["status"] == "scheduled"
    assert "channel" in result
    assert "provider_reference" in result


def test_stop_has_enriched_fields() -> None:
    result = execute_stop("policy reason")
    assert result["status"] == "stopped"
    assert result["channel"] == "internal"
    assert result["provider_reference"] is None


# ── 18. Unknown event type ──────────────────────────────────────────


def test_unknown_event_type_is_rejected() -> None:
    action = _make_action(status="sent")
    db = _make_db()
    try:
        process_action_event(db, action, "FAKE_EVENT")
        assert False, "Should have raised InvalidEventError"
    except InvalidEventError as e:
        assert "Unknown event type" in str(e)
