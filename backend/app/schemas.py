from uuid import UUID

from pydantic import BaseModel, Field


class ProcessPaymentRequest(BaseModel):
    payment_id: str = Field(min_length=3, examples=["pay_test_payment_id"])


class RejectedAlternativeResponse(BaseModel):
    action: str
    reason: str


class ProcessPaymentResponse(BaseModel):
    case_id: UUID
    diagnosis: str
    recovery_score: float
    recommended_action: str
    reasoning: str
    alternative_actions_rejected: list[RejectedAlternativeResponse]
    policy_allowed: bool
    policy_reason: str
    audit_event_count: int
    claude_reasoning: str | None
    claude_confidence: float | None
    was_fallback: bool


class FailedPaymentSummary(BaseModel):
    payment_id: str
    customer_id: str | None
    amount_paise: int
    currency: str
    error_code: str | None
    created_at: int | None


class GatewayAnomaly(BaseModel):
    gateway: str
    payments_observed: int
    failed_payments: int
    failure_rate: float
    baseline_failure_rate: float
    anomalous: bool


class IntelligenceEvent(BaseModel):
    payment_id: str
    customer_id: str | None
    amount_paise: int
    currency: str
    diagnosis: str
    root_cause: str
    error_code: str | None
    gateway: str
    recovery_probability: float
    revenue_at_risk_paise: int
    expected_recovery_value_paise: int
    priority: str
    recommended_action: str
    policy_allowed: bool
    gateway_anomaly: bool


class IntelligenceSnapshot(BaseModel):
    events: list[IntelligenceEvent]
    total_events: int
    total_revenue_at_risk_paise: int
    expected_recovery_value_paise: int
    gateway_anomalies: list[GatewayAnomaly]


class BatchStartResponse(BaseModel):
    batch_id: UUID
    status: str
    created_at: str | None
    cases_count: int


class BatchSummary(BaseModel):
    batch_id: UUID
    status: str
    cases_analyzed: int
    revenue_at_risk_paise: int
    revenue_recovered_paise: int
    recovery_rate: float
    by_diagnosis: dict
    by_action: dict


class CaseListItem(BaseModel):
    case_id: UUID
    customer: str | None
    amount_paise: int
    diagnosis: str
    action: str | None
    status: str
    recovered_amount_paise: int


class AuditTrailItem(BaseModel):
    event_type: str
    timestamp: str | None
    data: dict
