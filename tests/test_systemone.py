"""Native local decision protocol and existing provider isolation."""
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path

import httpx
import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("systemone_decision", ROOT / "system/services/decision/decision.py")
decision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decision)

REQUEST = {
    "state": {"task": "Assess production data pipelines", "selection_context": "Data reliability"},
    "instructions": "Choose the best declared fit, or abstain if neither fits.",
    "criteria": {"data": "Data engineering assessment", "no_suitable_capability": "None fits"},
}
ANSWER = {"choice": "data", "probabilities": {"data": 0.9, "no_suitable_capability": 0.1}, "confidence": 0.6}


@pytest.fixture(autouse=True)
def isolated_configuration(monkeypatch):
    for key in ("DECISION_PROVIDER", "DECISION_MODEL", "DECISION_BASE_URL", "DECISION_API_KEY", "TYPESAFE_API_KEY", "OLLAMA_HOST"):
        monkeypatch.delenv(key, raising=False)


def call(handler):
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await decision.decide(REQUEST, client)
    return asyncio.run(exercise())


def test_local_systemone_native_contract_and_provenance(monkeypatch):
    monkeypatch.setenv("DECISION_PROVIDER", "systemone")
    monkeypatch.setenv("TYPESAFE_API_KEY", "hosted-test-key-must-stay-private")
    def handler(request):
        assert request.method == "POST"
        assert str(request.url) == "http://host.docker.internal:11434/v1/systemone"
        assert "authorization" not in request.headers
        assert json.loads(request.content) == {
            "model": "clef-flash", "state": REQUEST["state"],
            "questions": {"decision": {"type": "choice", "instructions": REQUEST["instructions"], "criteria": REQUEST["criteria"]}},
        }
        return httpx.Response(200, json={"model": "clef-flash:9b-q8_0", "answers": {"decision": ANSWER}, "usage": {"input_tokens": 80, "output_tokens": 1}})
    result = call(handler)
    assert result["provider"] == "systemone"
    assert result["model"] == "clef-flash:9b-q8_0"
    assert result["probability_semantics"] == "provider_reported"
    assert result["probabilities"] == ANSWER["probabilities"]
    assert result["winner_probability"] == 0.9
    assert result["provider_confidence"] == 0.6
    assert result["usage"] == {"input_tokens": 80, "output_tokens": 1}
    assert result["estimated_cost_usd"] is None
    assert result["price_basis"] == "not estimated"
    assert result["input_sha256"] == hashlib.sha256(json.dumps(REQUEST, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def test_local_systemone_custom_endpoint_model_and_optional_auth(monkeypatch):
    monkeypatch.setenv("DECISION_PROVIDER", "systemone")
    monkeypatch.setenv("DECISION_MODEL", "clef-flash-oQ4e")
    monkeypatch.setenv("DECISION_BASE_URL", "http://127.0.0.1:8000/")
    monkeypatch.setenv("DECISION_API_KEY", "local-test-key")
    monkeypatch.setenv("TYPESAFE_API_KEY", "different-hosted-test-key")
    def handler(request):
        assert str(request.url) == "http://127.0.0.1:8000/v1/systemone"
        assert request.headers["authorization"] == "Bearer local-test-key"
        assert json.loads(request.content)["model"] == "clef-flash-oQ4e"
        return httpx.Response(200, json={"answers": {"decision": ANSWER}})
    assert call(handler)["model"] == "clef-flash-oQ4e"


@pytest.mark.parametrize("answer", [
    {"choice": "invented", "probabilities": ANSWER["probabilities"]},
    {"choice": "data"},
    {"choice": "data", "probabilities": {"data": 1.0}},
    {"choice": "data", "probabilities": {"data": 0.8, "no_suitable_capability": 0.8}},
    {"choice": "data", "probabilities": {"data": 0.1, "no_suitable_capability": 0.9}},
])
def test_local_systemone_rejects_invalid_choices_and_distributions(monkeypatch, answer):
    monkeypatch.setenv("DECISION_PROVIDER", "systemone")
    with pytest.raises(ValueError):
        call(lambda _: httpx.Response(200, json={"answers": {"decision": answer}}))


def test_unavailable_local_systemone_never_falls_back(monkeypatch):
    monkeypatch.setenv("DECISION_PROVIDER", "systemone")
    monkeypatch.setenv("TYPESAFE_API_KEY", "hosted-test-key")
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(503)
    with pytest.raises(httpx.HTTPStatusError):
        call(handler)
    assert calls == ["http://host.docker.internal:11434/v1/systemone"]


@pytest.mark.parametrize("provider,base,model,key", [
    ("typesafe", "https://api.typesafe.ai", "jev-1.13.0", "hosted-test-key"),
    ("kev", "http://host.docker.internal:8090", "gpt-oss:20b", "local-test-key"),
])
def test_existing_native_provider_defaults_and_auth_stay_unchanged(monkeypatch, provider, base, model, key):
    monkeypatch.setenv("DECISION_PROVIDER", provider)
    monkeypatch.setenv("TYPESAFE_API_KEY", "hosted-test-key")
    monkeypatch.setenv("DECISION_API_KEY", "local-test-key")
    def handler(request):
        assert str(request.url) == base + "/v1/systemone"
        assert request.headers["authorization"] == "Bearer " + key
        assert json.loads(request.content)["model"] == model
        return httpx.Response(200, json={"answers": {"decision": ANSWER}, "usage": {"input_tokens": 100}})
    result = call(handler)
    assert result["provider"] == provider
    assert result["probability_semantics"] == "provider_reported"
    if provider == "typesafe":
        assert result["estimated_cost_usd"] == 100 * 0.042 / 1_000_000
    else:
        assert result["estimated_cost_usd"] is None


def test_ollama_chat_baseline_remains_unscored(monkeypatch):
    monkeypatch.setenv("DECISION_PROVIDER", "ollama")
    def handler(request):
        assert str(request.url) == "http://host.docker.internal:11434/api/chat"
        body = json.loads(request.content)
        assert body["model"] == "gpt-oss:20b"
        assert body["format"]["properties"]["choice"]["enum"] == list(REQUEST["criteria"])
        return httpx.Response(200, json={"message": {"content": json.dumps(ANSWER)}, "prompt_eval_count": 80, "eval_count": 12})
    result = call(handler)
    assert result["choice"] == "data"
    assert result["probability_semantics"] == "unavailable"
    assert result["probabilities"] is None
    assert result["winner_probability"] is None
    assert result["provider_confidence"] is None
