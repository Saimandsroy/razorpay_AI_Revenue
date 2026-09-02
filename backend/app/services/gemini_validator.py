"""Validation for the bounded Gemini reasoning response.

The response is explanation-only. No action or policy field is accepted from
Gemini, so the deterministic engine remains authoritative.
"""
import json
from typing import Any


REQUIRED_FIELDS = {"reasoning", "confidence", "alternatives_rejected"}


def validate_gemini_output(response: str | dict[str, Any] | None) -> tuple[bool, dict[str, Any] | None]:
    if response is None:
        return False, None
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            return False, None
    if not isinstance(response, dict) or not REQUIRED_FIELDS.issubset(response):
        return False, None
    if not isinstance(response["reasoning"], str) or not response["reasoning"].strip():
        return False, None
    confidence = response["confidence"]
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        return False, None
    alternatives = response["alternatives_rejected"]
    if not isinstance(alternatives, list) or any(
        not isinstance(item, dict) or not isinstance(item.get("action"), str) or not isinstance(item.get("reason"), str)
        for item in alternatives
    ):
        return False, None
    return True, {
        "reasoning": response["reasoning"].strip(),
        "confidence": float(confidence),
        "alternatives_rejected": alternatives,
    }
