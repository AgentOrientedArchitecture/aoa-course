"""Probe a native local System One server through the real course callers.

This is a small synthetic compatibility/behaviour check, not calibration or an
end-to-end course rehearsal. No .env is read, no AU is invoked and no wiki store
is written. Example:

  python tests/check_local_decision.py --base-url http://127.0.0.1:11434 \
      --model clef-flash --output /tmp/clef-local-check.json

Optional authentication comes only from the explicitly named --api-key-env.
The report contains synthetic requests and responses, never request headers.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import time
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


allocation = load_module("local_probe_allocation", "system/services/planner/allocation.py")
wiki_decisions = load_module("local_probe_promotion", "system/agents/_base/decisions.py")
decision = load_module("local_probe_decision", "system/services/decision/decision.py")


def arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", required=True, help="Server root, without /v1/systemone")
    parser.add_argument("--model", required=True, help="Exact model ID advertised by the local server")
    parser.add_argument("--output", required=True, type=Path, help="New JSON evidence file; existing files are preserved")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--label", default="local-systemone")
    parser.add_argument("--api-key-env", help="Name of an environment variable containing this server's key")
    args = parser.parse_args()
    url = urlsplit(args.base_url)
    if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
        parser.error("--base-url must be an http(s) server root, without credentials, path, query or fragment")
    if not 1 <= args.repeats <= 20:
        parser.error("--repeats must be between 1 and 20")
    if not args.model.strip():
        parser.error("--model must be non-empty")
    if args.output.exists():
        parser.error("--output already exists; choose a new file to preserve earlier evidence")
    key = ""
    if args.api_key_env:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", args.api_key_env):
            parser.error("--api-key-env must name an environment variable, not contain a key")
        key = os.environ.get(args.api_key_env, "")
        if not key:
            parser.error("the environment variable named by --api-key-env is empty or missing")
    # Process-local settings only. Never inherit a hosted or unrelated key.
    os.environ.pop("DECISION_API_KEY", None)
    if key:
        os.environ["DECISION_API_KEY"] = key
    os.environ.update({
        "DECISION_PROVIDER": "systemone",
        "DECISION_BASE_URL": args.base_url.rstrip("/"),
        "DECISION_MODEL": args.model,
        "DECISION_URL": "http://in-process-decision",
        "DECISION_MIN_PROBABILITY": "0.65",
        "DECISION_ALLOW_UNSCORED": "false",
        "DECISION_TIMEOUT_SECONDS": "120",
    })
    return args


def source_note(identifier: str, title: str, text: str, summary: str):
    return {
        "title": title,
        "summary": summary,
        "candidate_concepts": [],
        "passages": [{"passage_id": identifier + "-p1", "quote": text, "why_it_matters": "Synthetic evidence for this local probe."}],
        "relationships": [],
        "open_questions": [],
    }


def fixtures():
    cv_purpose = "Score a structured CV against a job description."
    return [
        {"id": "au-data", "kind": "allocation", "purpose": cv_purpose,
         "emphasis": "Assess production data pipelines, SQL, data modelling, reliability and governance.",
         "expected_choices": ["evaluator-cv-data"], "expected_outcomes": ["evaluator-cv-data"]},
        {"id": "au-frontend", "kind": "allocation", "purpose": cv_purpose,
         "emphasis": "Assess frontend engineering, accessibility, design systems, browser performance and UI testing.",
         "expected_choices": ["evaluator-cv-frontend"], "expected_outcomes": ["evaluator-cv-frontend"]},
        {"id": "au-no-fit", "kind": "allocation",
         "purpose": "Generate a photorealistic product image from a text description.",
         "emphasis": "This is image generation. No CV, job description, candidate assessment or hiring work is requested.",
         "expected_choices": ["no_suitable_capability"], "expected_outcomes": [None]},
        {"id": "wiki-relevant", "kind": "promotion", "expected_choices": ["promote"], "expected_outcomes": ["promote"],
         "source_text": "In this synthetic AOA example, the registry stores each AU's accepted input and output contract. The planner filters incompatible capabilities before selecting among eligible AUs. An approved registration is a declared boundary, not proof that the AU's output is correct.",
         "title": "Contract eligibility in an AOA registry", "summary": "A concrete explanation of contract checks, AU selection and the limits of registration."},
        {"id": "wiki-fiction", "kind": "promotion", "expected_choices": ["reject"], "expected_outcomes": ["reject"],
         "source_text": "This is a fictional fairy tale: a talking teapot flew over a kingdom of sugar and asked a dragon to bake a birthday cake. It describes no software, agent architecture or operating practice.",
         "title": "The flying teapot", "summary": "A fictional fairy tale unrelated to agent-oriented architecture."},
        {"id": "wiki-unsupported", "kind": "promotion", "expected_choices": ["review", "reject"], "expected_outcomes": ["review", "reject"],
         "source_text": "Someone said a new agent architecture cut costs dramatically. No figures, measurement method, dates, implementation details or identifiable source were supplied. This assertion has not been verified.",
         "title": "An unsupported claim about agent cost savings", "summary": "A potentially relevant but unverified assertion with no supporting evidence or provenance."},
    ]


def safe_error(exc: Exception):
    # Provider response bodies and headers are deliberately not persisted.
    result = {"type": type(exc).__name__}
    if isinstance(exc, httpx.HTTPStatusError):
        result["http_status"] = exc.response.status_code
    elif isinstance(exc, (ValueError, KeyError, TypeError)):
        result["detail"] = "Request or response did not satisfy the course adapter contract."
    return result


def write_report(path: Path, report: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


async def run(args):
    cards = []
    for capability in ("cv", "cv-data", "cv-frontend"):
        card = yaml.safe_load((ROOT / f"system/agents/evaluator/capabilities/{capability}/capability-card.yaml").read_text())
        card["lifecycle"] = {"status": "approved"}
        cards.append(card)
    reference = deepcopy(cards[0])
    promotion_instructions = (ROOT / "system/agents/evaluator/capabilities/promote/instructions.md").read_text()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or "unavailable"
    report = {
        "schema_version": 1, "label": args.label,
        "started_at": datetime.now(timezone.utc).isoformat(), "commit": commit,
        "implementation_sha256": {
            relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            for relative in (
                "system/services/decision/decision.py",
                "system/services/planner/allocation.py",
                "system/agents/_base/decisions.py",
            )
        },
        "base_url": args.base_url.rstrip("/"), "provider": "systemone", "requested_model": args.model,
        "repeats": args.repeats, "minimum_probability": 0.65, "unscored_allowed": False,
        "scope": "Six synthetic cases through actual allocate(), promote() and decide(); no parser, AU execution, whole-plan validation or wiki publication.",
        "limits": [
            "Expected outcomes are hand-authored discussion expectations, not a held-out calibration dataset.",
            "The no-fit allocation uses the CV reference contract to isolate semantic rejection; it is not an executable image-generation plan.",
            "accepted_au means passed the allocation caller's probability gate, not final whole-plan authorisation.",
            "First-load, cache, candidate order and concurrent server work affect timing; this is not a throughput benchmark.",
            "Model confidence and winning probability do not establish semantic correctness.",
        ], "results": [],
    }
    current = None

    async def capture_wire(request):
        if current is not None:
            current["native_requests"].append(json.loads(await request.aread()))

    async with httpx.AsyncClient(timeout=120, trust_env=False, event_hooks={"request": [capture_wire]}) as live_client:
        async def route(request):
            if request.url.host != "in-process-decision" or request.url.path != "/choice":
                raise AssertionError("Unexpected caller request in the local probe")
            body = json.loads(request.content)
            current["decision_request"] = deepcopy(body)
            answer = await decision.decide(body, live_client)
            current["normalised_answer"] = deepcopy(answer)
            return httpx.Response(200, json=answer)

        async with httpx.AsyncClient(transport=httpx.MockTransport(route), trust_env=False) as course_client:
            for repeat in range(args.repeats):
                ordered_cards = deepcopy(cards if repeat % 2 == 0 else list(reversed(cards)))
                for case in fixtures():
                    current = {"case_id": case["id"], "kind": case["kind"], "repeat": repeat + 1,
                               "sequence_index": len(report["results"]) + 1,
                               "expected_choices": case["expected_choices"], "expected_outcomes": case["expected_outcomes"],
                               "native_requests": []}
                    started = time.perf_counter()
                    try:
                        if case["kind"] == "allocation":
                            current["candidate_order"] = [card["id"] for card in ordered_cards]
                            task = SimpleNamespace(id="evaluate-cv-fit", purpose=case["purpose"])
                            selected, evidence = await allocation.allocate(task, reference, ordered_cards,
                                {"selection_context": case["emphasis"], "use_context": {"purpose": "synthetic local compatibility probe"}}, course_client)
                            observed = selected["id"] if selected else None
                            current.update({"accepted_au": observed, "allocation_evidence": evidence})
                        else:
                            parsed = source_note(case["id"], case["title"], case["source_text"], case["summary"])
                            current["source_text"] = case["source_text"]
                            current["pre_parsed_note"] = deepcopy(parsed)
                            result = await wiki_decisions.promote(parsed, "synthetic/" + case["id"] + ".txt", promotion_instructions, course_client)
                            observed = result["outputs"]["promotion"]["decision_outcome"]
                            current.update({"promotion_outcome": observed, "promotion_result": result})
                        chosen = current["normalised_answer"]["choice"]
                        current.update({"observed_choice": chosen, "observed_outcome": observed,
                                        "choice_matches_expectation": chosen in case["expected_choices"],
                                        "outcome_matches_expectation": observed in case["expected_outcomes"]})
                        current["matches_expectation"] = current["choice_matches_expectation"] and current["outcome_matches_expectation"]
                    except Exception as exc:
                        current["error"] = safe_error(exc)
                        current["matches_expectation"] = False
                    current["caller_elapsed_seconds"] = time.perf_counter() - started
                    report["results"].append(current)
                    write_report(args.output, report)
                    status = "MATCH" if current["matches_expectation"] else "ERROR" if "error" in current else "MISMATCH"
                    print(f"{status}: repeat {repeat + 1} {case['id']}; choice={current.get('observed_choice', 'unavailable')}; outcome={current.get('observed_outcome', 'unavailable')}", flush=True)
    answers = [row["normalised_answer"] for row in report["results"] if "normalised_answer" in row]
    latencies = [answer["latency_seconds"] for answer in answers]
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["summary"] = {
        "cases_run": len(report["results"]), "normalised_responses": len(answers),
        "expectation_matches": sum(row["matches_expectation"] for row in report["results"]),
        "errors": sum("error" in row for row in report["results"]),
        "all_expectations_met": all(row["matches_expectation"] for row in report["results"]),
        "observed_models": sorted({answer["model"] for answer in answers}),
        "decision_latency_seconds": {"min": min(latencies), "median": statistics.median(latencies), "max": max(latencies)} if latencies else None,
        "interpretation": "Small repeated synthetic probe, not calibration, a quality benchmark or a full course rehearsal.",
    }
    report["synthetic_fixture_sha256"] = hashlib.sha256(json.dumps(fixtures(), sort_keys=True).encode()).hexdigest()
    write_report(args.output, report)
    print(json.dumps(report["summary"], indent=2), flush=True)
    print(f"Evidence saved to {args.output}", flush=True)
    return 0 if report["summary"]["all_expectations_met"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(arguments())))
