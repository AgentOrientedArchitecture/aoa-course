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
    if capability_id == "evaluator-agent-evidence":
        return await _evaluate_agent_evidence(inputs, ctx)
    if capability_id == "evaluator-flow-evidence":
        return await _evaluate_flow_evidence(inputs, ctx)
    if capability_id == "evaluator-compliance":
        return await _evaluate_compliance(inputs, ctx)
    if capability_id == "evaluator-plan-governance":
        return await _evaluate_plan_governance(inputs, ctx)
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
# evaluator-plan-governance — deterministic pre-execution composition gate
# ----------------------------------------------------------------------

_EMPLOYMENT_TEXT_MARKERS = (
    "candidate",
    "employment",
    "hiring",
    "recruit",
    "curriculum vitae",
    "job description",
    " cv",
    "cv ",
)
_CONSEQUENCE_TEXT_MARKERS = (
    "score",
    "ranking",
    "rank candidate",
    "verdict",
    "recommendation",
    "candidate screening",
    "evaluate fit",
    "interview question",
    "interview preparation",
)
_CONSEQUENTIAL_OUTPUT_NAMES = {
    "scores",
    "verdict",
    "recommendation",
    "ranking",
    "questions",
    "report_markdown",
}


def _plan_policy_assessment(
    workflow: str,
    use_context: dict,
    resolved_plan: list,
    capability_cards: list,
) -> dict:
    """Apply one structured employment-composition policy in both evaluators."""
    workflow_l = workflow.strip().lower()
    context_domain = str(use_context.get("domain") or "").lower()
    data_subjects = {
        str(subject).strip().lower()
        for subject in use_context.get("data_subjects") or []
        if str(subject).strip()
    }
    output_use = str(use_context.get("output_use") or "").lower()
    decision_effect = str(use_context.get("decision_effect") or "").lower()
    capabilities = [
        str(step.get("capability") or "").strip().lower()
        for step in resolved_plan
        if isinstance(step, dict) and step.get("capability")
    ]
    plan_text = json.dumps(resolved_plan, sort_keys=True, default=str).lower()

    employment_reasons: list[str] = []
    if workflow_l.startswith("cv-fit"):
        employment_reasons.append(f"workflow:{workflow_l}")
    if context_domain in {"employment", "hiring", "recruitment"}:
        employment_reasons.append(f"domain:{context_domain}")
    if data_subjects.intersection({"candidate", "candidates", "job applicants", "applicants"}):
        employment_reasons.append("data-subjects:candidates")
    if any(marker in output_use for marker in ("candidate", "employment", "hiring", "interview")):
        employment_reasons.append(f"output-use:{output_use}")
    if any(
        capability.startswith("parser-cv")
        or capability.startswith("evaluator-cv")
        or capability.startswith("reporter-cv")
        or capability.startswith("interviewer-")
        for capability in capabilities
    ):
        employment_reasons.append("composition:cv-or-interview-capability")
    employment_reasons.extend(
        f"plan-text:{marker.strip()}"
        for marker in _EMPLOYMENT_TEXT_MARKERS
        if marker in f" {plan_text} "
    )

    consequence_reasons: list[str] = []
    if decision_effect in {"recommendation", "decision", "selection", "ranking", "screening"}:
        consequence_reasons.append(f"decision-effect:{decision_effect}")
    if any(
        marker in output_use
        for marker in ("screen", "recommend", "rank", "selection", "interview-preparation")
    ):
        consequence_reasons.append(f"output-use:{output_use}")
    consequence_reasons.extend(
        f"plan-text:{marker}"
        for marker in _CONSEQUENCE_TEXT_MARKERS
        if marker in plan_text
    )
    for card in capability_cards:
        if not isinstance(card, dict):
            continue
        output_names = {
            str(field.get("name") or "").strip().lower()
            for field in card.get("outputs") or []
            if isinstance(field, dict)
        }
        matched_outputs = sorted(output_names.intersection(_CONSEQUENTIAL_OUTPUT_NAMES))
        if matched_outputs:
            consequence_reasons.append(
                f"card-outputs:{card.get('id', 'unknown')}:{','.join(matched_outputs)}"
            )

    return {
        "employment_shaped": bool(employment_reasons and consequence_reasons),
        "employment_reasons": sorted(set(employment_reasons)),
        "consequence_reasons": sorted(set(consequence_reasons)),
    }


