"""evaluator agent.

Backs ``evaluator-cv`` for Session 1, plus wiki promotion and wiki-query
evidence evaluation for Session 2. The same Python process serves each through
capability-id dispatch in ``handle``.

For ``evaluator-cv`` we receive a parsed CV (the parser's output) and a path
to a job description on the shared inbox volume. We read the JD through
``tool-document-text`` so the call shows up in the trace, hand both to the
model with the rubric in ``instructions.md``, and return a JSON evaluation.
"""
from __future__ import annotations

import json

from _base.base import Context, run
from _base.json_utils import error_envelope, parse_json


SYSTEM_PROMPT = (
    "You are a hiring evaluator. You assess how well a candidate fits a job "
    "description. You always respond with a single JSON object - no "
    "preamble, no commentary, no code fence."
)

PROMOTE_SYSTEM_PROMPT = (
    "You are a knowledge promotion evaluator for an Agent-oriented Architecture "
    "wiki. You always respond with a single JSON object - no preamble, no "
    "commentary, no code fence."
)

WIKI_QUERY_SYSTEM_PROMPT = (
    "You are a wiki evidence evaluator. You always respond with a single JSON "
    "object - no preamble, no commentary, no code fence."
)


async def handle(capability_id: str, inputs: dict, ctx: Context) -> dict:
    if capability_id == "evaluator-cv":
        return await _evaluate_cv(inputs, ctx)
    if capability_id == "evaluator-promote":
        return await _promote_note(inputs, ctx)
    if capability_id == "evaluator-wiki-query":
        return await _evaluate_wiki_query(inputs, ctx)
    if capability_id == "evaluator-compliance":
        return await _evaluate_compliance(inputs, ctx)
    return error_envelope(f"evaluator does not back capability {capability_id!r}")


async def _evaluate_cv(inputs: dict, ctx: Context) -> dict:
    cv = inputs.get("cv")
    jd_path = inputs.get("jd_path")
    if not isinstance(cv, dict):
        return error_envelope("cv (parsed object) is required")
    if not jd_path:
        return error_envelope("jd_path is required")

    doc_text = ctx.tools.get("tool-document-text")
    if doc_text is None:
        return error_envelope("tool-document-text is not available")
    doc_outputs = await doc_text({"path": jd_path})
    jd_text = doc_outputs.get("text", "")
    if not jd_text.strip():
        return error_envelope(f"JD at {jd_path} was empty")

    prompt = (
        f"{ctx.skills}\n\n"
        f"## Job description\n\n{jd_text}\n\n"
        f"## Parsed CV\n\n```json\n{json.dumps(cv, indent=2)}\n```\n"
    )
    completion = ctx.model.complete(prompt, system=SYSTEM_PROMPT, temperature=0.1)
    evaluation, err = parse_json(completion.text)
    if err is not None:
        return error_envelope(err)
    if not isinstance(evaluation, dict):
        return error_envelope("evaluation must be a JSON object")

    scores = evaluation.get("scores")
    verdict = evaluation.get("verdict")
    return {
        "outputs": evaluation,
        "signals": {
            "valid_output_shape": True,
            "has_scores": isinstance(scores, dict) and len(scores) > 0,
            "has_verdict": verdict in {"strong", "fit", "weak", "no"},
            "latency_seconds": completion.latency_seconds,
        },
    }


async def _promote_note(inputs: dict, ctx: Context) -> dict:
    parsed_note = inputs.get("parsed_note")
    source_path = inputs.get("source_path")
    if not isinstance(parsed_note, dict):
        return error_envelope("parsed_note (object) is required")
    if not isinstance(source_path, str) or not source_path.strip():
        return error_envelope("source_path is required")

    prompt = (
        f"{ctx.skills}\n\n"
        f"## Source path\n\n{source_path}\n\n"
        f"## Parsed note\n\n```json\n{json.dumps(parsed_note, indent=2)}\n```\n"
    )
    completion = ctx.model.complete(prompt, system=PROMOTE_SYSTEM_PROMPT, temperature=0.1)
    promotion, err = parse_json(completion.text)
    if err is not None:
        return error_envelope(err)
    if not isinstance(promotion, dict):
        return error_envelope("promotion must be a JSON object")

    concepts = promotion.get("concepts")
    passages = promotion.get("promoted_passages")
    promote = promotion.get("promote", True)
    return {
        "outputs": {"promotion": promotion},
        "signals": {
            "valid_output_shape": True,
            "promote_decision": isinstance(promote, bool),
            "has_concepts": isinstance(concepts, list) and len(concepts) > 0,
            "has_promoted_passages": isinstance(passages, list) and len(passages) > 0,
            "latency_seconds": completion.latency_seconds,
        },
    }


