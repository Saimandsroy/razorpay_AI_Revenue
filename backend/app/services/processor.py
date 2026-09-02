import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, RecoveryBatch, RecoveryCase
from app.schemas import FailedPaymentSummary, ProcessPaymentResponse, RejectedAlternativeResponse
from app.services.diagnosis import diagnose
from app.services.gemini_client import get_gemini_failure_reason, get_gemini_recommendation
from app.services.gemini_validator import validate_gemini_output
from app.services.executor import execute_action, execute_stop
from app.services.intelligence import gateway_identifier, priority_for
from app.services.policy import evaluate_policy, recommend_action
from app.services.scoring import CustomerContext, recovery_score


def _audit(db: Session, case_id: uuid.UUID, event_type: str, message: str, metadata: dict[str, Any]) -> None:
    db.add(AuditEvent(case_id=case_id, event_type=event_type, message=message, metadata_=metadata))


def _context_from_payments(payments: list[dict[str, Any]], failed_payment_id: str) -> CustomerContext:
    successes = [p for p in payments if p.get("status") == "captured"]
    failures = [p for p in payments if p.get("status") == "failed" and p.get("id") != failed_payment_id]
    ltv_paise = sum(int(p.get("amount", 0)) for p in successes)
    latest_success = max((int(p.get("created_at", 0)) for p in successes), default=0)
    days_inactive = int((datetime.now(UTC).timestamp() - latest_success) / 86_400) if latest_success else 61
    return CustomerContext(len(successes), len(failures), ltv_paise, max(0, days_inactive))


async def process_payment(db: Session, client: Any, payment_id: str, batch: RecoveryBatch | None = None) -> ProcessPaymentResponse:
    existing = db.scalar(select(RecoveryCase).where(RecoveryCase.razorpay_payment_id == payment_id))
    if existing:
        raise HTTPException(409, "This payment has already been processed.")

    payment = client.payment.fetch(payment_id)
    if payment.get("status") != "failed":
        raise HTTPException(422, "Only failed Razorpay payments are eligible for recovery.")
    customer_id = payment.get("customer_id")
    payments = client.payment.all({"customer_id": customer_id, "count": 100})["items"] if customer_id else []
    context = _context_from_payments(payments, payment_id)
    diagnosis = diagnose(payment.get("error_code"))
    score = recovery_score(diagnosis.base_score, context)
    recommendation = recommend_action(diagnosis.category, context)
    policy = evaluate_policy(recommendation.action, diagnosis.category, context)
    case_status = "allowed" if policy.allowed else "stopped"
    revenue_at_risk = int(payment["amount"])
    expected_recovery_value = round(revenue_at_risk * score)
    priority = priority_for(revenue_at_risk, score, policy.allowed)
    gemini_raw = await get_gemini_recommendation(diagnosis.category, context, score, recommendation.action)
    gemini_valid, gemini_output = validate_gemini_output(gemini_raw)
    was_fallback = not gemini_valid
    fallback_reason = "Invalid JSON" if gemini_raw is not None else (get_gemini_failure_reason() or "Gemini API error")

    if batch is None:
        batch = RecoveryBatch(name=f"single-{payment_id}", status="complete")
        db.add(batch)
        db.flush()
    case = RecoveryCase(
        batch_id=batch.id,
        razorpay_payment_id=payment_id,
        customer_id=customer_id,
        customer_name=payment.get("notes", {}).get("customer_name"),
        amount_paise=int(payment["amount"]),
        currency=payment.get("currency", "INR"),
        error_code=payment.get("error_code"),
        diagnosis=diagnosis.category,
        recovery_score=score,
        revenue_at_risk_paise=revenue_at_risk,
        expected_recovery_value_paise=expected_recovery_value,
        recovery_priority=priority,
        gateway_identifier=gateway_identifier(payment),
        recommended_action=recommendation.action,
        policy_allowed=policy.allowed,
        policy_reason=policy.reason,
        status=case_status,
    )
    db.add(case)
    db.flush()
    _audit(db, case.id, "DETECTED", "Failed Razorpay payment detected.", {"payment_id": payment_id, "amount_paise": case.amount_paise})
    _audit(db, case.id, "DIAGNOSED", diagnosis.root_cause, {"error_code": case.error_code, "diagnosis": diagnosis.category})
    _audit(db, case.id, "CONTEXT_FETCHED", "Customer payment history was retrieved.", {"successful_payments": context.successful_payments, "failed_payments": context.failed_payments, "ltv_paise": context.ltv_paise, "days_inactive": context.days_inactive})
    _audit(db, case.id, "SCORED", "Deterministic recovery score calculated.", {"score": score, "base_diagnosis_score": diagnosis.base_score})
    _audit(db, case.id, "RISK_ASSESSED", "Revenue-at-risk and recovery priority calculated.", {"revenue_at_risk_paise": revenue_at_risk, "expected_recovery_value_paise": expected_recovery_value, "priority": priority, "gateway": case.gateway_identifier})
    _audit(db, case.id, "DECISION_MADE", recommendation.reasoning, {"recommended_action": recommendation.action, "alternative_actions_rejected": [{"action": item.action, "reason": item.reason} for item in recommendation.alternatives_rejected]})
    _audit(db, case.id, "GEMINI_REASONING_RECEIVED", "Gemini explanation accepted." if gemini_valid else f"Deterministic fallback used: {fallback_reason}.", {"gemini_reasoning": gemini_output["reasoning"] if gemini_valid else None, "confidence": gemini_output["confidence"] if gemini_valid else None, "alternatives_rejected": gemini_output["alternatives_rejected"] if gemini_valid else [], "was_fallback": was_fallback, "fallback_reason": fallback_reason if was_fallback else None})
    _audit(db, case.id, "POLICY_GATE", policy.reason, {"allowed": policy.allowed})
    execution = execute_action(client, recommendation.action, payment_id, customer_id, revenue_at_risk, policy.reason) if policy.allowed else execute_stop(policy.reason)
    case.execution_status = execution["status"]
    case.execution_result = execution
    event_type = "ACTION_EXECUTED" if policy.allowed else "ACTION_STOPPED"
    _audit(db, case.id, event_type, f"Action {recommendation.action} {execution['status']}.", execution)
    db.commit()
    return ProcessPaymentResponse(case_id=case.id, diagnosis=diagnosis.category, recovery_score=score, recommended_action=recommendation.action, reasoning=recommendation.reasoning, alternative_actions_rejected=[RejectedAlternativeResponse(action=item.action, reason=item.reason) for item in recommendation.alternatives_rejected], policy_allowed=policy.allowed, policy_reason=policy.reason, audit_event_count=9, gemini_reasoning=gemini_output["reasoning"] if gemini_valid else None, gemini_confidence=gemini_output["confidence"] if gemini_valid else None, was_fallback=was_fallback)


def list_failed_payments(client: Any, limit: int) -> list[FailedPaymentSummary]:
    """Detect failed test-mode payments without changing Razorpay or local state."""
    payments = client.payment.all({"count": limit}).get("items", [])
    return [
        FailedPaymentSummary(
            payment_id=payment["id"],
            customer_id=payment.get("customer_id"),
            amount_paise=int(payment["amount"]),
            currency=payment.get("currency", "INR"),
            error_code=payment.get("error_code"),
            created_at=payment.get("created_at"),
        )
        for payment in payments
        if payment.get("status") == "failed" and int(payment.get("amount", 0)) > 10_000
    ]
