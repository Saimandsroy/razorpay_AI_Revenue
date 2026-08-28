from datetime import UTC, datetime
import os
from typing import Any


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def execute_retry(payment_id: str) -> dict[str, Any]:
    # Razorpay has no safe API that re-charges an already-failed payment ID.
    return {"status": "scheduled", "payment_id": payment_id, "timestamp": _timestamp(), "note": "Retry recorded; no charge is initiated by this service."}


def execute_send_card_link(client: Any, customer_id: str | None, payment_id: str, amount: int) -> dict[str, Any]:
    link = client.payment_link.create({"amount": amount, "currency": "INR", "reference_id": payment_id, "description": "Update payment method to recover failed payment", "customer": {"id": customer_id} if customer_id else None, "notify": {"sms": False, "email": False}})
    return {"status": "executed", "link_url": link.get("short_url"), "link_id": link.get("id"), "timestamp": _timestamp()}


def execute_send_payment_plan(client: Any, customer_id: str | None, amount: int) -> dict[str, Any]:
    installment = max(100, amount // 3)
    links = [execute_send_card_link(client, customer_id, f"plan-{index}-{int(datetime.now(UTC).timestamp())}", installment) for index in range(1, 4)]
    return {"status": "executed", "plan_links": links, "timestamp": _timestamp()}


def execute_send_downgrade_offer(subscription_id: str | None, new_amount: int) -> dict[str, Any]:
    return {"status": "proposed", "subscription_id": subscription_id, "new_amount": new_amount, "timestamp": _timestamp(), "note": "Downgrade requires merchant/customer confirmation; no subscription is changed automatically."}


def execute_stop(reason: str) -> dict[str, Any]:
    return {"status": "stopped", "reason": reason, "stopped_at": _timestamp()}


def execute_action(client: Any, action: str, payment_id: str, customer_id: str | None, amount: int, policy_reason: str) -> dict[str, Any]:
    try:
        if os.getenv("EXECUTOR_SIMULATE_FAILURE") == "1":
            raise RuntimeError("Simulated Razorpay execution error")
        if action == "send_card_update_link":
            return execute_send_card_link(client, customer_id, payment_id, amount)
        if action == "send_payment_plan":
            return execute_send_payment_plan(client, customer_id, amount)
        if action == "send_downgrade_offer":
            return execute_send_downgrade_offer(None, amount // 2)
        if action == "retry":
            return execute_retry(payment_id)
        return execute_stop(policy_reason)
    except Exception as error:  # Gateway SDK errors are persisted, not swallowed.
        return {"status": "failed", "error": str(error), "timestamp": _timestamp()}
