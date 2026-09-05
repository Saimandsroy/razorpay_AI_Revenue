import asyncio
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.models import AuditEvent
from app.services import gemini_client, processor
from app.services.gemini_client import get_gemini_failure_reason, get_gemini_recommendation
from app.services.gemini_validator import validate_gemini_output
from app.services.scoring import CustomerContext


VALID_OUTPUT = '{"reasoning":"The customer has reliable payment history.","confidence":0.82,"alternatives_rejected":[{"action":"retry","reason":"The card is expired."}]}'


def _configured_settings() -> SimpleNamespace:
    return SimpleNamespace(gemini_api_key="test-key", gemini_model="gemini-test", gemini_timeout_seconds=0.05)


class FakeGeminiModels:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.response, self.error, self.call = response, error, None

    def generate_content(self, **kwargs: object) -> object:
        self.call = kwargs
        if self.error:
            raise self.error
        return self.response


def _client(response: object | None = None, error: Exception | None = None) -> SimpleNamespace:
    return SimpleNamespace(models=FakeGeminiModels(response, error))


def test_gemini_validator_accepts_valid_json() -> None:
    valid, output = validate_gemini_output(VALID_OUTPUT)
    assert valid is True
    assert output is not None and output["confidence"] == 0.82


def test_gemini_validator_rejects_malformed_json() -> None:
    assert validate_gemini_output("not-json") == (False, None)


def test_gemini_uses_structured_response_and_explanation_only_prompt(monkeypatch) -> None:
    monkeypatch.setattr(gemini_client, "get_settings", _configured_settings)
    client = _client(SimpleNamespace(text=VALID_OUTPUT))
    result = asyncio.run(get_gemini_recommendation("card_expired", CustomerContext(8, 2, 1_800_000, 3), 0.843, "send_card_update_link", client))
    call = client.models.call

    assert validate_gemini_output(result)[0] is True
    assert call["model"] == "gemini-test"
    assert "Do not choose, alter, or propose a different action" in call["contents"]
    assert call["config"].response_mime_type == "application/json"


def test_gemini_unavailable_falls_back_without_network(monkeypatch) -> None:
    monkeypatch.setattr(gemini_client, "get_settings", lambda: SimpleNamespace(gemini_api_key=None, gemini_model=None, gemini_timeout_seconds=0.05))
    async def execute() -> tuple[str | None, str | None]:
        result = await get_gemini_recommendation("card_expired", CustomerContext(8, 2, 1_800_000, 3), 0.843, "send_card_update_link")
        return result, get_gemini_failure_reason()
    result, reason = asyncio.run(execute())
    assert result is None
    assert reason == "Gemini not configured"


def test_gemini_api_error_and_rate_limit_are_safe(monkeypatch) -> None:
    monkeypatch.setattr(gemini_client, "get_settings", _configured_settings)
    async def execute(client: object) -> tuple[str | None, str | None]:
        result = await get_gemini_recommendation("card_expired", CustomerContext(8, 2, 1_800_000, 3), 0.843, "send_card_update_link", client)
        return result, get_gemini_failure_reason()
    api_error, api_reason = asyncio.run(execute(_client(error=RuntimeError("service unavailable"))))
    assert api_error is None and api_reason == "Gemini temporarily unavailable"
    rate_limited, rate_reason = asyncio.run(execute(_client(error=RuntimeError("429 too many requests"))))
    assert rate_limited is None and rate_reason == "Rate limited"


def test_gemini_timeout_is_safe(monkeypatch) -> None:
    monkeypatch.setattr(gemini_client, "get_settings", _configured_settings)
    def slow_response(**_: object) -> object:
        import time
        time.sleep(0.2)
        return SimpleNamespace(text=VALID_OUTPUT)

    client = SimpleNamespace(models=SimpleNamespace(generate_content=slow_response))
    async def execute() -> tuple[str | None, str | None]:
        result = await get_gemini_recommendation("card_expired", CustomerContext(8, 2, 1_800_000, 3), 0.843, "send_card_update_link", client)
        return result, get_gemini_failure_reason()
    result, reason = asyncio.run(execute())
    assert result is None and reason == "Timeout"


