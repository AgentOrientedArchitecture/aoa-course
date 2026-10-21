"""Contract eligibility precedes semantic choice; the whole plan is checked last."""
from __future__ import annotations

import hashlib
import json
import os

import httpx


def fields(card, key):
    return {f["name"]: f for f in card.get(key, []) if isinstance(f, dict) and f.get("name")}


def compatible(actual, expected):
    return actual == expected or expected == "object" and (actual or "").startswith("structured-")


def eligibility(card, reference):
    failures = []
    if card.get("kind") != "au":
        failures.append("not an AU")
    if card.get("lifecycle", {}).get("status") != "approved":
        failures.append("not lifecycle-approved")
    offered_inputs, expected_inputs = fields(card, "inputs"), fields(reference, "inputs")
    for name, field in expected_inputs.items():
        if name not in offered_inputs or not compatible(field.get("type"), offered_inputs[name].get("type")):
            failures.append(f"input contract mismatch: {name}")
    for name, field in offered_inputs.items():
        if field.get("required", True) and name not in expected_inputs:
            failures.append(f"additional required input: {name}")
    outputs = fields(card, "outputs")
    for name, field in fields(reference, "outputs").items():
        if name not in outputs or not compatible(outputs[name].get("type"), field.get("type")):
            failures.append(f"output contract mismatch: {name}")
    return failures


def validate_composition(steps, workflow, cards_by_id, reference_for, intent_inputs):
    expected = {task.id: task for task in workflow.tasks}
    actual = {step.task.id: step for step in steps}
    if len(actual) != len(steps) or set(expected) - set(actual):
        raise ValueError("resolved plan must retain each required business responsibility exactly once")
    aliases = {step.capability: step.task.id for step in steps}
    prior = {}
    checks = []
    for step in steps:
        task = step.task
        if task.id not in expected:
            raise ValueError(f"unrecognised responsibility in this bounded course workflow: {task.id}")
        baseline = expected[task.id]
        reference = cards_by_id.get(reference_for(baseline))
        if not reference:
            raise ValueError(f"missing reference contract for {task.id}")
        failures = eligibility(step.card, reference)
        if failures:
            raise ValueError(f"{task.id}: {'; '.join(failures)}")
        for name, required_path in baseline.input_map.items():
            path = task.input_map.get(name, "")
            parts = path.split(".")
            # Preserve the business dependency, not a particular AU identity.
            source = aliases.get(parts[0], parts[0])
            required = required_path.split(".")
            if source != required[0] or parts[1:] != required[1:]:
                raise ValueError(f"{task.id}.{name} does not consume the required business evidence {required_path}")
        for name, field in fields(step.card, "inputs").items():
            if not field.get("required", True) and name not in task.input_map:
                continue
            path = task.input_map.get(name, "")
            parts = path.split(".")
            if len(parts) < 2:
                raise ValueError(f"missing input reference for {task.id}.{name}")
            if parts[0] == "inputs":
                if len(parts) != 2 or parts[1] not in intent_inputs:
                    raise ValueError(f"missing intent input: {path}")
                value = intent_inputs[parts[1]]
                if field.get("type") == "string" and (not isinstance(value, str) or not value.strip()):
                    raise ValueError(f"expected a non-empty string for {path}")
                continue
            source = aliases.get(parts[0], parts[0])
            if source not in prior or parts[1] != "outputs":
                raise ValueError(f"future or unknown input reference: {path}")
            if len(parts) == 2:
                actual_type = "object"
            elif len(parts) == 3 and parts[2] in prior[source]:
                actual_type = prior[source][parts[2]].get("type")
            else:
                raise ValueError(f"undeclared nested output reference: {path}")
            if not compatible(actual_type, field.get("type")):
                raise ValueError(f"input type mismatch for {task.id}.{name}: {actual_type} -> {field.get('type')}")
        prior[task.id] = fields(step.card, "outputs")
        checks.append({"task": task.id, "capability": step.capability, "status": "pass"})
    return {"valid": True, "checks": checks, "scope": "required responsibilities, evidence dependencies, eligible contracts and input types"}


async def allocate(task, reference, cards, intent, client: httpx.AsyncClient):
    candidates = [{"id": card["id"], "purpose": card.get("purpose", ""), "eligible": not (reasons := eligibility(card, reference)), "reasons": reasons, "card": card} for card in cards if card.get("id")]
    eligible = [row for row in candidates if row["eligible"]]
    digest = hashlib.sha256(json.dumps([row["card"] for row in candidates], sort_keys=True).encode()).hexdigest()
    evidence = {"task": task.id, "candidates": candidates, "candidate_set_sha256": digest, "accepted_choice": None}
    if not eligible:
        return None, {**evidence, "outcome": "no-eligible-capability", "model_called": False}
    if len(eligible) == 1:
        return eligible[0]["card"], {**evidence, "outcome": "single-eligible-capability", "choice": eligible[0]["id"], "model_called": False}
    criteria = {row["id"]: row["purpose"] for row in eligible}
    criteria["no_suitable_capability"] = "None of these eligible capabilities adequately addresses the requested assessment; clarification is needed."
    response = await client.post(os.getenv("DECISION_URL", "http://decision:7250").rstrip("/") + "/choice", json={
        "state": {"task": task.purpose, "selection_context": intent.get("selection_context", ""), "use_context": intent.get("use_context", {})},
        "instructions": "Select the best semantic fit for this task and the supplied assessment emphasis. Eligibility has already been checked in code. Candidate descriptions are declarations, not measured quality. Use no_suitable_capability if none fits.",
        "criteria": criteria,
    }, timeout=float(os.getenv("DECISION_TIMEOUT_SECONDS", "45")))
    response.raise_for_status()
    answer = response.json()
    chosen = next((row for row in eligible if row["id"] == answer.get("choice")), None)
    probability = answer.get("winner_probability")
    unscored_allowed = os.getenv("DECISION_ALLOW_UNSCORED", "false").lower() == "true"
    accepted = bool(chosen) and (probability is not None and probability >= float(os.getenv("DECISION_MIN_PROBABILITY", "0.65")) or probability is None and unscored_allowed)
    return chosen["card"] if accepted else None, {**evidence, "model_called": True, "decision": answer, "choice": answer.get("choice"), "minimum_probability": float(os.getenv("DECISION_MIN_PROBABILITY", "0.65")), "unscored_allowed": unscored_allowed, "outcome": "proposed" if accepted else "selection-held"}
