"""Customer interaction event handling for recovery actions.

Validates event types, enforces state transitions, prevents duplicates,
and updates RecoveryAction timestamps/status accordingly.
"""
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent, RecoveryAction

logger = logging.getLogger("recovery_api")

# Valid customer interaction event types
VALID_EVENT_TYPES = {
    "LINK_CLICKED",
    "PLAN_VIEWED",
    "PLAN_ACCEPTED",
    "PAYMENT_STARTED",
    "PAYMENT_COMPLETED",
    "PAYMENT_FAILED",
}

# Status transitions: from_status -> set of valid event types
VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"LINK_CLICKED", "PLAN_VIEWED"},
    "sent": {"LINK_CLICKED", "PLAN_VIEWED", "PAYMENT_STARTED"},
    "delivered": {"LINK_CLICKED", "PLAN_VIEWED", "PAYMENT_STARTED"},
    "clicked": {"LINK_CLICKED", "PLAN_VIEWED", "PLAN_ACCEPTED", "PAYMENT_STARTED", "PAYMENT_COMPLETED", "PAYMENT_FAILED"},
    "accepted": {"PAYMENT_STARTED", "PAYMENT_COMPLETED", "PAYMENT_FAILED"},
    "payment_pending": {"PAYMENT_COMPLETED", "PAYMENT_FAILED"},
}

# Event type -> new status mapping
EVENT_STATUS_MAP: dict[str, str] = {
    "LINK_CLICKED": "clicked",
    "PLAN_VIEWED": "clicked",
    "PLAN_ACCEPTED": "accepted",
    "PAYMENT_STARTED": "payment_pending",
    "PAYMENT_COMPLETED": "completed",
    "PAYMENT_FAILED": "failed",
}

# Audit event messages
EVENT_MESSAGES: dict[str, str] = {
    "LINK_CLICKED": "Customer interacted with recovery link.",
    "PLAN_VIEWED": "Customer viewed the recovery plan.",
    "PLAN_ACCEPTED": "Customer accepted the recovery plan.",
    "PAYMENT_STARTED": "Customer started a payment.",
    "PAYMENT_COMPLETED": "Customer completed payment successfully.",
    "PAYMENT_FAILED": "Customer payment attempt failed.",
}


class InvalidEventError(Exception):
    """Raised when an event is invalid for the current action state."""
    pass


class DuplicateEventError(Exception):
    """Raised when a duplicate event is detected."""
    pass


def process_action_event(
    db: Session,
    action: RecoveryAction,
    event_type: str,
    metadata: dict[str, Any] | None = None,
) -> RecoveryAction:
    """Process a customer interaction event against a RecoveryAction.

    Validates:
    - Event type is recognized
    - State transition is valid
    - Event is not a duplicate (e.g., clicking twice)

    Updates RecoveryAction timestamps/status and creates audit events.
    Revenue is NOT attributed here — only via outcome_tracker when Razorpay confirms capture.
    """
    if event_type not in VALID_EVENT_TYPES:
        raise InvalidEventError(f"Unknown event type: {event_type}. Valid types: {sorted(VALID_EVENT_TYPES)}")

    current_status = action.status
    # Check terminal states
    if current_status in {"completed", "failed", "expired", "cancelled"}:
        raise InvalidEventError(f"Action is in terminal state '{current_status}' and cannot accept new events.")

    # Check valid transitions
    allowed = VALID_TRANSITIONS.get(current_status, set())
    if event_type not in allowed:
        raise InvalidEventError(
            f"Event '{event_type}' is not valid from status '{current_status}'. "
            f"Allowed events: {sorted(allowed) if allowed else 'none'}"
        )

    # Check for duplicate click/view events
    now = datetime.now(UTC)
    if event_type == "LINK_CLICKED" and action.clicked_at is not None:
        raise DuplicateEventError("LINK_CLICKED event was already recorded for this action.")

    # Update timestamps based on event type
    if event_type in {"LINK_CLICKED", "PLAN_VIEWED"} and action.clicked_at is None:
        action.clicked_at = now
    if event_type in {"PLAN_ACCEPTED"} and action.responded_at is None:
        action.responded_at = now
    if event_type == "PAYMENT_COMPLETED":
        # Do NOT set revenue here. Revenue attribution is only via outcome_tracker
        # when Razorpay confirms the payment capture.
        action.completed_at = now

    # Update status
    new_status = EVENT_STATUS_MAP.get(event_type, current_status)
    action.status = new_status
    action.updated_at = now

    # Create audit event
    audit_metadata = {
        "action_id": str(action.id),
        "event_type": event_type,
        "previous_status": current_status,
        "new_status": new_status,
        **(metadata or {}),
    }
    # Map event type to the appropriate audit event type
    audit_event_type = "CUSTOMER_RESPONSE" if event_type not in {"LINK_CLICKED"} else "LINK_CLICKED"
    if event_type == "PLAN_VIEWED":
        audit_event_type = "PLAN_VIEWED"
    elif event_type == "PLAN_ACCEPTED":
        audit_event_type = "PLAN_ACCEPTED"
    elif event_type == "PAYMENT_STARTED":
        audit_event_type = "PAYMENT_STARTED"
    elif event_type == "PAYMENT_COMPLETED":
        audit_event_type = "PAYMENT_COMPLETED"
    elif event_type == "PAYMENT_FAILED":
        audit_event_type = "ACTION_FAILED"

    message = EVENT_MESSAGES.get(event_type, f"Customer event: {event_type}")
    db.add(AuditEvent(
        case_id=action.case_id,
        event_type=audit_event_type,
        message=message,
        metadata_=audit_metadata,
    ))

    db.commit()
    logger.info("Processed event %s for action %s: %s -> %s", event_type, action.id, current_status, new_status)
    return action
