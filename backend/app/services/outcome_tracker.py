import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent, RecoveryCase


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
                break
            if payment.get("status") in {"failed", "refunded"} and case.execution_status == "failed":
                outcome = "failed"
                case.status = "failed"
                break
        except Exception:
            outcome = "pending"
            break
        if asyncio.get_running_loop().time() >= deadline:
            break
        await asyncio.sleep(min(poll_seconds, max(0, deadline - asyncio.get_running_loop().time())))
    case.outcome_status = outcome
    case.outcome_checked_at = datetime.now(UTC)
    db.add(AuditEvent(case_id=case.id, event_type="OUTCOME_TRACKED", message=f"Recovery outcome: {outcome}.", metadata_={"outcome": outcome, "recovered_amount_paise": case.recovered_amount_paise}))
    db.commit()
    return outcome
