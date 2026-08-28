import asyncio
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx

from app.models import AuditEvent
from app.services import claude_client, processor
from app.services.claude_client import get_claude_failure_reason, get_claude_recommendation
from app.services.claude_validator import validate_claude_output
from app.services.scoring import CustomerContext


VALID_OUTPUT = '{"reasoning":"The customer has reliable payment history.","confidence":0.82,"alternatives_rejected":[{"action":"retry","reason":"The card is expired."}]}'


def _configured_settings() -> SimpleNamespace:
    return SimpleNamespace(anthropic_api_key="test-key", claude_model="test-model", claude_timeout_seconds=2.5)


def test_validator_accepts_valid_claude_json() -> None:
    valid, output = validate_claude_output(VALID_OUTPUT)

    assert valid is True
    assert output is not None and output["confidence"] == 0.82


def test_validator_rejects_invalid_json() -> None:
    assert validate_claude_output("not-json") == (False, None)


def test_claude_client_returns_valid_response_text(monkeypatch) -> None:
    monkeypatch.setattr(claude_client, "get_settings", _configured_settings)
    body = {"content": [{"type": "text", "text": VALID_OUTPUT}]}
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body)))
    result = asyncio.run(get_claude_recommendation("card_expired", CustomerContext(8, 2, 1_800_000, 3), "send_card_update_link", client))
    asyncio.run(client.aclose())

    assert validate_claude_output(result)[0] is True


def test_claude_timeout_returns_none_with_reason(monkeypatch) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(claude_client, "get_settings", _configured_settings)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async def execute() -> tuple[str | None, str | None]:
        result = await get_claude_recommendation("card_expired", CustomerContext(8, 2, 1_800_000, 3), "send_card_update_link", client)
        return result, get_claude_failure_reason()

    result, failure_reason = asyncio.run(execute())
    asyncio.run(client.aclose())

    assert result is None
    assert failure_reason == "Timeout"


def test_claude_api_error_returns_none_with_reason(monkeypatch) -> None:
    monkeypatch.setattr(claude_client, "get_settings", _configured_settings)
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(500)))
    async def execute() -> tuple[str | None, str | None]:
        result = await get_claude_recommendation("card_expired", CustomerContext(8, 2, 1_800_000, 3), "send_card_update_link", client)
        return result, get_claude_failure_reason()

    result, failure_reason = asyncio.run(execute())
    asyncio.run(client.aclose())

    assert result is None
    assert failure_reason == "Claude API error"


def test_processing_falls_back_and_audits_claude_unavailability(monkeypatch) -> None:
    class FakeDb:
        def __init__(self) -> None:
            self.items: list[object] = []

        def scalar(self, _: object) -> None:
            return None

        def add(self, item: object) -> None:
            self.items.append(item)

        def flush(self) -> None:
            for item in self.items:
                if getattr(item, "id", None) is None:
                    item.id = uuid.uuid4()

        def commit(self) -> None:
            pass

    payment = {"id": "pay_claude_fallback", "status": "failed", "customer_id": "cust_1", "amount": 50_000, "currency": "INR", "error_code": "BAD_REQUEST_CARD_EXPIRED", "created_at": int(datetime.now(UTC).timestamp())}
    captured = {"id": "pay_prior_success", "status": "captured", "customer_id": "cust_1", "amount": 1_800_000, "created_at": int(datetime.now(UTC).timestamp())}
    payment_api = SimpleNamespace(fetch=lambda _: payment, all=lambda _: {"items": [payment, captured]})
    fake_db = FakeDb()

    async def unavailable(*_: object) -> None:
        return None

    monkeypatch.setattr(processor, "get_claude_recommendation", unavailable)
    monkeypatch.setattr(processor, "get_claude_failure_reason", lambda: "Claude API error")
    response = asyncio.run(processor.process_payment(fake_db, SimpleNamespace(payment=payment_api), payment["id"]))
    claude_event = next(item for item in fake_db.items if isinstance(item, AuditEvent) and item.event_type == "CLAUDE_REASONING_RECEIVED")

    assert response.was_fallback is True
    assert response.recommended_action == "send_card_update_link"
    assert claude_event.metadata_["was_fallback"] is True
    assert claude_event.metadata_["fallback_reason"] == "Claude API error"
