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


def _allocate(client):
    return asyncio.run(planner._allocate_with_decision(client, WORKFLOW, {"kind": "cv-fit"}, TASK, CARDS))


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
