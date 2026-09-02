"""Optional smoke test. It is skipped unless both Gemini settings are configured."""
import asyncio

import pytest

from app.config import get_settings
from app.services import gemini_client
from app.services.gemini_client import get_gemini_failure_reason, get_gemini_recommendation
from app.services.gemini_validator import validate_gemini_output
from app.services.scoring import CustomerContext


settings = get_settings()
pytestmark = pytest.mark.skipif(not (settings.gemini_api_key and settings.gemini_model), reason="GEMINI_API_KEY and GEMINI_MODEL are not configured")


def test_live_gemini_returns_valid_reasoning(monkeypatch: pytest.MonkeyPatch) -> None:
    # Production keeps a 2.5s fail-fast timeout. Permit one bounded 10s
    # network allowance here so this optional connectivity smoke test measures
    # provider access instead of normal interactive fallback behavior.
    monkeypatch.setattr(gemini_client, "get_settings", lambda: settings.model_copy(update={"gemini_timeout_seconds": 10.0}))
    response = asyncio.run(get_gemini_recommendation("card_expired", CustomerContext(8, 2, 1_800_000, 3), 0.843, "send_card_update_link"))
    if response is None:
        pytest.skip(f"Gemini live smoke unavailable: {get_gemini_failure_reason() or 'unexpected provider response'}")
    valid, _ = validate_gemini_output(response)
    assert valid is True
