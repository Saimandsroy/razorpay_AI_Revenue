"""Offline-safe verification of the production pipeline using Razorpay test-mode-shaped fixtures.

It never creates a Razorpay payment or charges a customer. If GEMINI_API_KEY and
GEMINI_MODEL are configured, the real bounded Gemini client is used; otherwise its
production fallback path is audited explicitly.
"""
import asyncio
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.models import AuditEvent, RecoveryBatch, RecoveryCase
from app.services.outcome_tracker import track_outcome
from app.services.processor import process_payment

EXPECTED = ["DETECTED", "DIAGNOSED", "SCORED", "GEMINI_REASONING_RECEIVED", "POLICY_GATE"]


class DryDb:
    def __init__(self) -> None: self.items: list[object] = []
    def scalar(self, _: object) -> None: return None
    def add(self, item: object) -> None: self.items.append(item)
    def flush(self) -> None:
        for item in self.items:
            if getattr(item, "id", None) is None: item.id = uuid.uuid4()
    def commit(self) -> None: pass
    def get(self, model: type, key: object) -> object | None:
        return next((item for item in self.items if isinstance(item, model) and getattr(item, "id", None) == key), None)


class PaymentApi:
    def __init__(self, payments: dict[str, dict], histories: dict[str, list[dict]], capture_after_first_fetch: set[str]) -> None:
        self.payments, self.histories, self.calls, self.capture_after = payments, histories, {}, capture_after_first_fetch
    def fetch(self, payment_id: str) -> dict:
        self.calls[payment_id] = self.calls.get(payment_id, 0) + 1
        payment = dict(self.payments[payment_id])
        if payment_id in self.capture_after and self.calls[payment_id] > 1: payment["status"] = "captured"
        return payment
    def all(self, query: dict) -> dict: return {"items": self.histories.get(query.get("customer_id"), [])}


def payment_link_create(_: dict) -> dict: return {"id": "plink_dry", "short_url": "https://rzp.io/i/dry-run"}


async def main() -> None:
    settings = get_settings()
    if settings.razorpay_key_id and not settings.razorpay_key_id.startswith("rzp_test_"):
        raise RuntimeError("Dry run refuses non-test Razorpay credentials.")
    now, old = int(datetime.now(UTC).timestamp()), int(datetime.now(UTC).timestamp()) - 61 * 86_400
    def failed(identifier: str, customer: str, code: str) -> dict: return {"id": identifier, "status": "failed", "customer_id": customer, "amount": 499_900, "currency": "INR", "error_code": code, "created_at": now}
    payments = {
        "pay_card_high": failed("pay_card_high", "high", "BAD_REQUEST_CARD_EXPIRED"),
        "pay_card_churn": failed("pay_card_churn", "churn", "BAD_REQUEST_CARD_EXPIRED"),
        "pay_funds": failed("pay_funds", "funds", "BAD_REQUEST_INSUFFICIENT_FUNDS"),
        "pay_mandate": failed("pay_mandate", "mandate", "BAD_REQUEST_MANDATE_REJECTED"),
        "pay_policy_block": failed("pay_policy_block", "blocked", "BAD_REQUEST_CARD_EXPIRED"),
    }
    success = lambda customer, created, amount=1_800_000: {"id": f"pay_success_{customer}", "status": "captured", "customer_id": customer, "amount": amount, "created_at": created}
    histories = {"high": [payments["pay_card_high"], success("high", now)], "churn": [payments["pay_card_churn"], success("churn", old)], "funds": [payments["pay_funds"], success("funds", now, 300_000)], "mandate": [payments["pay_mandate"], success("mandate", now, 300_000)], "blocked": [payments["pay_policy_block"], success("blocked", old)]}
    payment_api = PaymentApi(payments, histories, {"pay_card_high"})
    client = SimpleNamespace(payment=payment_api, payment_link=SimpleNamespace(create=payment_link_create))
    print(f"TEST_MODE_KEY={'configured' if settings.razorpay_key_id else 'not configured'} GEMINI={'real' if settings.gemini_api_key and settings.gemini_model else 'fallback'}")
    for identifier in payments:
        db = DryDb(); result = await process_payment(db, client, identifier)
        case = db.get(RecoveryCase, result.case_id)
        await track_outcome(db, client, case, timeout_seconds=0)
        events = [item.event_type for item in db.items if isinstance(item, AuditEvent)]
        expected_end = "ACTION_EXECUTED" if result.policy_allowed else "ACTION_STOPPED"
        valid = all(name in events for name in EXPECTED + [expected_end, "OUTCOME_TRACKED"])
        ordering = [events.index(name) for name in EXPECTED + [expected_end, "OUTCOME_TRACKED"]]
        valid = valid and ordering == sorted(ordering)
        print(f"{'PASS' if valid else 'FAIL'} {identifier}: action={result.recommended_action} policy={result.policy_allowed} outcome={case.outcome_status}")
        print(json.dumps([{ "event_type": item.event_type, "data": item.metadata_ } for item in db.items if isinstance(item, AuditEvent)], indent=2, default=str))
    print("DRY_RUN_COMPLETE")


if __name__ == "__main__": asyncio.run(main())