async def _evaluate_wiki_query(inputs: dict, ctx: Context) -> dict:
    question = inputs.get("question")
    query = inputs.get("query")
    if not isinstance(question, str) or not question.strip():
        return error_envelope("question is required")
    if not isinstance(query, dict):
        return error_envelope("query object is required")

    wiki = ctx.tools.get("tool-wiki-store")
    if wiki is None:
        return error_envelope("tool-wiki-store is not available")
    search_text = " ".join(
        [question] + [str(term) for term in query.get("terms", []) if str(term).strip()]
    )
    search_outputs = await wiki({"op": "search", "query": search_text, "limit": 8})
    passages = search_outputs.get("passages", [])
    ranked = _rank_wiki_passages(passages)

    parsed_note = {
        "title": "Course wiki search results",
        "summary": f"Retrieved {len(passages)} passages from the course wiki.",
        "key_points": [],
        "entities": [],
        "candidate_concepts": query.get("terms", []),
        "passages": [
            {
                "passage_id": p.get("passage_id"),
                "quote": p.get("quote"),
                "why_it_matters": p.get("why_it_matters", ""),
                "source_path": p.get("source_path"),
            }
            for p in passages
            if isinstance(p, dict)
        ],
    }
    direct_answer_possible = bool(ranked and ranked[0].get("relevance", 0) >= 3)
    evaluation = {
        "ranked_passages": ranked,
        "direct_answer_possible": direct_answer_possible,
        "gaps": [] if direct_answer_possible else ["The wiki did not return enough cited passages to answer directly."],
        "rationale": (
            "Ranked deterministically from wiki-store retrieval scores; answer text must stay within returned passages."
        ),
        "parsed_note": parsed_note,
    }
    return {
        "outputs": evaluation,
        "signals": {
            "valid_output_shape": True,
            "has_ranked_passages": isinstance(ranked, list) and len(ranked) > 0,
            "passages_have_citations": all(
                isinstance(item, dict) and item.get("passage_id")
                for item in ranked
            ) if isinstance(ranked, list) else False,
            "latency_seconds": 0,
        },
    }


def _rank_wiki_passages(passages: object) -> list[dict]:
    """Convert wiki-store retrieval scores into evaluator output.

    The Session 2 query path is a grounding demo, so this capability keeps the
    ranking deterministic and citation-preserving instead of asking the model to
    judge sparse evidence.
    """
    if not isinstance(passages, list):
        return []
    ranked = []
    for passage in passages:
        if not isinstance(passage, dict) or not passage.get("passage_id"):
            continue
        score = int(passage.get("score") or 0)
        relevance = max(1, min(5, score))
        matched = passage.get("matched_terms") if isinstance(passage.get("matched_terms"), list) else []
        reason = (
            f"Matched wiki terms: {', '.join(str(term) for term in matched[:6])}."
            if matched
            else "Returned by wiki search."
        )
        ranked.append({
            "passage_id": passage["passage_id"],
            "relevance": relevance,
            "reason": reason,
        })
    ranked.sort(key=lambda item: (-item["relevance"], item["passage_id"]))
    return ranked

# ----------------------------------------------------------------------
# evaluator-compliance — EU AI Act obligation checks over an estate
# inventory. Deterministic checks + wiki-store retrieval for citations.
# Findings and evidence only; never a verdict.
# ----------------------------------------------------------------------

import time as _time

_ANNEX_III_MARKERS = (
    "recruit", "candidates", "candidate evaluation", " cv", "cv ",
    "curriculum vitae", "job description", "job applications", "interview",
    "employment", "hiring",
)