def test_processing_uses_gemini_and_cannot_change_deterministic_action(monkeypatch) -> None:
    class FakeDb:
        def __init__(self) -> None: self.items: list[object] = []
        def scalar(self, _: object) -> None: return None
        def add(self, item: object) -> None: self.items.append(item)
        def flush(self) -> None:
            for item in self.items:
                if getattr(item, "id", None) is None: item.id = uuid.uuid4()
        def commit(self) -> None: pass

    payment = {"id": "pay_gemini_pipeline", "status": "failed", "customer_id": "cust_1", "amount": 50_000, "currency": "INR", "error_code": "BAD_REQUEST_CARD_EXPIRED", "created_at": int(datetime.now(UTC).timestamp())}
    captured = {"id": "pay_prior_success", "status": "captured", "customer_id": "cust_1", "amount": 1_800_000, "created_at": int(datetime.now(UTC).timestamp())}
    fake_db = FakeDb()
    payment_api = SimpleNamespace(fetch=lambda _: payment, all=lambda _: {"items": [payment, captured]})
    gemini_output = '{"reasoning":"Explanation only.","confidence":0.9,"alternatives_rejected":[],"recommended_action":"retry"}'

    async def explanation_only(*_: object) -> str: return gemini_output

    monkeypatch.setattr(processor, "get_gemini_recommendation", explanation_only)
    response, _ = asyncio.run(processor.process_payment(fake_db, SimpleNamespace(payment=payment_api, payment_link=SimpleNamespace(create=lambda _: {"id": "plink", "short_url": "https://example.invalid"})), payment["id"]))
    event = next(item for item in fake_db.items if isinstance(item, AuditEvent) and item.event_type == "GEMINI_REASONING_RECEIVED")

    assert response.recommended_action == "send_card_update_link"
    assert response.policy_allowed is True
    assert event.metadata_["gemini_reasoning"] == "Explanation only."


def test_processing_audits_gemini_fallback(monkeypatch) -> None:
    class FakeDb:
        def __init__(self) -> None: self.items: list[object] = []
        def scalar(self, _: object) -> None: return None
        def add(self, item: object) -> None: self.items.append(item)
        def flush(self) -> None:
            for item in self.items:
                if getattr(item, "id", None) is None: item.id = uuid.uuid4()
        def commit(self) -> None: pass

    payment = {"id": "pay_gemini_fallback", "status": "failed", "customer_id": "cust_2", "amount": 50_000, "currency": "INR", "error_code": "BAD_REQUEST_CARD_EXPIRED", "created_at": int(datetime.now(UTC).timestamp())}
    captured = {"id": "pay_prior_success_2", "status": "captured", "customer_id": "cust_2", "amount": 1_800_000, "created_at": int(datetime.now(UTC).timestamp())}
    async def unavailable(*_: object) -> None: return None
    monkeypatch.setattr(processor, "get_gemini_recommendation", unavailable)
    monkeypatch.setattr(processor, "get_gemini_failure_reason", lambda: "Gemini API error")
    db = FakeDb()
    response, _ = asyncio.run(processor.process_payment(db, SimpleNamespace(payment=SimpleNamespace(fetch=lambda _: payment, all=lambda _: {"items": [payment, captured]}), payment_link=SimpleNamespace(create=lambda _: {"id": "plink", "short_url": "https://example.invalid"})), payment["id"]))
    event = next(item for item in db.items if isinstance(item, AuditEvent) and item.event_type == "GEMINI_REASONING_RECEIVED")
    assert response.was_fallback is True
    assert event.metadata_["fallback_reason"] == "Gemini API error"