async def _evaluate_plan_governance(inputs: dict, ctx: Context) -> dict:
    started = _time.monotonic()
    workflow = str(inputs.get("workflow") or "").strip()
    use_context = inputs.get("use_context")
    resolved_plan = inputs.get("resolved_plan")
    capability_cards = inputs.get("capability_cards")
    plan_digest = str(inputs.get("plan_digest") or "").strip()

    if not workflow:
        return error_envelope("workflow is required")
    if not isinstance(use_context, dict):
        return error_envelope("use_context (object) is required")
    if not isinstance(resolved_plan, list) or not resolved_plan:
        return error_envelope("resolved_plan (non-empty array) is required")
    if not isinstance(capability_cards, list):
        return error_envelope("capability_cards (array) is required")
    if not plan_digest:
        return error_envelope("plan_digest is required")

    policy = _plan_policy_assessment(
        workflow, use_context, resolved_plan, capability_cards
    )
    employment_shaped = policy["employment_shaped"]
    decision = "require-human-approval" if employment_shaped else "proceed"

    capabilities = [
        str(step.get("capability") or "")
        for step in resolved_plan
        if isinstance(step, dict) and step.get("capability")
    ]
    findings = [{
        "finding_id": f"{workflow}/composition",
        "severity": "amber" if employment_shaped else "green",
        "checked": (
            "workflow, declared use context, resolved task purposes/capabilities/input mappings, "
            "and selected card output contracts"
        ),
        "evidence": {
            "workflow": workflow,
            "capabilities": capabilities,
            "use_context": use_context,
            "resolved_plan": resolved_plan,
            "selected_cards": [
                {
                    "id": card.get("id"),
                    "version": card.get("version"),
                    "agent_id": card.get("agent_id"),
                    "outputs": card.get("outputs") or [],
                }
                for card in capability_cards
                if isinstance(card, dict)
            ],
            "employment_reasons": policy["employment_reasons"],
            "consequence_reasons": policy["consequence_reasons"],
            "plan_digest": plan_digest,
        },
        "control": (
            "Record accountable human approval for this exact plan digest before invoking any application AU."
            if employment_shaped
            else "No pre-execution human approval is required by the course composition policy."
        ),
    }]

    lines = [
        "# Pre-execution plan governance",
        "",
        "> **Operational execution decision only. This is not legal permission or a legal determination.**",
        "",
        f"- **Workflow:** `{workflow}`",
        f"- **Plan digest:** `{plan_digest}`",
        f"- **Resolved composition:** `{' -> '.join(capabilities)}`",
        f"- **Decision:** **{decision}**",
        "",
    ]
    if employment_shaped:
        lines += [
            "## Why execution is held",
            "",
            "The resolved plan combines candidate or employment context with scoring, evaluation, recommendation, screening, or interview-oriented outputs.",
            "Individually governed AUs do not make that end-to-end composition safe to execute automatically.",
            "",
            "## Required control",
            "",
            "An accountable human must approve this exact resolved plan before the first application AU runs.",
            "The approval is recorded on the same trace and applies only to the displayed plan digest.",
        ]
    else:
        lines += [
            "## Policy result",
            "",
            "No consequential employment composition was found by the deterministic course policy, so execution may proceed.",
        ]
    evaluation_markdown = "\n".join(lines).strip() + "\n"
    lowered = evaluation_markdown.lower()

    return {
        "outputs": {
            "decision": decision,
            "plan_digest": plan_digest,
            "findings": findings,
            "evaluation_markdown": evaluation_markdown,
        },
        "signals": {
            "valid_output_shape": True,
            "resolved_plan_assessed": True,
            "decision_supported": bool(findings),
            "no_compliance_verdict": not any(
                word in lowered for word in ("compliant", "complies", "certified")
            ),
            "latency_seconds": round(_time.monotonic() - started, 3),
        },
    }


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


async def _retrieve_regulation_citations(
    ctx: Context, queries: dict[str, str]
) -> dict[str, dict | None] | None:
    """Retrieve one complete, citation-preserving passage per requested article."""
    wiki = ctx.tools.get("tool-wiki-store")
    if wiki is None:
        return None

    citations: dict[str, dict | None] = {}
    for key, query in queries.items():
        try:
            found = await wiki({"op": "search", "query": query, "limit": 3})
            passages = [
                passage
                for passage in found.get("passages") or []
                if isinstance(passage, dict)
                and passage.get("passage_id")
                and int(passage.get("score") or 0) >= 2
            ]
        except Exception:
            passages = []
        citations[key] = (
            {
                "passage_id": passages[0]["passage_id"],
                "quote": str(passages[0].get("quote") or "").strip(),
                "source_path": passages[0].get("source_path", ""),
            }
            if passages
            else None
        )
    return citations


def _component_evidence(
    inventory: list, citations: dict[str, dict | None]
) -> tuple[list[dict], dict]:
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
        "aus_scanned": len([item for item in inventory if isinstance(item, dict)]),
        "annex_iii_candidates": annex_iii_candidates,
        **counts,
        "corpus_present": all(citations.get(article) for article in _OBLIGATIONS),
    }
    return findings, summary


