"""HTTP client for talking to the registry service.

The registry is just an HTTP service with four endpoints:

- ``POST /register`` — register a capability card.
- ``POST /update``   — update an existing card (used on hot reload).
- ``GET  /find``     — look a capability up by id.
- ``GET  /list``     — list every registered capability.

This client wraps those endpoints with retries on boot, since agents start
up alongside the registry and need to wait for it to become ready.
"""
from __future__ import annotations

import os
import time
from typing import Any

import httpx


class RegistryClient:
    def __init__(
        self,
        base_url: str | None = None,
        boot_retry_seconds: float = 30.0,
        boot_retry_interval: float = 0.5,
    ) -> None:
        self.base_url = (base_url or os.environ.get("REGISTRY_URL", "http://registry:7100")).rstrip("/")
        self.boot_retry_seconds = boot_retry_seconds
        self.boot_retry_interval = boot_retry_interval

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=10.0)

    # ------------------------------------------------------------------
    # Boot-time helpers
    # ------------------------------------------------------------------
    def wait_until_ready(self) -> None:
        """Poll ``/healthz`` until the registry is reachable, or give up."""
        deadline = time.monotonic() + self.boot_retry_seconds
        last_err: Exception | None = None
        while time.monotonic() < deadline:
            try:
                with self._client() as c:
                    r = c.get("/healthz")
                    if r.status_code == 200:
                        return
            except Exception as e:  # noqa: BLE001
                last_err = e
            time.sleep(self.boot_retry_interval)
        raise RuntimeError(
            f"registry at {self.base_url} not ready after {self.boot_retry_seconds:.0f}s"
            f" (last error: {last_err!r})"
        )

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register(self, card: dict[str, Any]) -> None:
        with self._client() as c:
            r = c.post("/register", json=card)
            r.raise_for_status()

    def update(self, card: dict[str, Any]) -> None:
        with self._client() as c:
            r = c.post("/update", json=card)
            r.raise_for_status()

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------
    def find(self, capability_id: str) -> dict[str, Any] | None:
        with self._client() as c:
            r = c.get("/find", params={"id": capability_id})
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()

    def list_all(self) -> list[dict[str, Any]]:
        with self._client() as c:
            r = c.get("/list")
            r.raise_for_status()
            return r.json().get("capabilities", [])

    def wait_for_capabilities(self, ids: list[str], timeout_seconds: float = 30.0) -> None:
        """Wait until every id in ``ids`` is registered. Used for tools.yaml deps."""
        if not ids:
            return
        deadline = time.monotonic() + timeout_seconds
        remaining = set(ids)
        while remaining and time.monotonic() < deadline:
            present = {c["id"] for c in self.list_all()}
            remaining -= present
            if remaining:
                time.sleep(self.boot_retry_interval)
        if remaining:
            raise RuntimeError(
                f"capabilities not registered after {timeout_seconds:.0f}s: {sorted(remaining)}"
            )
