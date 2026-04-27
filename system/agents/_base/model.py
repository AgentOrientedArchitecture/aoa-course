"""Thin wrapper around the configured model provider.

Agents call ``model.complete(prompt, **opts)`` and don't know which provider
is behind it. The provider is chosen by the ``PROVIDER`` env var; the model
name comes from ``MODEL``. Hosted OpenAI-compatible endpoints can be selected
with ``OPENAI_BASE_URL``. Switching model or hosting location is a ``.env``
change.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class Completion:
    """A single model completion together with usage metadata."""

    text: str
    model: str
    provider: str
    latency_seconds: float
    raw: dict[str, Any]


class Model:
    """Provider-agnostic completion interface.

    The provider is selected at construction time from the env. All providers
    expose the same ``complete(prompt)`` signature; their internals differ.
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.provider = (provider or os.environ.get("PROVIDER", "openai")).lower()
        self.model = model or os.environ.get("MODEL", "")
        if not self.model:
            raise RuntimeError(
                "MODEL env var is not set. See system/.env.example for guidance."
            )
        self.timeout_seconds = (
            float(os.environ.get("MODEL_TIMEOUT_SECONDS", "180"))
            if timeout_seconds is None
            else timeout_seconds
        )
        self._client: Any = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> Completion:
        """Run a single completion and return text + usage."""
        import time

        start = time.perf_counter()
        if self.provider == "openai":
            text, raw = self._complete_openai(prompt, system, temperature, max_tokens)
        elif self.provider == "anthropic":
            text, raw = self._complete_anthropic(prompt, system, temperature, max_tokens)
        elif self.provider == "ollama":
            text, raw = self._complete_ollama(prompt, system, temperature, max_tokens)
        else:
            raise RuntimeError(f"Unknown PROVIDER: {self.provider!r}")
        latency = time.perf_counter() - start
        return Completion(
            text=text,
            model=self.model,
            provider=self.provider,
            latency_seconds=latency,
            raw=raw,
        )

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------
    def _complete_openai(
        self, prompt: str, system: str | None, temperature: float, max_tokens: int
    ) -> tuple[str, dict[str, Any]]:
        from openai import OpenAI  # type: ignore[import-untyped]

        if self._client is None:
            base_url = os.environ.get("OPENAI_BASE_URL") or None
            self._client = OpenAI(timeout=self.timeout_seconds, base_url=base_url)
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = resp.choices[0].message.content or ""
        return text, resp.model_dump()

    def _complete_anthropic(
        self, prompt: str, system: str | None, temperature: float, max_tokens: int
    ) -> tuple[str, dict[str, Any]]:
        from anthropic import Anthropic  # type: ignore[import-untyped]

        if self._client is None:
            self._client = Anthropic(timeout=self.timeout_seconds)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        resp = self._client.messages.create(**kwargs)
        # Anthropic returns a list of content blocks; concatenate text blocks.
        text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        return "".join(text_parts), resp.model_dump()

    def _complete_ollama(
        self, prompt: str, system: str | None, temperature: float, max_tokens: int
    ) -> tuple[str, dict[str, Any]]:
        host = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            payload["system"] = system
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(f"{host}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("response", ""), data
