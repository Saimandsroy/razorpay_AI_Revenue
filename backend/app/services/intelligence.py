from collections import defaultdict
from typing import Any

from app.schemas import GatewayAnomaly, IntelligenceEvent, IntelligenceSnapshot
from app.services.diagnosis import diagnose
from app.services.policy import choose_deterministic_action, evaluate_policy
from app.services.scoring import CustomerContext, recovery_score

MINIMUM_RECOVERABLE_AMOUNT_PAISE = 10_000  # ₹100


def gateway_identifier(payment: dict[str, Any]) -> str:
    """Use the best available processor attribute without inventing a gateway value."""
    return str(payment.get("gateway") or payment.get("bank") or payment.get("wallet") or payment.get("method") or "unknown")


def customer_context(payment: dict[str, Any], all_payments: list[dict[str, Any]]) -> CustomerContext:
    customer_id = payment.get("customer_id")
    customer_payments = [item for item in all_payments if customer_id and item.get("customer_id") == customer_id]
    successes = [item for item in customer_payments if item.get("status") == "captured"]
    failures = [item for item in customer_payments if item.get("status") == "failed" and item.get("id") != payment.get("id")]
    ltv_paise = sum(int(item.get("amount", 0)) for item in successes)
    # Without an authoritative last-success timestamp in a list response, use a neutral activity score.
    return CustomerContext(len(successes), len(failures), ltv_paise, days_inactive=30)


def priority_for(revenue_at_risk_paise: int, probability: float, policy_allowed: bool) -> str:
    expected_value = revenue_at_risk_paise * probability
    if not policy_allowed:
        return "P3"
    if revenue_at_risk_paise >= 1_000_000 and probability >= 0.70:
        return "P0"
    if revenue_at_risk_paise >= 500_000 or expected_value >= 400_000:
        return "P1"
    if probability >= 0.50:
        return "P2"
    return "P3"


def detect_gateway_anomalies(payments: list[dict[str, Any]]) -> list[GatewayAnomaly]:
    total_count = len(payments)
    failed_count = sum(item.get("status") == "failed" for item in payments)
    baseline = failed_count / total_count if total_count else 0.0
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for payment in payments:
        groups[gateway_identifier(payment)].append(payment)
    anomalies = []
    for gateway, group in sorted(groups.items()):
        failures = sum(item.get("status") == "failed" for item in group)
        rate = failures / len(group)
        anomalous = len(group) >= 5 and failures >= 2 and rate >= max(0.20, baseline * 2)
        anomalies.append(GatewayAnomaly(
            gateway=gateway,
            payments_observed=len(group),
            failed_payments=failures,
            failure_rate=round(rate, 3),
            baseline_failure_rate=round(baseline, 3),
            anomalous=anomalous,
        ))
    return anomalies


def build_intelligence_snapshot(payments: list[dict[str, Any]]) -> IntelligenceSnapshot:
    anomalies = detect_gateway_anomalies(payments)
    anomaly_by_gateway = {anomaly.gateway: anomaly.anomalous for anomaly in anomalies}
    events = []
    for payment in payments:
        amount = int(payment.get("amount", 0))
        if payment.get("status") != "failed" or amount <= MINIMUM_RECOVERABLE_AMOUNT_PAISE:
            continue
        diagnosis = diagnose(payment.get("error_code"))
        context = customer_context(payment, payments)
        probability = recovery_score(diagnosis.base_score, context)
        action = choose_deterministic_action(diagnosis.category, context)
        policy = evaluate_policy(action, diagnosis.category, context)
        gateway = gateway_identifier(payment)
        revenue_at_risk = amount
        events.append(IntelligenceEvent(
            payment_id=payment["id"],
            customer_id=payment.get("customer_id"),
            amount_paise=amount,
            currency=payment.get("currency", "INR"),
            diagnosis=diagnosis.category,
            root_cause=diagnosis.root_cause,
            error_code=payment.get("error_code"),
            gateway=gateway,
            recovery_probability=probability,
            revenue_at_risk_paise=revenue_at_risk,
            expected_recovery_value_paise=round(revenue_at_risk * probability),
            priority=priority_for(revenue_at_risk, probability, policy.allowed),
            recommended_action=action,
            policy_allowed=policy.allowed,
            gateway_anomaly=anomaly_by_gateway[gateway],
        ))
    events.sort(key=lambda event: ({"P0": 0, "P1": 1, "P2": 2, "P3": 3}[event.priority], -event.expected_recovery_value_paise))
    return IntelligenceSnapshot(
        events=events,
        total_events=len(events),
        total_revenue_at_risk_paise=sum(event.revenue_at_risk_paise for event in events),
        expected_recovery_value_paise=sum(event.expected_recovery_value_paise for event in events),
        gateway_anomalies=[item for item in anomalies if item.anomalous],
    )
