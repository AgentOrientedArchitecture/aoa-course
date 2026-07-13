"""Smoke-test the configured provider through the course's real model adapter."""
from __future__ import annotations

import json
import os
import sys
from typing import cast
from urllib.parse import urlsplit, urlunsplit

from _base.model import Model


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _endpoint(provider: str) -> str:
    if provider == "openai":
        base_url = os.environ.get("OPENAI_BASE_URL", "").strip()
        return _join_url(base_url or "https://api.openai.com/v1", "chat/completions")
    if provider == "ollama":
        host = os.environ.get("OLLAMA_HOST", "http://ollama:11434").strip()
        return _join_url(host, "api/chat")
    if provider == "anthropic":
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "").strip()
        return _join_url(base_url or "https://api.anthropic.com", "v1/messages")
    return "<unknown provider>"


def _public_url(url: str) -> str:
    """Remove credentials, query strings, and fragments before displaying a URL."""
    try:
        parts = urlsplit(url)
        if not parts.scheme or not parts.hostname:
            return "<invalid endpoint>"
        hostname = parts.hostname
        if ":" in hostname:
            hostname = f"[{hostname}]"
        netloc = hostname
        if parts.port is not None:
            netloc = f"{netloc}:{parts.port}"
        return urlunsplit((parts.scheme, netloc, parts.path, "", ""))
    except ValueError:
        return "<invalid endpoint>"


def _configuration_error(provider: str, model: str) -> str | None:
    if not model:
        return "MODEL is not set"
    if provider == "openai":
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            return "AOA_OPENAI_API_KEY is not set for PROVIDER=openai"
        return None
    if provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
            return "ANTHROPIC_API_KEY is not set for PROVIDER=anthropic"
        return None
    if provider == "ollama":
        if not os.environ.get("OLLAMA_HOST", "http://ollama:11434").strip():
            return "OLLAMA_HOST is empty for PROVIDER=ollama"
        return None
    return f"unsupported PROVIDER={provider!r}; use openai, ollama, or anthropic"


def _safe_error(exc: Exception) -> str:
    message = " ".join(str(exc).split()) or "no error details returned"
    for variable in (
        "OPENAI_API_KEY",
        "AOA_OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        secret = os.environ.get(variable, "")
        if secret:
            message = message.replace(secret, "[redacted]")
    return message[:500]


def _failure_hint(provider: str) -> str:
    if provider == "ollama":
        host = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
        if urlsplit(host).hostname == "ollama":
            return (
                "OLLAMA_HOST points to the bundled Ollama service. Start it with "
                "'docker compose --env-file .env -f system/docker-compose.yml "
                "--profile local up -d ollama', ensure MODEL is pulled there, and retry."
            )
        return (
            "Confirm Ollama is running, MODEL appears in 'ollama list', and "
            "OLLAMA_HOST is reachable from Docker (normally "
            "http://host.docker.internal:11434 for host Ollama)."
        )
    if provider == "openai":
        return (
            "Check AOA_OPENAI_API_KEY, the provider's exact MODEL id, and that "
            "OPENAI_BASE_URL is the API root ending in /v1 rather than "
            "/chat/completions."
        )
    if provider == "anthropic":
        return "Check ANTHROPIC_API_KEY, the exact MODEL id, and provider access."
    return "Check PROVIDER and MODEL in .env."


def main() -> int:
    provider = os.environ.get("PROVIDER", "openai").strip().lower()
    model_name = os.environ.get("MODEL", "").strip()
    endpoint = _public_url(_endpoint(provider))

    print("Model provider smoke test")
    print(f"provider={provider or '<empty>'}")
    print(f"model={model_name or '<empty>'}")
    print(f"endpoint={endpoint}")

    configuration_error = _configuration_error(provider, model_name)
    if configuration_error:
        print(f"error={configuration_error}", file=sys.stderr)
        print(f"hint={_failure_hint(provider)}", file=sys.stderr)
        return 1

    try:
        completion = Model(provider=provider, model=model_name).complete(
            'Return exactly this JSON object and no other text: {"ok":true}',
            system="Return only valid JSON. Do not use Markdown or add commentary.",
            temperature=0,
            max_tokens=1024,
        )
    except KeyboardInterrupt:
        print("error=model request interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(
            f"error=model request failed ({type(exc).__name__}): {_safe_error(exc)}",
            file=sys.stderr,
        )
        print(f"hint={_failure_hint(provider)}", file=sys.stderr)
        return 1

    preview = " ".join(completion.text.split())[:200]
    print(f"latency_seconds={completion.latency_seconds:.3f}")
    print(f"content_preview={json.dumps(preview)}")

    try:
        payload = cast(object, json.loads(completion.text))
    except json.JSONDecodeError as exc:
        print(
            f"error=model was reachable but returned invalid JSON: {exc.msg}",
            file=sys.stderr,
        )
        hint = "hint=Use a model with reliable JSON output or adjust the provider's "
        hint += "response-format settings in .env."
        print(hint, file=sys.stderr)
        return 1

    if not isinstance(payload, dict):
        print(
            'error=model JSON must be an object containing "ok": true',
            file=sys.stderr,
        )
        return 1

    result = cast(dict[str, object], payload)
    if result.get("ok") is not True:
        print(
            'error=model JSON must be an object containing "ok": true',
            file=sys.stderr,
        )
        return 1

    print("result=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
