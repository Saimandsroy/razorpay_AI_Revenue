from dataclasses import dataclass

from app.services.scoring import CustomerContext


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


def evaluate_policy(action: str, diagnosis: str, context: CustomerContext, gateway_anomalous: bool = False) -> PolicyDecision:
    if context.disputed:
        return PolicyDecision(False, "Stopped: customer has disputed the original payment.")
    if context.days_inactive > 60:
        return PolicyDecision(False, "Stopped: customer is inactive for more than 60 days.")
    if action == "retry" and context.retry_attempts_last_30_days >= 3:
        return PolicyDecision(False, "Stopped: retry limit of 3 attempts in 30 days reached.")
    if diagnosis == "mandate_rejected" and context.mandate_rejections >= 2:
        return PolicyDecision(False, "Stopped: mandate was rejected at least twice.")
    if diagnosis == "mandate_rejected" and action == "retry":
        return PolicyDecision(False, "Stopped: retrying a rejected mandate is not permitted.")
    if diagnosis == "card_expired" and action == "retry":
        return PolicyDecision(False, "Stopped: retrying an expired card is not permitted.")
    if gateway_anomalous and action == "retry":
        return PolicyDecision(False, "Stopped: automatic retry suppressed because the gateway has an active failure-rate anomaly.")
    return PolicyDecision(True, "Allowed: all deterministic recovery policies passed.")


def choose_deterministic_action(diagnosis: str, context: CustomerContext) -> str:
    if diagnosis == "card_expired":
        if context.ltv_paise > 1_000_000:
            return "send_card_update_link"
        if context.ltv_paise >= 500_000:
            return "send_payment_plan"
        return "stop"
    if diagnosis == "insufficient_funds":
        if context.failed_payments >= 2:
            return "send_downgrade_offer"
        return "send_payment_plan" if context.history_score >= 0.5 else "retry"
    if diagnosis == "mandate_rejected":
        if context.ltv_paise > 2_000_000 and context.days_inactive <= 30:
            return "send_card_update_link"
        if context.ltv_paise < 2_000_000 and context.days_inactive <= 60:
            return "send_downgrade_offer"
        return "stop"
    if diagnosis == "authentication_failed":
        return "send_card_update_link" if context.history_score >= 0.5 else "stop"
    return "stop"
