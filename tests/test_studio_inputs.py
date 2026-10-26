"""CV allocation sees the same job context for pasted and uploaded documents."""
import importlib.util
import asyncio
import json
from pathlib import Path

from fastapi.testclient import TestClient
import httpx
import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "course_input_studio", ROOT / "system/services/studio/studio.py"
)
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)


@pytest.fixture
def submission(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, "INBOX_DIR", tmp_path)
    monkeypatch.setattr(studio, "ENABLED_WORKFLOWS", ["cv-fit", "cv-fit-interview"])
    submitted = []

    async def planner(body):
        submitted.append(body)
        return {"trace_id": "fixture-run", "status": "completed"}

    monkeypatch.setattr(studio, "_post_planner_intent", planner)
    # No lifespan: these input checks must not open registry/planner SSE feeds.
    client = TestClient(studio.app, raise_server_exceptions=True)
    yield client, submitted
    client.close()


def document_reader(monkeypatch, extracted_text, *, status=200):
    requests = []

    def handle(request):
        requests.append(request)
        if request.method == "GET":
            assert request.url.params["id"] == "tool-document-text"
            return httpx.Response(200, json={"endpoint": "http://reader.fixture/invoke"})
        assert str(request.url) == "http://reader.fixture/invoke?capability=tool-document-text"
        body = json.loads(request.content)
        assert Path(body["inputs"]["path"]).is_file()
        return httpx.Response(status, json={"outputs": {"text": extracted_text}})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        studio.httpx, "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    return requests


@pytest.mark.parametrize("kind", ["cv-fit", "cv-fit-interview"])
def test_paste_and_upload_use_identical_job_description_context(submission, monkeypatch, kind):
    client, submitted = submission
    job = "Senior data engineer\nProduction SQL, data pipelines and reliability."
    requests = document_reader(monkeypatch, job)
    pasted = client.post("/api/intent", json={
        "kind": kind, "inputs": {"cv_text": "Synthetic CV", "jd_text": job},
    })
    assert pasted.status_code == 200
    assert requests == []
    uploaded = client.post("/api/intent", data={"kind": kind, "cv_text": "Synthetic CV"},
                           files={"jd_file": ("role.txt", job, "text/plain")})
    assert uploaded.status_code == 200
    assert [body["selection_context"] for body in submitted] == [job, job]
    assert len(requests) == 2
    assert Path(submitted[1]["inputs"]["jd_path"]).read_text() == job


def test_explicit_emphasis_takes_precedence_without_document_call(submission, monkeypatch):
    client, submitted = submission
    requests = document_reader(monkeypatch, "Job description")
    response = client.post("/api/intent", data={
        "cv_text": "Synthetic CV", "allocation_brief": "Focus on accessibility",
    }, files={"jd_file": ("role.pdf", b"original PDF bytes", "application/pdf")})
    assert response.status_code == 200
    assert submitted[0]["selection_context"] == "Focus on accessibility"
    assert requests == []
    assert Path(submitted[0]["inputs"]["jd_path"]).read_bytes() == b"original PDF bytes"


def test_whitespace_emphasis_does_not_hide_uploaded_context(submission, monkeypatch):
    client, submitted = submission
    document_reader(monkeypatch, "Extracted PDF job description" + "x" * 17000)
    response = client.post("/api/intent", data={"cv_text": "CV", "allocation_brief": "  \n "},
                           files={"jd_file": ("role.pdf", b"PDF bytes", "application/pdf")})
    assert response.status_code == 200
    assert submitted[0]["selection_context"].startswith("Extracted PDF job description")
    assert len(submitted[0]["selection_context"]) == 16000


@pytest.mark.parametrize("text,status", [("", 200), ("\n ", 200), (None, 200), ("", 400), ("", 503)])
def test_unreadable_upload_does_not_silently_submit_generic_context(submission, monkeypatch, text, status):
    client, submitted = submission
    document_reader(monkeypatch, text, status=status)
    response = client.post("/api/intent", data={"cv_text": "Synthetic CV"},
                           files={"jd_file": ("role.pdf", b"unreadable", "application/pdf")})
    assert response.status_code == 422
    assert "paste the job description as text" in response.json()["error"]
    assert "No plan has been submitted" in response.json()["error"]
    assert submitted == []


def test_missing_job_description_stops_before_document_read_or_planner(submission, monkeypatch):
    client, submitted = submission
    requests = document_reader(monkeypatch, "unused")
    response = client.post("/api/intent", json={"inputs": {"cv_text": "Synthetic CV", "jd_text": " "}})
    assert response.status_code == 400
    assert requests == [] and submitted == []


@pytest.mark.parametrize("detail", [
    {"message": "evaluator-cv received 64.48%, below the configured 65% minimum.",
     "trace_id": "held-example", "task": "evaluate-cv-fit",
     "reason": "below-probability-threshold", "winner_probability": 0.6448,
     "minimum_probability": 0.65},
    "Allocation needs review or clarification; no AU was invoked",
])
def test_planner_hold_message_is_readable_and_keeps_structured_evidence(monkeypatch, detail):
    def handle(request):
        return httpx.Response(409, json={"detail": detail})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(studio.httpx, "AsyncClient",
                        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    response = asyncio.run(studio._post_planner_intent({"kind": "cv-fit"}))
    assert response.status_code == 409
    body = json.loads(response.body)
    assert body["error"] == (detail["message"] if isinstance(detail, dict) else detail)
    if isinstance(detail, dict):
        assert body["detail"] == detail