def _flow_evidence(
    plans: list, article_14_citation: dict | None
) -> tuple[list[dict], dict]:
    plan_findings = [
        _plan_governance_finding(plan, article_14_citation)
        for plan in plans
        if isinstance(plan, dict) and _employment_shaped_plan(plan)
    ]
    counts = {"red": 0, "amber": 0, "green": 0, "unknown": 0}
    for finding in plan_findings:
        counts[finding["severity"]] += 1
    summary = {
        "plans_observed": len(plan_findings),
        "employment_plans_assessed": len(plan_findings),
        "plan_counts": counts,
        "corpus_present": article_14_citation is not None,
    }
    return plan_findings, summary


async def _evaluate_agent_evidence(inputs: dict, ctx: Context) -> dict:
    started = _time.monotonic()
    inventory = inputs.get("inventory")
    if not isinstance(inventory, list):
        return error_envelope("inventory (array) is required")
    citations = await _retrieve_regulation_citations(ctx, _ARTICLE_QUERIES)
    if citations is None:
        return error_envelope("tool-wiki-store is not available")
    findings, summary = _component_evidence(inventory, citations)
    return {
        "outputs": {"findings": findings, "summary": summary},
        "signals": {
            "valid_output_shape": True,
            "risk_marker_assessed": True,
            "all_findings_cited": all(
                finding.get("regulation_citation") or finding.get("corpus_silent")
                for finding in findings
            ),
            "corpus_present": summary["corpus_present"],
            "latency_seconds": round(_time.monotonic() - started, 2),
        },
    }


async def _evaluate_flow_evidence(inputs: dict, ctx: Context) -> dict:
    started = _time.monotonic()
    plans = inputs.get("plans")
    if not isinstance(plans, list):
        return error_envelope("plans (array) is required")
    citations = await _retrieve_regulation_citations(
        ctx, {"Art 14": _ARTICLE_QUERIES["Art 14"]}
    )
    if citations is None:
        return error_envelope("tool-wiki-store is not available")
    plan_findings, summary = _flow_evidence(plans, citations.get("Art 14"))
    return {
        "outputs": {"plan_findings": plan_findings, "summary": summary},
        "signals": {
            "valid_output_shape": True,
            "plan_sequence_assessed": True,
            "all_findings_cited": all(
                finding.get("regulation_citation") or finding.get("corpus_silent")
                for finding in plan_findings
            ),
            "corpus_present": summary["corpus_present"],
            "latency_seconds": round(_time.monotonic() - started, 2),
        },
    }


async def _evaluate_compliance(inputs: dict, ctx: Context) -> dict:
    """Compatibility wrapper returning the former combined estate evidence shape."""
    started = _time.monotonic()
    inventory = inputs.get("inventory")
    plans = inputs.get("plans")
    if not isinstance(inventory, list):
        return error_envelope("inventory (array) is required")
    if not isinstance(plans, list):
        return error_envelope("plans (array) is required")
    citations = await _retrieve_regulation_citations(ctx, _ARTICLE_QUERIES)
    if citations is None:
        return error_envelope("tool-wiki-store is not available")

    findings, component_summary = _component_evidence(inventory, citations)
    plan_findings, flow_summary = _flow_evidence(plans, citations.get("Art 14"))
    summary = {
        **component_summary,
        **flow_summary,
        "corpus_present": component_summary["corpus_present"],
    }
    all_findings = findings + plan_findings
    return {
        "outputs": {
            "findings": findings,
            "plan_findings": plan_findings,
            "summary": summary,
        },
        "signals": {
            "valid_output_shape": True,
            "risk_marker_assessed": True,
            "plan_sequence_assessed": True,
            "all_findings_cited": all(
                finding.get("regulation_citation") or finding.get("corpus_silent")
                for finding in all_findings
            ),
            "corpus_present": summary["corpus_present"],
            "latency_seconds": round(_time.monotonic() - started, 2),
        },
    }


def _employment_shaped_plan(plan: dict) -> bool:
    assessment = _plan_policy_assessment(
        str(plan.get("workflow") or ""),
        plan.get("use_context") if isinstance(plan.get("use_context"), dict) else {},
        plan.get("resolved_composition")
        if isinstance(plan.get("resolved_composition"), list)
        else [],
        plan.get("capability_cards")
        if isinstance(plan.get("capability_cards"), list)
        else [],
    )
    return bool(assessment["employment_shaped"])


