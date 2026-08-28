from dataclasses import dataclass

from app.services.scoring import CustomerContext


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class RejectedAlternative:
    action: str
    reason: str


@dataclass(frozen=True)
class ActionRecommendation:
    action: str
    reasoning: str
    alternatives_rejected: list[RejectedAlternative]


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


def recommend_action(diagnosis: str, context: CustomerContext) -> ActionRecommendation:
    """Context-aware recommendation with explainable, deterministic trade-offs."""
    if diagnosis == "card_expired":
        if context.days_inactive > 60:
            return ActionRecommendation(
                "send_downgrade_offer",
                "Customer is churned; a lower-friction offer is the least intrusive recovery option, subject to the policy gate.",
                [
                    RejectedAlternative("retry", "The card is expired, so the same payment method cannot succeed."),
                    RejectedAlternative("send_card_update_link", "A card update requires high customer effort and is unlikely from a churned customer."),
                ],
            )
        if context.ltv_paise > 1_500_000 and context.history_score > 0.70:
            return ActionRecommendation(
                "send_card_update_link",
                "Customer has high lifetime value and a strong successful-payment history; asking for updated card details is justified to recover the full amount.",
                [
                    RejectedAlternative("retry", "The card is expired, so retrying the same payment method is expected to fail and wastes customer goodwill."),
                    RejectedAlternative("send_downgrade_offer", "The customer is valuable and engaged; recover the full plan before offering a lower-value alternative."),
                ],
            )
        return ActionRecommendation(
            "send_card_update_link",
            "Card expiry is a correctable payment-method issue; an update link lets the customer provide a valid card.",
            [
                RejectedAlternative("retry", "The expired card will not become valid through another retry."),
                RejectedAlternative("send_downgrade_offer", "There is no churn signal requiring a lower-value offer before attempting full recovery."),
            ],
        )
    if diagnosis == "insufficient_funds":
        if context.failed_payments >= 2:
            return ActionRecommendation("send_downgrade_offer", "Repeated failures indicate affordability pressure; a lower-cost plan may retain the customer.", [RejectedAlternative("retry", "Multiple recent failures make another automatic retry low confidence."), RejectedAlternative("send_payment_plan", "A lower recurring amount better addresses repeated affordability pressure.")])
        if context.history_score >= 0.5:
            return ActionRecommendation("send_payment_plan", "Customer has enough positive history that spreading the amount reduces temporary cash-flow friction.", [RejectedAlternative("retry", "A payment plan has a higher expected recovery chance than an immediate retry."), RejectedAlternative("send_downgrade_offer", "The customer has not shown repeated affordability failures requiring a downgrade.")])
        return ActionRecommendation("retry", "There is no evidence of a permanent payment-method issue; a delayed retry is the lowest-friction option.", [RejectedAlternative("send_payment_plan", "Customer history does not yet justify changing the payment arrangement."), RejectedAlternative("send_downgrade_offer", "Downgrading is premature before a measured retry.")])
    if diagnosis == "mandate_rejected":
        if context.ltv_paise > 2_000_000 and context.days_inactive <= 30:
            return ActionRecommendation("send_card_update_link", "A high-value active customer can re-authorize with an updated payment method.", [RejectedAlternative("retry", "A bank-rejected mandate should not be retried."), RejectedAlternative("send_downgrade_offer", "Recovering the active customer's full plan is preferable first.")])
        if context.ltv_paise < 2_000_000 and context.days_inactive <= 60:
            return ActionRecommendation("send_downgrade_offer", "A lower commitment can be more acceptable after a mandate rejection.", [RejectedAlternative("retry", "The mandate has been rejected at bank level."), RejectedAlternative("send_card_update_link", "Re-authorization asks for more effort than a lower-commitment option.")])
        return ActionRecommendation("stop", "The customer context does not support a safe mandate recovery action.", [RejectedAlternative("retry", "Rejected mandates must not be retried."), RejectedAlternative("send_card_update_link", "The customer is not sufficiently active or valuable to justify re-authorization outreach.")])
    if diagnosis == "authentication_failed":
        if context.history_score >= 0.5:
            return ActionRecommendation("send_card_update_link", "A previously reliable customer can complete a fresh authentication flow with updated payment details.", [RejectedAlternative("retry", "Repeating a failed authentication without customer intervention is unlikely to resolve it.")])
        return ActionRecommendation("stop", "Low customer-history confidence does not justify further authentication outreach.", [RejectedAlternative("retry", "The authentication flow requires customer intervention.")])
    return ActionRecommendation("stop", "The failure code is unsupported, so no automated action is safe.", [RejectedAlternative("retry", "An unknown failure cause should not trigger blind retries.")])


def choose_deterministic_action(diagnosis: str, context: CustomerContext) -> str:
    """Compatibility wrapper for pipeline consumers that only need the action."""
    return recommend_action(diagnosis, context).action
