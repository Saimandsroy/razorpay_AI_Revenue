import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


CASE_STATUS = ENUM(
    "detected", "processing", "allowed", "stopped", "pending", "success", "failed",
    name="case_status", create_type=False,
)
RECOVERY_ACTION = ENUM(
    "retry", "send_card_update_link", "send_payment_plan", "send_downgrade_offer", "stop",
    name="recovery_action", create_type=False,
)


class RecoveryBatch(Base):
    __tablename__ = "recovery_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cases_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    revenue_at_risk_paise: Mapped[int] = mapped_column(Integer, default=0)
    actions_executed: Mapped[int] = mapped_column(Integer, default=0)
    stopped_by_policy: Mapped[int] = mapped_column(Integer, default=0)
    successful_recoveries: Mapped[int] = mapped_column(Integer, default=0)
    failed_recoveries: Mapped[int] = mapped_column(Integer, default=0)
    pending_recoveries: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue_recovered_paise: Mapped[int] = mapped_column(Integer, default=0)
    metrics_by_diagnosis: Mapped[dict] = mapped_column(JSONB, default=dict)
    metrics_by_action: Mapped[dict] = mapped_column(JSONB, default=dict)


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recovery_batches.id"))
    razorpay_payment_id: Mapped[str] = mapped_column(Text, unique=True)
    customer_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String, default="INR")
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[str] = mapped_column(Text)
    recovery_score: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    revenue_at_risk_paise: Mapped[int] = mapped_column(Integer, default=0)
    expected_recovery_value_paise: Mapped[int] = mapped_column(Integer, default=0)
    recovery_priority: Mapped[str | None] = mapped_column(String, nullable=True)
    gateway_identifier: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(RECOVERY_ACTION, nullable=True)
    policy_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    policy_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(CASE_STATUS, default="detected")
    recovered_amount_paise: Mapped[int] = mapped_column(Integer, default=0)
    execution_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_result: Mapped[dict] = mapped_column(JSONB, default=dict)
    outcome_status: Mapped[str] = mapped_column(Text, default="pending")
    outcome_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recovery_cases.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
