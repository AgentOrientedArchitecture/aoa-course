"""Generic generation configuration reaches both AU and planner clients.

These tests use SDK doubles and an HTTP mock transport. No provider is called.
Ambient vendor variables deliberately contain different values so an implicit
SDK or planner fallback cannot silently pass the checks.
"""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS

import httpx
import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "system/agents"))
    monkeypatch.syspath_prepend(str(ROOT / "system/services/planner"))
    monkeypatch.setenv("DURABLE_CASES", "false")
    monkeypatch.setenv("MODEL", "fixture-model")
    for variable in ("LLM_API_KEY", "LLM_BASE_URL", "PROVIDER"):
        monkeypatch.delenv(variable, raising=False)
    for vendor in ("OPENAI", "ANTHROPIC", "CEREBRAS", "AOA_OPENAI"):
        monkeypatch.setenv(vendor + "_API_KEY", "ambient-vendor-key-not-for-use")
        monkeypatch.setenv(vendor + "_BASE_URL", "https://ambient-vendor.invalid")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "ambient-bearer-not-for-use")
    from _base import model, provider_test
    spec = importlib.util.spec_from_file_location("generation_config_planner", ROOT / "system/services/planner/planner.py")
    planner = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, planner)
    spec.loader.exec_module(planner)
    return NS(model=model, smoke=provider_test, planner=planner)


def sdk_double(monkeypatch, provider):
    recorded = {}
    if provider == "openai":
        raw = {"choices": [{"message": {"content": '{"ok":true}'}}]}
        response = NS(model_dump=lambda: raw)
    else:
        raw = {"content": [{"type": "text", "text": '{"ok":true}'}]}
        response = NS(model_dump=lambda: raw, content=[NS(type="text", text='{"ok":true}')])

    def create(**kwargs):
        recorded["request"] = kwargs
        return response

    def constructor(**kwargs):
        recorded["constructor"] = kwargs
        if provider == "openai":
            return NS(chat=NS(completions=NS(create=create)))
        return NS(messages=NS(create=create))

    monkeypatch.setitem(sys.modules, provider, NS(**{("OpenAI" if provider == "openai" else "Anthropic"): constructor}))
    return recorded


@pytest.mark.parametrize("provider,default", [
    ("openai", "https://api.openai.com/v1"),
    ("anthropic", "https://api.anthropic.com"),
])
@pytest.mark.parametrize("custom", [False, True])
def test_au_sdk_receives_explicit_generic_key_and_base(monkeypatch, modules, provider, default, custom):
    monkeypatch.setenv("LLM_API_KEY", "generic-generation-key")
    base = "https://generation.fixture.test/gateway" if custom else default
    if custom:
        monkeypatch.setenv("LLM_BASE_URL", base)
    calls = sdk_double(monkeypatch, provider)
    completion = modules.model.Model(provider=provider, timeout_seconds=17).complete("prompt", system="system", max_tokens=32)
    assert completion.text == '{"ok":true}'
    assert calls["constructor"]["api_key"] == "generic-generation-key"
    assert calls["constructor"]["base_url"] == base
    assert calls["constructor"]["timeout"] == 17
    if provider == "anthropic":
        assert calls["constructor"]["auth_token"] == ""
    assert calls["request"]["model"] == "fixture-model"
    assert calls["request"]["max_tokens"] == 32


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_au_rejects_missing_generic_key_despite_ambient_keys(monkeypatch, modules, provider):
    calls = sdk_double(monkeypatch, provider)
    with pytest.raises(RuntimeError, match=f"LLM_API_KEY is not set for PROVIDER={provider}"):
        modules.model.Model(provider=provider).complete("prompt")
    assert "constructor" not in calls


@pytest.mark.parametrize("provider,default,path", [
    ("openai", "https://api.openai.com/v1", "/chat/completions"),
    ("anthropic", "https://api.anthropic.com", "/v1/messages"),
])
@pytest.mark.parametrize("custom", [False, True])
def test_planner_uses_generic_endpoint_and_key_on_wire(monkeypatch, modules, provider, default, path, custom):
    monkeypatch.setenv("PROVIDER", provider)
    monkeypatch.setenv("LLM_API_KEY", "generic-generation-key")
    base = "https://generation.fixture.test/gateway" if custom else default
    if custom:
        monkeypatch.setenv("LLM_BASE_URL", base + "/")
    requests = []

    def handler(request):
        requests.append(request)
        assert str(request.url) == base + path
        assert json.loads(request.content)["model"] == "fixture-model"
        if provider == "openai":
            assert request.headers["authorization"] == "Bearer generic-generation-key"
            return httpx.Response(200, json={"choices": [{"message": {"content": '{"tasks":[]}'}}]})
        assert request.headers["x-api-key"] == "generic-generation-key"
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"content": [{"type": "text", "text": '{"tasks":[]}'}]})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(modules.planner.httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    text, _raw = asyncio.run(modules.planner._planner_model_complete("bounded task plan"))
    assert text == '{"tasks":[]}' and len(requests) == 1


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_planner_rejects_missing_generic_key_before_network(monkeypatch, modules, provider):
    monkeypatch.setenv("PROVIDER", provider)
    with pytest.raises(RuntimeError, match=f"LLM_API_KEY is not set for PROVIDER={provider}"):
        asyncio.run(modules.planner._planner_model_complete("bounded task plan"))


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_smoke_missing_key_diagnostic_is_generic(monkeypatch, modules, capsys, provider):
    monkeypatch.setenv("PROVIDER", provider)
    assert modules.smoke.main() == 1
    output = capsys.readouterr()
    assert f"LLM_API_KEY is not set for PROVIDER={provider}" in output.err
    assert "LLM_BASE_URL" in output.err
    assert "ambient-vendor" not in output.out + output.err


def test_smoke_endpoint_and_error_redaction(monkeypatch, modules):
    monkeypatch.setenv("LLM_API_KEY", "fixture-sensitive-value")
    monkeypatch.setenv("LLM_BASE_URL", "http://user:password@localhost:18000/v1?private=query#fragment")
    assert modules.smoke._public_url(modules.smoke._endpoint("openai")) == "http://localhost:18000/v1"
    assert modules.smoke._safe_error(RuntimeError("rejected fixture-sensitive-value")) == "rejected [redacted]"


def test_native_ollama_does_not_require_generic_key(monkeypatch, modules):
    monkeypatch.setenv("OLLAMA_HOST", "http://local-ollama.fixture:11434")
    assert modules.smoke._configuration_error("ollama", "fixture-model") is None
    assert modules.smoke._endpoint("ollama") == "http://local-ollama.fixture:11434/api/chat"
