"""Unit tests for the decision allocator (run: python -m pytest system/services/planner/test_allocator.py).

The decision service is replaced by a fake client so the tests cover the planner's own logic: the
candidate criteria it sends, the proceed / review / gap thresholds, and the trace-shaped result.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("PLANNER_TRACES_DIR", "/tmp/aoa-planner-tests")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import planner  # noqa: E402


CARDS = [
    {"id": "parser-cv", "kind": "au", "purpose": "Read a CV and return a structured representation.", "lifecycle": {"status": "approved"}},
    {"id": "evaluator-cv", "kind": "au", "purpose": "Score a parsed CV against a job description.", "lifecycle": {"status": "approved"}},
    {"id": "reporter-cv-fit", "kind": "au", "purpose": "Turn a parsed CV and an evaluation into a short report.", "lifecycle": {"status": "approved"}},
    {"id": "evaluator-old", "kind": "au", "purpose": "Deprecated.", "lifecycle": {"status": "deprecated"}},
]
TASK = planner.TaskSpec(id="evaluate-cv-fit", purpose="Score a structured CV against a job description.",
                        discovery={"kind": "au", "text": "score"}, input_map={})
WORKFLOW = planner.WORKFLOWS["cv-fit"]


class FakeClient:
    """Answers the agent question with a fixed distribution and the fit question with a fixed value."""

    def __init__(self, probabilities: dict[str, float], fit: float = 0.9):
        self.probabilities = probabilities
        self.fit = fit
        self.requests: list[dict] = []

    async def post(self, url, json, timeout):  # noqa: A002
        self.requests.append(json)
        question = next(iter(json["questions"].values()))
        if question["type"] == "choice":
            best = max(self.probabilities, key=self.probabilities.get)
            k = len(question["criteria"])
            confidence = (self.probabilities[best] - 1 / k) / (1 - 1 / k)
            answers = {"agent": {"type": "choice", "choice": best, "confidence": confidence, "probabilities": self.probabilities}}
        else:
            answers = {"fits": {"type": "noul", "noul": self.fit}}
        return _Response({"answers": answers})


class _Response:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self._body


def _allocate(client, proposed=None):
    async def fake_discover(_client, _query):
        return {"candidates": [{"score": 9.5, "reasons": ["input cv matched by name"], "card": CARDS[1]},
                               {"score": 2.0, "reasons": ["kind au"], "card": CARDS[0]}]}
    original = planner._registry_discover
    planner._registry_discover = fake_discover
    try:
        return asyncio.run(planner._allocate_with_decision(client, WORKFLOW, {"kind": "cv-fit"}, TASK, CARDS, proposed=proposed))
    finally:
        planner._registry_discover = original


def test_criteria_only_approved_cards_plus_escape():
    criteria = planner._decision_criteria(CARDS)
    assert set(criteria) == {"parser-cv", "evaluator-cv", "reporter-cv-fit", planner.DECISION_NONE}


def test_confident_choice_proceeds_and_ranks_candidates():
    client = FakeClient({"evaluator-cv": 0.9, "parser-cv": 0.05, "reporter-cv-fit": 0.04, "none_of_these": 0.01})
    candidates, query = _allocate(client)
    assert [c["card"]["id"] for c in candidates] == ["evaluator-cv", "parser-cv", "reporter-cv-fit"]
    assert candidates[0]["score"] == 0.9
    assert query["decision"]["outcome"] == "proceed"
    assert query["decision"]["fit"] == 0.9
    assert client.requests[0]["state"]["task"] == TASK.purpose
    assert len(client.requests) == 2  # agent question, then the fit question about the winner


def test_low_confidence_is_review_not_gap():
    client = FakeClient({"evaluator-cv": 0.5, "reporter-cv-fit": 0.4, "parser-cv": 0.05, "none_of_these": 0.05})
    candidates, query = _allocate(client)
    assert query["decision"]["outcome"] == "review"
    assert candidates[0]["card"]["id"] == "evaluator-cv"
    assert candidates[1]["card"]["id"] == "reporter-cv-fit"


def test_none_of_these_is_a_gap_with_no_candidates():
    client = FakeClient({"none_of_these": 0.8, "evaluator-cv": 0.1, "parser-cv": 0.05, "reporter-cv-fit": 0.05})
    candidates, query = _allocate(client)
    assert candidates == []
    assert query["decision"]["outcome"] == "gap"
    assert len(client.requests) == 1  # no fit question for a gap


def test_spread_probability_below_gap_floor_is_a_gap():
    client = FakeClient({"evaluator-cv": 0.3, "parser-cv": 0.3, "reporter-cv-fit": 0.3, "none_of_these": 0.1})
    candidates, query = _allocate(client)
    assert query["decision"]["outcome"] == "gap"
    assert candidates == []


def test_goal_prefers_intent_text_then_context():
    assert planner._allocation_goal(WORKFLOW, {"goal": "Is this candidate a fit?"}) == "Is this candidate a fit?"
    goal = planner._allocation_goal(WORKFLOW, {"use_context": {"domain": "employment", "output_use": "candidate-screening"}})
    assert goal == "workflow: cv-fit; domain: employment; output_use: candidate-screening"


# ---------------------------------------------------------------------------
# Stage 2: free-text goals
# ---------------------------------------------------------------------------

class FakeWorkflowClient(FakeClient):
    async def post(self, url, json, timeout):  # noqa: A002
        self.requests.append(json)
        best = max(self.probabilities, key=self.probabilities.get)
        k = len(json["questions"]["workflow"]["criteria"])
        confidence = (self.probabilities[best] - 1 / k) / (1 - 1 / k)
        return _Response({"answers": {"workflow": {"type": "choice", "choice": best, "confidence": confidence, "probabilities": self.probabilities}}, "latency_ms": 12})


def test_free_text_goal_is_classified_to_a_workflow():
    client = FakeWorkflowClient({"cv-fit": 0.9, "cv-fit-interview": 0.05, "knowledge-query": 0.03, "none_of_these": 0.02})
    c = asyncio.run(planner._classify_workflow(client, "Is this candidate a fit for the data engineer role?"))
    assert c["choice"] == "cv-fit" and c["outcome"] == "proceed" and c["latency_ms"] == 12
    assert set(client.requests[0]["questions"]["workflow"]["criteria"]) == set(planner.WORKFLOWS) | {planner.DECISION_NONE}


def test_off_topic_goal_is_a_gap():
    client = FakeWorkflowClient({"none_of_these": 0.85, "cv-fit": 0.1, "knowledge-query": 0.05})
    c = asyncio.run(planner._classify_workflow(client, "Book me a flight to Lisbon"))
    assert c["outcome"] == "gap"


def test_free_text_intent_detection_and_default_inputs():
    assert planner._is_free_text_intent({"kind": "auto", "goal": "x"})
    assert planner._is_free_text_intent({"goal": "x"})
    assert not planner._is_free_text_intent({"kind": "cv-fit", "inputs": {}})
    intent = {"goal": "What does the wiki say about registries?", "inputs": {}}
    planner._default_inputs_for(planner.WORKFLOWS["knowledge-query"], intent)
    assert intent["inputs"]["question"] == intent["goal"]


def test_free_text_plan_validation_is_structural():
    cards = {c["id"]: {**c, "inputs": [], "outputs": [{"name": "report_markdown"}]} for c in CARDS if c["id"] != "evaluator-old"}
    proposal = {"tasks": [{"id": "only", "purpose": "report", "capability": "reporter-cv-fit", "input_map": {}}]}
    tasks, validation = planner._validate_plan(proposal, {}, cards, WORKFLOW, strict_workflow=False)
    assert [t.id for t in tasks] == ["only"]
    assert validation["checks"][-1]["missing_workflow_tasks"] == ["evaluate-cv-fit", "parse-cv", "write-cv-fit-report"]
    try:
        planner._validate_plan(proposal, {}, cards, WORKFLOW, strict_workflow=True)
        raise AssertionError("strict validation should reject a plan missing workflow tasks")
    except ValueError:
        pass


def test_free_text_prompt_omits_the_requested_workflow_example():
    prompt = planner._build_planner_prompt(WORKFLOW, {"kind": "cv-fit", "free_text": True, "goal": "Is this candidate a fit?", "inputs": {"cv_path": "a", "jd_path": "b"}}, CARDS)
    assert '"workflow": "cv-fit"' not in prompt and '"goal": "Is this candidate a fit?"' in prompt
    strict = planner._build_planner_prompt(WORKFLOW, {"kind": "cv-fit", "inputs": {}}, CARDS)
    assert '"workflow": "cv-fit"' in strict


def test_counterfactuals_recorded_next_to_the_decision():
    client = FakeClient({"evaluator-cv": 0.9, "parser-cv": 0.05, "reporter-cv-fit": 0.04, "none_of_these": 0.01})
    _candidates, query = _allocate(client, proposed="evaluator-cv")
    cf = query["counterfactuals"]
    assert cf["planner_model"] == "evaluator-cv"
    assert cf["reference_plan"] == "evaluator-cv"
    assert [c["id"] for c in cf["registry_lexical"]] == ["evaluator-cv", "parser-cv"]
    assert cf["registry_lexical"][0]["score"] == 9.5
