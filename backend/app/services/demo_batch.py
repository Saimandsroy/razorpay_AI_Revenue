"""Development-only, Razorpay-shaped fixtures for a safe dashboard demo.

This module never imports or calls the Razorpay SDK. It exists solely to feed
fixed failure scenarios through the production recovery pipeline and persist
their results to PostgreSQL.
"""
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AuditEvent, RecoveryBatch, RecoveryCase
from app.services.batch_processor import calculate_metrics
from app.services.outcome_tracker import track_outcome
from app.services.processor import process_payment


class DemoPaymentApi:
    def __init__(self, payments: dict[str, dict[str, Any]], histories: dict[str, list[dict[str, Any]]], successful: set[str]) -> None:
        self.payments, self.histories, self.successful, self.calls = payments, histories, successful, {}

    def fetch(self, payment_id: str) -> dict[str, Any]:
        self.calls[payment_id] = self.calls.get(payment_id, 0) + 1
        payment = dict(self.payments[payment_id])
        if payment_id in self.successful and self.calls[payment_id] > 1:
            payment["status"] = "captured"
        return payment

    def all(self, query: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        return {"items": list(self.histories.get(query.get("customer_id"), []))}


class DemoPaymentLinkApi:
    def __init__(self, failing_references: set[str]) -> None:
        self.failing_references = failing_references

    def create(self, payload: dict[str, Any]) -> dict[str, str]:
        reference = str(payload.get("reference_id"))
        if reference in self.failing_references:
            raise RuntimeError("DEMO: simulated payment-link provider failure")
        return {"id": f"plink_demo_{reference}", "short_url": "https://example.invalid/demo-payment-link"}


def _fixture_client() -> SimpleNamespace:
    token, now, old = uuid.uuid4().hex[:12], int(datetime.now(UTC).timestamp()), int(datetime.now(UTC).timestamp()) - 61 * 86_400

    def failed(name: str, customer: str, code: str, amount: int) -> dict[str, Any]:
        return {"id": f"pay_demo_{token}_{name}", "status": "failed", "customer_id": f"cust_demo_{token}_{customer}", "amount": amount, "currency": "INR", "error_code": code, "notes": {"customer_name": f"Demo {customer.title()}"}, "gateway": "demo_gateway", "created_at": now}

    def success(customer: str, created_at: int, amount: int = 1_800_000) -> dict[str, Any]:
        return {"id": f"pay_demo_history_{token}_{customer}", "status": "captured", "customer_id": f"cust_demo_{token}_{customer}", "amount": amount, "currency": "INR", "created_at": created_at}

    payments = {
        "success": failed("success", "high_value", "BAD_REQUEST_CARD_EXPIRED", 499_900),
        "pending": failed("pending", "cash_flow", "BAD_REQUEST_INSUFFICIENT_FUNDS", 299_900),
        "stopped": failed("stopped", "churn_risk", "BAD_REQUEST_CARD_EXPIRED", 199_900),
        "mandate": failed("mandate", "mandate_churn", "BAD_REQUEST_MANDATE_REJECTED", 399_900),
        "failed": failed("failed", "link_failure", "BAD_REQUEST_CARD_EXPIRED", 599_900),
    }
    histories = {
        payments["success"]["customer_id"]: [payments["success"], success("high_value", now)],
        payments["pending"]["customer_id"]: [payments["pending"], success("cash_flow", now, 300_000)],
        payments["stopped"]["customer_id"]: [payments["stopped"], success("churn_risk", old)],
        payments["mandate"]["customer_id"]: [payments["mandate"], success("mandate_churn", old)],
        payments["failed"]["customer_id"]: [payments["failed"], success("link_failure", now)],
    }
    return SimpleNamespace(
        payment=DemoPaymentApi({payment["id"]: payment for payment in payments.values()}, histories, {payments["success"]["id"]}),
        payment_link=DemoPaymentLinkApi({payments["failed"]["id"]}),
        demo_payment_ids=[payment["id"] for payment in payments.values()],
    )


async def process_demo_batch(db: Session) -> RecoveryBatch:
    """Persist five fixed demo scenarios through the production pipeline."""
    client = _fixture_client()
    batch = RecoveryBatch(name=f"demo-{uuid.uuid4().hex[:12]}", status="processing")
    db.add(batch)
    db.commit()
    db.refresh(batch)
    cases: list[RecoveryCase] = []
    for payment_id in client.demo_payment_ids:
        response, was_duplicate = await process_payment(db, client, payment_id, batch)
        if not was_duplicate:
            case = db.get(RecoveryCase, response.case_id)
            if case:
                await track_outcome(db, client, case, timeout_seconds=0)
                cases.append(case)
    calculate_metrics(batch, cases)
    batch.status = "complete"
    db.commit()
    db.refresh(batch)
    return batch


def clear_demo_batches(db: Session) -> int:
    """Delete only batches that this module created, including their case audits."""
    batches = list(db.scalars(select(RecoveryBatch).where(RecoveryBatch.name.like("demo-%"))))
    batch_ids = [batch.id for batch in batches]
    if not batch_ids:
        return 0
    case_ids = list(db.scalars(select(RecoveryCase.id).where(RecoveryCase.batch_id.in_(batch_ids))))
    if case_ids:
        db.execute(delete(AuditEvent).where(AuditEvent.case_id.in_(case_ids)))
        db.execute(delete(RecoveryCase).where(RecoveryCase.id.in_(case_ids)))
    db.execute(delete(RecoveryBatch).where(RecoveryBatch.id.in_(batch_ids)))
    db.commit()
    return len(batch_ids)