_ARTICLE_QUERIES = {
    "Annex III": "annex iii high-risk employment recruitment selection evaluate candidates",
    "Art 9": "article 9 risk management system identify evaluate risks",
    "Art 10": "article 10 data and data governance training validation testing",
    "Art 11": "article 11 technical documentation",
    "Art 12": "article 12 record-keeping automatic recording of events logs",
    "Art 13": "article 13 transparency and provision of information to deployers",
    "Art 14": "article 14 human oversight natural persons effectively overseen",
    "Art 72": "article 72 post-market monitoring plan providers",
}

_OBLIGATIONS = {
    "Art 9": "risk management system",
    "Art 10": "data and data governance",
    "Art 11": "technical documentation",
    "Art 12": "record-keeping",
    "Art 13": "transparency to deployers",
    "Art 14": "human oversight",
    "Art 72": "post-market monitoring",
}


async def _evaluate_compliance(inputs: dict, ctx: Context) -> dict:
    started = _time.monotonic()
    inventory = inputs.get("inventory")
    if not isinstance(inventory, list):
        return error_envelope("inventory (array) is required")

    wiki = ctx.tools.get("tool-wiki-store")
    if wiki is None:
        return error_envelope("tool-wiki-store is not available")

    # One retrieval per article, shared across every AU — the citation cache.
    citations: dict[str, dict | None] = {}
    for key, query in _ARTICLE_QUERIES.items():
        try:
            found = await wiki({"op": "search", "query": query, "limit": 3})
            passages = [
                p for p in found.get("passages") or []
                if isinstance(p, dict) and p.get("passage_id") and int(p.get("score") or 0) >= 2
            ]
        except Exception:
            passages = []
        citations[key] = (
            {
                "passage_id": passages[0]["passage_id"],
                "quote": str(passages[0].get("quote") or "")[:400],
                "source_path": passages[0].get("source_path", ""),
            }
            if passages
            else None
        )

    findings: list[dict] = []
    counts = {"red": 0, "amber": 0, "green": 0, "unknown": 0}
    annex_iii_candidates = 0

    for item in inventory:
        if not isinstance(item, dict):
            continue
        cap_id = item.get("capability_id", "unknown")
        purpose = str(item.get("purpose") or "").lower()
        annex_shaped = any(marker in f" {purpose} " for marker in _ANNEX_III_MARKERS)
        if annex_shaped:
            annex_iii_candidates += 1
        risk_tier = (
            "Annex III candidate (employment) - contextual legal assessment required"
            if annex_shaped
            else "no Annex III employment marker found by this check"
        )
        for article, obligation in _OBLIGATIONS.items():
            checked, present, evidence = _obligation_check(article, item)
            severity = "green" if present else "red"
            gap = "" if present else _gap_for(article, cap_id)
            if article == "Art 10" and severity == "green":
                severity = "amber"
                gap = (
                    "Declared access boundary only; training-data governance is "
                    "outside the architecture's scope."
                )
            citation = citations.get(article)
            corpus_silent = citation is None
            if corpus_silent:
                severity = "unknown"
                gap = (
                    f"The regulations corpus has no passage for {article} - "
                    "ingest the regulation note before this check can cite the obligation."
                )
            counts[severity] += 1
            findings.append({
                "finding_id": f"{cap_id}/{article.lower().replace(' ', '')}",
                "capability_id": cap_id,
                "risk_tier": risk_tier,
                "article": article,
                "obligation": obligation,
                "severity": severity,
                "checked": checked,
                "evidence": evidence,
                "regulation_citation": citation,
                "corpus_silent": corpus_silent,
                "annex_citation": citations.get("Annex III") if annex_shaped else None,
                "gap": gap,
                "remediation_hint": _remediation_for(article),
            })

    summary = {
        "aus_scanned": len([i for i in inventory if isinstance(i, dict)]),
        "annex_iii_candidates": annex_iii_candidates,
        **counts,
        "corpus_present": all(citations.get(a) for a in _OBLIGATIONS),
    }
    return {
        "outputs": {"findings": findings, "summary": summary},
        "signals": {
            "valid_output_shape": True,
            "risk_marker_assessed": True,
            "all_findings_cited": all(
                f.get("regulation_citation") or f.get("corpus_silent") for f in findings
            ),
            "corpus_present": summary["corpus_present"],
            "latency_seconds": round(_time.monotonic() - started, 2),
        },
    }


