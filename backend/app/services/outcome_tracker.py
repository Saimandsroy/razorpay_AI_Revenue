import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, RecoveryAction, RecoveryCase


def _attribute_recovery_to_action(db: Session, case: RecoveryCase, payment_id: str) -> None:
    """Attribute recovered revenue to the most recent non-completed RecoveryAction.

    Uses the Razorpay payment_id as an idempotency key to prevent double attribution.
    """
    # Check if this payment was already attributed
    existing = db.scalar(
        select(AuditEvent).where(
            AuditEvent.case_id == case.id,
            AuditEvent.event_type == "PAYMENT_CAPTURED",
        )
    )
    if existing:
        # Already attributed — do not double-count
        return

    # Find the latest active RecoveryAction for this case
    action = db.scalar(
        select(RecoveryAction)
        .where(RecoveryAction.case_id == case.id)
        .where(RecoveryAction.status.notin_(["completed", "failed", "expired", "cancelled"]))
        .order_by(RecoveryAction.created_at.desc())
    )
    if action:
        action.status = "completed"
        action.completed_at = datetime.now(UTC)
        action.revenue_recovered_paise = case.amount_paise
        action.updated_at = datetime.now(UTC)

    # Write PAYMENT_CAPTURED audit event
    db.add(AuditEvent(
        case_id=case.id,
        event_type="PAYMENT_CAPTURED",
        message=f"Payment {payment_id} captured successfully.",
        metadata_={
            "payment_id": payment_id,
            "amount_paise": case.amount_paise,
            "action_id": str(action.id) if action else None,
        },
    ))

    # Write REVENUE_RECOVERED audit event
    recovered_rupees = case.amount_paise / 100
    db.add(AuditEvent(
        case_id=case.id,
        event_type="REVENUE_RECOVERED",
        message=f"₹{recovered_rupees:,.0f} recovered from payment {payment_id}.",
        metadata_={
            "payment_id": payment_id,
            "recovered_amount_paise": case.amount_paise,
            "action_id": str(action.id) if action else None,
            "action_type": action.action_type if action else None,
        },
    ))


async def track_outcome(db: Session, client: Any, case: RecoveryCase, timeout_seconds: int = 300, poll_seconds: int = 30) -> str:
    """Poll only the original test payment; pending is an honest result for link/proposal actions."""
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    outcome = "pending"
    while True:
        try:
            payment = client.payment.fetch(case.razorpay_payment_id)
            if payment.get("status") == "captured":
                outcome = "success"
                case.recovered_amount_paise = case.amount_paise
                case.status = "success"
                _attribute_recovery_to_action(db, case, case.razorpay_payment_id)
                break
            if payment.get("status") in {"failed", "refunded"} and case.execution_status == "failed":
                outcome = "failed"
                case.status = "failed"
                # Mark associated actions as failed too
                actions = list(db.scalars(
                    select(RecoveryAction)
                    .where(RecoveryAction.case_id == case.id)
                    .where(RecoveryAction.status.notin_(["completed", "failed", "expired", "cancelled"]))
                ))
                for action in actions:
                    action.status = "failed"
                    action.failure_reason = "Payment failed or refunded"
                    action.updated_at = datetime.now(UTC)
                break
        except Exception:
            outcome = "pending"
            break
        if asyncio.get_running_loop().time() >= deadline:
            break
        await asyncio.sleep(min(poll_seconds, max(0, deadline - asyncio.get_running_loop().time())))
    case.outcome_status = outcome
    case.outcome_checked_at = datetime.now(UTC)
    db.add(AuditEvent(case_id=case.id, event_type="OUTCOME_TRACKED", message=f"Recovery outcome: {outcome}.", metadata_={"outcome": outcome, "recovered_amount_paise": case.recovered_amount_paise or 0}))
    db.commit()
    return outcome

