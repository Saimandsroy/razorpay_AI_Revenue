from dataclasses import dataclass


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class CustomerContext:
    successful_payments: int
    failed_payments: int
    ltv_paise: int
    days_inactive: int
    disputed: bool = False
    retry_attempts_last_30_days: int = 0
    mandate_rejections: int = 0

    @property
    def history_score(self) -> float:
        total = self.successful_payments + self.failed_payments
        return self.successful_payments / total if total else 0.5

    @property
    def ltv_score(self) -> float:
        return clamp(self.ltv_paise / 2_000_000)  # ₹20,000 = high value for MVP policy

    @property
    def churn_score(self) -> float:
        return clamp(1 - (self.days_inactive / 60))

    @property
    def activity_score(self) -> float:
        return clamp(1 - (self.days_inactive / 30))


def recovery_score(base_diagnosis_score: float, context: CustomerContext) -> float:
    """Auditable weighted score defined by the product brief, normalized to [0, 1]."""
    return round(clamp(
        0.25 * base_diagnosis_score
        + 0.25 * context.history_score
        + 0.20 * context.ltv_score
        + 0.15 * context.churn_score
        + 0.15 * context.activity_score
    ), 3)