def _obligation_check(article: str, item: dict) -> tuple[str, bool, dict]:
    fields = item.get("card_fields") or {}
    lifecycle = item.get("lifecycle") or {}
    signals = item.get("evaluation_signals") or []
    trace = item.get("trace_evidence") or {}
    if article == "Art 9":
        present = bool(signals) and bool(lifecycle.get("reviewed_by"))
        return (
            "evaluation signals declared and a reviewer is recorded in the lifecycle",
            present,
            {"kind": "card_field", "ref": "evaluation_signals + lifecycle.reviewed_by",
             "value": {"signals": len(signals), "reviewed_by": lifecycle.get("reviewed_by", "")}},
        )
    if article == "Art 10":
        present = fields.get("has_inputs", False)
        return (
            "a declared input/tool boundary exists on the card",
            present,
            {"kind": "card_field", "ref": "inputs", "value": fields.get("has_inputs")},
        )
    if article == "Art 11":
        present = all(fields.get(k) for k in ("has_purpose", "has_inputs", "has_outputs", "has_constraints", "has_version"))
        return (
            "purpose, inputs, outputs, constraints, and version are all present on the card",
            present,
            {"kind": "card_field", "ref": "card completeness", "value": fields},
        )
    if article == "Art 12":
        invocations = int(trace.get("invocations") or 0)
        return (
            "trace evidence exists for this capability",
            invocations > 0,
            {"kind": "trace", "ref": "planner traces", "value": {"invocations": invocations}},
        )
    if article == "Art 13":
        present = fields.get("has_constraints", False) and bool(signals)
        return (
            "constraints and evaluation signals are declared to consumers",
            present,
            {"kind": "card_field", "ref": "constraints + evaluation_signals",
             "value": {"constraints": fields.get("has_constraints"), "signals": len(signals)}},
        )
    if article == "Art 14":
        present = bool(item.get("oversight_declared"))
        return (
            "the card declares a human oversight or escalation boundary",
            present,
            {"kind": "card_field", "ref": "constraints",
             "value": (item.get("oversight_evidence") or [None])[0]},
        )
    if article == "Art 72":
        present = lifecycle.get("status") == "approved" and bool(signals)
        return (
            "lifecycle status is approved and observed signals are declared",
            present,
            {"kind": "lifecycle", "ref": "status + evaluation_signals",
             "value": {"status": lifecycle.get("status", ""), "replaced_by": lifecycle.get("replaced_by", "")}},
        )
    return ("unrecognised article", False, {"kind": "none", "ref": "", "value": None})


def _gap_for(article: str, cap_id: str) -> str:
    gaps = {
        "Art 9": "No reviewer recorded or no evaluation signals declared.",
        "Art 10": "No declared input/tool boundary on the card.",
        "Art 11": "The card is missing one or more of purpose, inputs, outputs, constraints, version.",
        "Art 12": f"No trace evidence found for {cap_id}; run the workflow so records exist.",
        "Art 13": "Constraints or evaluation signals are not declared on the card.",
        "Art 14": "No human oversight or escalation declaration on the card.",
        "Art 72": "The capability is not approved in the registry lifecycle, or declares no observed signals.",
    }
    return gaps.get(article, "Evidence absent.")


def _remediation_for(article: str) -> str:
    hints = {
        "Art 9": "Declare evaluation_signals on the card and record a reviewer via the registry lifecycle.",
        "Art 10": "Declare the capability's inputs and tool dependencies on the card.",
        "Art 11": "Complete the capability card: purpose, inputs, outputs, constraints, version.",
        "Art 12": "Exercise the capability through the planner so traces exist; keep trace retention on.",
        "Art 13": "Declare constraints and evaluation signals on the card (hot-reloads and re-registers).",
        "Art 14": "Add an oversight/escalation constraint to capability-card.yaml (hot-reloads and re-registers).",
        "Art 72": "Approve the card via the registry lifecycle and keep observed signals flowing.",
    }
    return hints.get(article, "")


if __name__ == "__main__":
    run(handle)
