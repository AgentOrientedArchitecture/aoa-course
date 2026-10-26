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
        evidence.update({"outcome": "no-eligible-capability", "reason": "no-eligible-capability", "model_called": False})
        evidence["message"] = _allocation_hold_message(evidence)
        return None, evidence
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
    minimum_probability = float(os.getenv("DECISION_MIN_PROBABILITY", "0.65"))
    accepted = bool(chosen) and (probability is not None and probability >= minimum_probability or probability is None and unscored_allowed)
    evidence.update({"model_called": True, "decision": answer, "choice": answer.get("choice"), "minimum_probability": minimum_probability, "unscored_allowed": unscored_allowed, "outcome": "proposed" if accepted else "selection-held"})
    if not accepted:
        if answer.get("choice") == "no_suitable_capability":
            evidence["reason"] = "no-suitable-capability"
        elif chosen is None:
            evidence["reason"] = "unrecognised-choice"
        elif probability is None:
            evidence["reason"] = "unscored-decision-not-allowed"
        else:
            evidence["reason"] = "below-probability-threshold"
        evidence["message"] = _allocation_hold_message(evidence)
    return chosen["card"] if accepted else None, evidence


def _allocation_hold_message(evidence):
    reason = evidence.get("reason", evidence.get("outcome"))
    task = evidence.get("task")
    choice = evidence.get("choice")
    probability = (evidence.get("decision") or {}).get("winner_probability")
    minimum = evidence.get("minimum_probability")
    if reason == "no-eligible-capability":
        explanation = "No approved AU matches the required input/output contract."
    elif reason == "no-suitable-capability":
        explanation = "The decision model found no suitable capability among the eligible AUs."
    elif reason == "below-probability-threshold":
        reported_percent, minimum_percent = f"{probability * 100:g}", f"{minimum * 100:g}"
        precision = f" (reported probability {probability} < {minimum})" if reported_percent == minimum_percent else ""
        explanation = f"{choice} received {reported_percent}%, below the configured {minimum_percent}% minimum{precision}."
    elif reason == "unscored-decision-not-allowed":
        explanation = "The decision has no reported probability and unscored decisions are not permitted."
    else:
        explanation = "The returned choice could not be accepted; inspect the recorded allocation evidence."
    return f"Allocation held for {task}: {explanation} No AU was invoked."


def allocation_hold_detail(trace_id, evidence):
    """Expose the recorded policy result without including task input or card data."""
    return {
        "message": _allocation_hold_message(evidence),
        "trace_id": trace_id,
        "task": evidence.get("task"),
        "reason": evidence.get("reason", evidence.get("outcome")),
        "choice": evidence.get("choice"),
        "winner_probability": (evidence.get("decision") or {}).get("winner_probability"),
        "minimum_probability": evidence.get("minimum_probability"),
    }
