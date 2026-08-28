import json
import os
import asyncio
from contextvars import ContextVar
from typing import Any

import httpx

from app.config import get_settings
from app.services.scoring import CustomerContext

_failure_reason: ContextVar[str | None] = ContextVar("claude_failure_reason", default=None)


def get_claude_failure_reason() -> str | None:
    return _failure_reason.get()


async def get_claude_recommendation(
    diagnosis: str,
    customer_context: CustomerContext,
    deterministic_action: str,
    http_client: httpx.AsyncClient | None = None,
) -> str | None:
    """Return raw JSON explanation from Claude, or None on configuration/API/timeout failure."""
    settings = get_settings()
    _failure_reason.set(None)
    simulation = os.getenv("CLAUDE_SIMULATE_FAILURE")
    if simulation == "invalid_json":
        return "{invalid-json"
    if simulation == "timeout":
        await asyncio.sleep(settings.claude_timeout_seconds)
        _failure_reason.set("Timeout")
        return None
    if simulation == "api_error":
        _failure_reason.set("Claude API error")
        return None
    if not settings.anthropic_api_key or not settings.claude_model:
        _failure_reason.set("Claude not configured")
        return None
    prompt = {
        "diagnosis": diagnosis,
        "customer_ltv_paise": customer_context.ltv_paise,
        "success_rate": round(customer_context.history_score, 3),
        "churn_signal": "churned" if customer_context.days_inactive > 60 else "at_risk" if customer_context.days_inactive > 30 else "active",
        "deterministic_recommended_action": deterministic_action,
        "instruction": "Explain the supplied deterministic action only. Do not choose, alter, or propose an action. Return strict JSON with reasoning (string), confidence (0..1), and alternatives_rejected ([{action, reason}]).",
    }
    payload = {"model": settings.claude_model, "max_tokens": 400, "messages": [{"role": "user", "content": json.dumps(prompt)}]}
    headers = {"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=settings.claude_timeout_seconds)
    try:
        response = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=settings.claude_timeout_seconds)
        response.raise_for_status()
        content = response.json().get("content", [])
        text = next((item.get("text") for item in content if item.get("type") == "text"), None)
        if not isinstance(text, str):
            _failure_reason.set("Claude API error")
            return None
        return text
    except httpx.TimeoutException:
        _failure_reason.set("Timeout")
        return None
    except (httpx.HTTPError, ValueError, KeyError):
        _failure_reason.set("Claude API error")
        return None
    finally:
        if owns_client:
            await client.aclose()
