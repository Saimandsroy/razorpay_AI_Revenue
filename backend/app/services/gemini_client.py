"""Bounded Google Gemini enrichment for deterministic recovery decisions."""
import asyncio
import json
import os
from contextvars import ContextVar
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import get_settings
from app.services.scoring import CustomerContext


class RejectedAlternative(BaseModel):
    action: str
    reason: str


class GeminiReasoning(BaseModel):
    reasoning: str
    confidence: float
    alternatives_rejected: list[RejectedAlternative]


_failure_reason: ContextVar[str | None] = ContextVar("gemini_failure_reason", default=None)


def get_gemini_failure_reason() -> str | None:
    return _failure_reason.get()


def _failure_for(error: Exception) -> str:
    status = getattr(error, "status_code", None) or getattr(error, "code", None)
    if status == 429 or "429" in str(error) or "rate limit" in str(error).lower():
        return "Rate limited"
    return "Gemini API error"


async def get_gemini_recommendation(
    diagnosis: str,
    customer_context: CustomerContext,
    recovery_score: float,
    deterministic_action: str,
    client: Any | None = None,
) -> str | None:
    """Return a structured Gemini explanation, or None with a safe failure reason.

    Gemini never receives authority to choose an action. The caller uses only
    the validated explanation fields and retains the deterministic decision.
    """
    settings = get_settings()
    _failure_reason.set(None)
    simulation = os.getenv("GEMINI_SIMULATE_FAILURE")
    if simulation == "invalid_json":
        return "{invalid-json"
    if simulation == "timeout":
        await asyncio.sleep(settings.gemini_timeout_seconds)
        _failure_reason.set("Timeout")
        return None
    if simulation == "api_error":
        _failure_reason.set("Gemini API error")
        return None
    if simulation == "rate_limit":
        _failure_reason.set("Rate limited")
        return None
    if not settings.gemini_api_key or not settings.gemini_model:
        _failure_reason.set("Gemini not configured")
        return None

    prompt = {
        "diagnosis": diagnosis,
        "customer_ltv_paise": customer_context.ltv_paise,
        "success_rate": round(customer_context.history_score, 3),
        "churn_signal": "churned" if customer_context.days_inactive > 60 else "at_risk" if customer_context.days_inactive > 30 else "active",
        "recovery_score": recovery_score,
        "deterministic_recommended_action": deterministic_action,
        "instruction": "Explain the supplied deterministic recovery action only. Do not choose, alter, or propose a different action. Return only JSON with reasoning (string), confidence (0..1), and alternatives_rejected ([{action, reason}]).",
    }
    api_client = client or genai.Client(api_key=settings.gemini_api_key)

    def generate() -> Any:
        return api_client.models.generate_content(
            model=settings.gemini_model,
            contents=json.dumps(prompt),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiReasoning,
            ),
        )

    try:
        response = await asyncio.wait_for(asyncio.to_thread(generate), timeout=settings.gemini_timeout_seconds)
        text = getattr(response, "text", None)
        if not isinstance(text, str):
            _failure_reason.set("Unexpected Gemini response")
            return None
        return text
    except TimeoutError:
        _failure_reason.set("Timeout")
        return None
    except Exception as error:  # The SDK exposes provider-specific exception types.
        _failure_reason.set(_failure_for(error))
        return None
