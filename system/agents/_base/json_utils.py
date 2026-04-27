"""Helpers for the prompt-then-parse pattern every Session 2 agent uses.

Agents ask the model to reply with JSON. The model usually obliges, sometimes
inside a ```json``` code fence, sometimes with prose around it. ``parse_json``
finds the JSON block and parses it, returning an error string instead of
raising so the agent can convert the failure into a normal error envelope
that shows up cleanly in the studio's trace pane.
"""
from __future__ import annotations

import json
import re
from typing import Any


_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)


def parse_json(text: str) -> tuple[Any, str | None]:
    """Try to extract a JSON value from ``text``.

    Returns ``(value, None)`` on success or ``(None, message)`` on failure.
    The error message names what was attempted so the trace pane reads well.
    """
    if not text or not text.strip():
        return None, "model returned an empty response"

    # First try the whole string as-is.
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        pass

    # Then the contents of a ```json``` fence.
    match = _FENCE_RE.search(text)
    if match:
        try:
            return json.loads(match.group(1)), None
        except json.JSONDecodeError as e:
            return None, f"could not parse JSON inside code fence: {e}"

    # Finally, the largest balanced {...} or [...] in the response.
    block = _largest_balanced(text)
    if block is not None:
        try:
            return json.loads(block), None
        except json.JSONDecodeError as e:
            return None, f"could not parse extracted JSON block: {e}"

    return None, "no JSON object or array found in model response"


def _largest_balanced(text: str) -> str | None:
    """Find the largest balanced {...} or [...] substring in ``text``."""
    best: str | None = None
    for opener, closer in [("{", "}"), ("[", "]")]:
        depth = 0
        start = -1
        for i, ch in enumerate(text):
            if ch == opener:
                if depth == 0:
                    start = i
                depth += 1
            elif ch == closer and depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    candidate = text[start : i + 1]
                    if best is None or len(candidate) > len(best):
                        best = candidate
                    start = -1
    return best


def error_envelope(message: str, *, signal: str = "valid_output_shape") -> dict[str, Any]:
    """Standard shape for an agent that couldn't produce a valid response."""
    return {
        "outputs": {"error": message},
        "signals": {signal: False, "error": message},
    }