def _plan_governance_finding(plan: dict, citation: dict | None) -> dict:
    trace_id = str(plan.get("trace_id") or "unknown")
    plan_digest = str(plan.get("plan_digest") or "")
    governance = plan.get("governance") if isinstance(plan.get("governance"), dict) else {}
    hold = plan.get("hold") if isinstance(plan.get("hold"), dict) else {}
    approval = plan.get("approval") if isinstance(plan.get("approval"), dict) else {}
    resume = plan.get("resume") if isinstance(plan.get("resume"), dict) else {}
    decision = str(governance.get("decision") or "")
    execution_status = str(plan.get("execution_status") or "unknown")
    invoked_at = str(plan.get("first_application_invoke_at") or "")
    approval_digest = str(approval.get("plan_digest") or "")
    hold_digest = str(hold.get("plan_digest") or "")
    resume_digest = str(resume.get("plan_digest") or "")
    hold_recorded = bool(hold)
    approval_recorded = approval.get("decision") == "approve"
    resume_recorded = bool(resume)
    digest_match = bool(
        plan_digest
        and hold_digest == plan_digest
        and approval_digest == plan_digest
        and resume_digest == plan_digest
    )
    governance_preceded = plan.get("governance_preceded_application_invoke") is not False
    approval_preceded = plan.get("approval_preceded_application_invoke") is True
    resume_preceded = plan.get("resume_preceded_application_invoke") is True
    finished = execution_status == "finished"

    severity = "green"
    checked = (
        "pre-execution governance decision, exact-digest approval, event order, "
        "and observed application completion"
    )
    gap = ""
    remediation = ""
    if decision == "proceed":
        severity = "red"
        gap = "The employment-shaped plan was released automatically instead of requiring accountable review."
        remediation = "Require approval for the exact resolved plan digest before any application AU invocation."
    elif decision != "require-human-approval":
        severity = "red" if invoked_at else "amber"
        gap = "No observed pre-execution decision required human approval for this employment-shaped plan."
        remediation = "Run the plan through the composition governance evaluator before application execution."
    elif invoked_at and not governance_preceded:
        severity = "red"
        gap = "An application AU invocation was observed before the governance decision."
        remediation = "Move the governance gate between resolved-plan recording and the first application invocation."
    elif not hold_recorded:
        severity = "red" if invoked_at else "amber"
        gap = "No hold record binds this employment-shaped plan before approval or execution."
        remediation = "Record a hold for the exact resolved plan digest before accepting approval."
    elif not approval_recorded:
        severity = "red" if invoked_at else "amber"
        gap = (
            "Application execution was observed without an approval record."
            if invoked_at
            else "The plan was held and no approval has yet been recorded."
        )
        remediation = "Record an accountable approve/reject decision for the exact held plan digest."
    elif not resume_recorded:
        severity = "red" if invoked_at else "amber"
        gap = "Approval was recorded, but no same-trace resume record was observed."
        remediation = "Record resume for the approved digest before invoking any application AU."
    elif not digest_match:
        severity = "red"
        gap = "The approval, hold, or resume evidence does not bind to the resolved plan digest."
        remediation = "Reject stale approvals and approve only the exact digest shown in the governance report."
    elif invoked_at and not approval_preceded:
        severity = "red"
        gap = "An application AU invocation was observed before the approval event."
        remediation = "Keep application execution paused until approval is durably recorded on the same trace."
    elif invoked_at and not resume_preceded:
        severity = "red"
        gap = "An application AU invocation was observed before the same-trace resume event."
        remediation = "Resume the approved plan before invoking the first application AU."
    elif not invoked_at or not finished:
        severity = "amber"
        gap = "Approval evidence is present, but completed application execution is not yet observed."
        remediation = "Complete or investigate the run, then repeat the estate check."

    evidence = {
        "trace_id": trace_id,
        "workflow": plan.get("workflow"),
        "use_context": plan.get("use_context") or {},
        "capability_ids": plan.get("capability_ids") or [],
        "plan_digest": plan_digest,
        "governance_decision": decision or "not observed",
        "hold_digest": hold_digest or "not observed",
        "approval": approval or "not observed",
        "resume": resume or "not observed",
        "governance_preceded_application_invoke": governance_preceded,
        "approval_preceded_application_invoke": approval_preceded,
        "resume_preceded_application_invoke": resume_preceded,
        "first_application_invoke_at": invoked_at or "not observed",
        "execution_status": execution_status,
    }
    return {
        "finding_id": f"{trace_id}/plan-governance",
        "scope": "plan",
        "trace_id": trace_id,
        "plan_digest": plan_digest,
        "workflow": plan.get("workflow", ""),
        "article": "Art 14",
        "obligation": "human oversight",
        "severity": severity,
        "checked": checked,
        "evidence": evidence,
        "regulation_citation": citation,
        "corpus_silent": citation is None,
        "gap": gap,
        "remediation_hint": remediation,
        "interpretation": (
            "This is operational evidence about a course execution gate. It does not establish "
            "effective human oversight, satisfy Article 14, or confer legal permission."
        ),
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
