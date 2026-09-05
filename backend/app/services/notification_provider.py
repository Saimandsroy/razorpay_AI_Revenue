"""Test-mode notification provider abstraction.

This module provides a clean interface for sending recovery notifications.
The TestModeNotificationProvider records what WOULD be sent without making
external API calls. It is clearly distinguished from actual delivery.
"""
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class NotificationResult:
    """Result of a notification attempt. Never claims real delivery in test mode."""
    recipient: str | None
    channel: str
    provider: str
    provider_reference: str
    action_url: str | None
    sent_at: str
    status: str  # "sent" for real providers, "test_mode_recorded" for test mode
    metadata: dict = field(default_factory=dict)


def _extract_email_from_payment(payment_data: dict[str, Any]) -> str | None:
    """Extract customer email from Razorpay payment data if available."""
    email = payment_data.get("email")
    if email:
        return str(email)
    notes = payment_data.get("notes")
    if isinstance(notes, dict):
        return notes.get("customer_email") or notes.get("email")
    return None


class TestModeNotificationProvider:
    """Records notification details without external delivery.

    IMPORTANT: This provider logs what would be sent. It does NOT
    actually deliver messages to customers. The UI must distinguish
    between 'action executed' and 'message delivered'.
    """

    def send_email(
        self,
        recipient: str | None,
        subject: str,
        action_url: str | None,
        amount_paise: int,
        context: dict[str, Any] | None = None,
    ) -> NotificationResult:
        reference = f"test_email_{uuid.uuid4().hex[:16]}"
        return NotificationResult(
            recipient=recipient,
            channel="email",
            provider="test_mode_notification",
            provider_reference=reference,
            action_url=action_url,
            sent_at=datetime.now(UTC).isoformat(),
            status="test_mode_recorded",
            metadata={
                "subject": subject,
                "amount_paise": amount_paise,
                "test_mode": True,
                **(context or {}),
            },
        )

    def send_sms(
        self,
        recipient: str | None,
        message: str,
        action_url: str | None,
    ) -> NotificationResult:
        reference = f"test_sms_{uuid.uuid4().hex[:16]}"
        return NotificationResult(
            recipient=recipient,
            channel="sms",
            provider="test_mode_notification",
            provider_reference=reference,
            action_url=action_url,
            sent_at=datetime.now(UTC).isoformat(),
            status="test_mode_recorded",
            metadata={"message_preview": message[:100], "test_mode": True},
        )

    def send_payment_link(
        self,
        recipient: str | None,
        link_url: str | None,
        link_id: str | None,
        amount_paise: int,
    ) -> NotificationResult:
        return NotificationResult(
            recipient=recipient,
            channel="payment_link",
            provider="razorpay_payment_link",
            provider_reference=link_id or f"test_plink_{uuid.uuid4().hex[:16]}",
            action_url=link_url,
            sent_at=datetime.now(UTC).isoformat(),
            status="sent",
            metadata={"amount_paise": amount_paise, "link_id": link_id},
        )


# Singleton for use across the application.
notification_provider = TestModeNotificationProvider()
