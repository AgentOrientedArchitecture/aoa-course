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
_RESULT_REVIEW_POLICY = "human-review-before-release"


def _human_review_before_use_constraint(card: dict) -> str:
    """Return the selected card constraint that makes a CV verdict draft-only."""
    for value in card.get("constraints") or []:
        text = str(value).strip()
        lowered = text.lower()
        if (
            "every verdict" in lowered
            and "draft" in lowered
            and "approved" in lowered
            and "human reviewer" in lowered
            and "before" in lowered
            and any(
                marker in lowered
                for marker in ("candidate screening", "interview", "employment action")
            )
        ):
            return text
    return ""


def _employment_card_eligibility(capability_cards: list) -> dict:
    evaluator_cards = [
        card
        for card in capability_cards
        if isinstance(card, dict)
        and str(card.get("id") or "").lower().startswith("evaluator-cv")
    ]
    if not evaluator_cards:
        return {
            "eligible": False,
            "capability_id": "evaluator-cv",
            "matched_constraint": "",
            "reason": "The resolved employment plan has no selected evaluator-cv card snapshot.",
        }
    card = evaluator_cards[0]
    lifecycle = card.get("lifecycle") if isinstance(card.get("lifecycle"), dict) else {}
    status = str(lifecycle.get("status") or "approved")
    matched = _human_review_before_use_constraint(card)
    eligible = status == "approved" and bool(matched)
    if status != "approved":
        reason = f"{card.get('id')} lifecycle status is {status}, not approved."
    elif not matched:
        reason = (
            f"{card.get('id')} does not declare every verdict draft-only and subject "
            "to human approval before candidate screening, interview, or employment action."
        )
    else:
        reason = "The selected evaluator card declares the required review-before-use boundary."
    return {
        "eligible": eligible,
        "capability_id": card.get("id"),
        "version": card.get("version"),
        "lifecycle_status": status,
        "constraints": card.get("constraints") or [],
        "matched_constraint": matched,
        "reason": reason,
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
    release_policy = inputs.get("release_policy")
    plan_digest = str(inputs.get("plan_digest") or "").strip()

    if not workflow:
        return error_envelope("workflow is required")
    if not isinstance(use_context, dict):
        return error_envelope("use_context (object) is required")
    if not isinstance(resolved_plan, list) or not resolved_plan:
        return error_envelope("resolved_plan (non-empty array) is required")
    if not isinstance(capability_cards, list):
        return error_envelope("capability_cards (array) is required")
    if not isinstance(release_policy, dict):
        return error_envelope("release_policy (object) is required")
    if not plan_digest:
        return error_envelope("plan_digest is required")

    policy = _plan_policy_assessment(
        workflow, use_context, resolved_plan, capability_cards
    )
    employment_shaped = policy["employment_shaped"]
    card_eligibility = _employment_card_eligibility(capability_cards)
    review_control_present = (
        release_policy.get("mode") == _RESULT_REVIEW_POLICY
    )
    governance_queries = {
        "Annex III": _ARTICLE_QUERIES["Annex III"],
        "Art 14": _ARTICLE_QUERIES["Art 14"],
    }
    citations = await _retrieve_regulation_citations(ctx, governance_queries)
    if citations is None:
        citations = {key: None for key in governance_queries}
    knowledge_evidence_present = all(citations.get(key) for key in governance_queries)
    eligible = (
        bool(card_eligibility["eligible"])
        and review_control_present
        and knowledge_evidence_present
        if employment_shaped
        else True
    )
    decision = "proceed" if eligible else "reject"
    result_review_required = bool(employment_shaped)

    capabilities = [
        str(step.get("capability") or "")
        for step in resolved_plan
        if isinstance(step, dict) and step.get("capability")
    ]
    gaps: list[str] = []
    if employment_shaped and not card_eligibility["eligible"]:
        gaps.append(str(card_eligibility["reason"]))
    if employment_shaped and not review_control_present:
        gaps.append(
            "The resolved plan does not declare a human-review-before-release result control."
        )
    if employment_shaped and not knowledge_evidence_present:
        missing = ", ".join(key for key in governance_queries if not citations.get(key))
        gaps.append(
            f"The governance wiki has no citeable passage for: {missing}. Seed the Session 4 corpus before retrying."
        )
    finding = {
        "finding_id": f"{workflow}/eligibility",
        "severity": "green" if eligible else "red",
        "checked": (
            "employment use context, selected evaluator-card review-before-use declaration, "
            "and a post-result human-review-before-release control"
        ),
        "evidence": {
            "workflow": workflow,
            "capabilities": capabilities,
            "use_context": use_context,
            "resolved_plan": resolved_plan,
            "release_policy": release_policy,
            "card_eligibility": card_eligibility,
            "knowledge_evidence": {
                "tool": "tool-wiki-store",
                "queries": governance_queries,
                "citations": citations,
            },
            "employment_reasons": policy["employment_reasons"],
            "consequence_reasons": policy["consequence_reasons"],
            "plan_digest": plan_digest,
        },
        "gap": " ".join(gaps),
        "regulation_citations": [
            citation for citation in citations.values() if citation
        ],
        "corpus_silent": not knowledge_evidence_present,
        "control": (
            "Run the application AUs only to a draft, then hold the exact result digest for human review before release."
            if eligible and employment_shaped
            else "Do not invoke application AUs until every context-blocking card and plan-control gap is fixed."
            if employment_shaped
            else "No employment-specific result review is required by this course policy."
        ),
    }
    findings = [finding]

    lines = [
        "# Pre-execution plan eligibility",
        "",
        "> **Operational eligibility decision only. This is not legal permission or a legal determination.**",
        "",
        f"- **Workflow:** `{workflow}`",
        f"- **Plan digest:** `{plan_digest}`",
        f"- **Resolved composition:** `{' -> '.join(capabilities)}`",
        f"- **Decision:** **{decision}**",
        "",
    ]
    if employment_shaped and not eligible:
        lines += [
            "## Plan blocked",
            "",
            "This employment composition contains context-blocking evidence gaps:",
            "",
            *[f"- {gap}" for gap in gaps],
            "",
            "Fix the selected capability card or release control, let it hot-reload, and submit a new CV-fit intent.",
            "No application AU has been invoked.",
        ]
    elif employment_shaped:
        lines += [
            "## Eligibility passed",
            "",
            f"`{card_eligibility.get('capability_id')}` declares:",
            "",
            f"> {card_eligibility.get('matched_constraint')}",
            "",
            "The plan may execute only to a draft. A human must review the actual evaluation and approve its exact result digest before release.",
        ]
    else:
        lines += [
            "## Policy result",
            "",
            "No consequential employment composition was found, so this course policy allows automatic completion.",
        ]
    if employment_shaped:
        lines += [
            "",
            "## Governance knowledge used",
            "",
            "The eligibility rule is deterministic; the regulatory rationale is retrieved through `tool-wiki-store` so its source remains inspectable in the trace.",
            "",
        ]
        for label, query in governance_queries.items():
            citation = citations.get(label)
            lines.append(f"### {label}")
            lines.append("")
            lines.append(f"- **Wiki query:** `{query}`")
            if citation:
                lines.append(
                    f"- **Passage:** `{citation.get('passage_id')}` from `{citation.get('source_path')}`"
                )
                lines.append("")
                for quote_line in str(citation.get("quote") or "").splitlines():
                    lines.append(f"> {quote_line}" if quote_line else ">")
            else:
                lines.append("- **Passage:** corpus silent")
            lines.append("")
    evaluation_markdown = "\n".join(lines).strip() + "\n"
    lowered = evaluation_markdown.lower()

    return {
        "outputs": {
            "decision": decision,
            "plan_digest": plan_digest,
            "result_review_required": result_review_required,
            "card_eligibility": card_eligibility,
            "release_policy": release_policy,
            "knowledge_evidence": {
                "tool": "tool-wiki-store",
                "queries": governance_queries,
                "citations": citations,
            },
            "findings": findings,
            "evaluation_markdown": evaluation_markdown,
        },
        "signals": {
            "valid_output_shape": True,
            "resolved_plan_assessed": True,
            "card_eligibility_assessed": True,
            "result_release_control_assessed": True,
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
        "knowledge_evidence": {
            "tool": "tool-wiki-store",
            "queries": _ARTICLE_QUERIES,
            "passage_ids": {
                key: citation.get("passage_id") if citation else None
                for key, citation in citations.items()
            },
            "citations": citations,
        },
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
        "knowledge_evidence": {
            "tool": "tool-wiki-store",
            "queries": {"Art 14": _ARTICLE_QUERIES["Art 14"]},
            "passage_ids": {
                "Art 14": article_14_citation.get("passage_id")
                if article_14_citation else None
            },
            "citations": {"Art 14": article_14_citation},
        },
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
    decision = str(governance.get("decision") or "")
    release_policy = (
        plan.get("release_policy")
        if isinstance(plan.get("release_policy"), dict)
        else governance.get("release_policy")
        if isinstance(governance.get("release_policy"), dict)
        else {}
    )
    card_eligibility = (
        governance.get("card_eligibility")
        if isinstance(governance.get("card_eligibility"), dict)
        else _employment_card_eligibility(
            plan.get("capability_cards")
            if isinstance(plan.get("capability_cards"), list)
            else []
        )
    )
    draft = plan.get("draft") if isinstance(plan.get("draft"), dict) else {}
    result_hold = plan.get("result_hold") if isinstance(plan.get("result_hold"), dict) else {}
    review = plan.get("review") if isinstance(plan.get("review"), dict) else {}
    release = plan.get("release") if isinstance(plan.get("release"), dict) else {}
    quarantine = plan.get("quarantine") if isinstance(plan.get("quarantine"), dict) else {}
    execution_status = str(plan.get("execution_status") or "unknown")
    invoked_at = str(plan.get("first_application_invoke_at") or "")
    result_digest = str(draft.get("result_digest") or "")
    review_digest = str(review.get("result_digest") or "")
    review_decision = str(review.get("decision") or "")
    controlled_rejection = (
        decision == "reject"
        and not invoked_at
        and not release
        and execution_status == "plan-rejected"
    )

    severity = "green"
    checked = (
        "selected-card eligibility, governance before application work, draft creation after "
        "application completion, exact-result review, and review-before-release or quarantine"
    )
    gap = ""
    remediation = ""
    outcome = execution_status
    if controlled_rejection:
        outcome = "ineligible plan correctly blocked"
    elif decision != "proceed":
        severity = "red" if invoked_at else "amber"
        gap = "The employment plan has no observed proceed decision before application work."
        remediation = "Resolve a new plan and run the pre-execution eligibility evaluator."
    elif not card_eligibility.get("eligible"):
        severity = "red"
        gap = "The selected evaluator card was not eligible for this employment composition."
        remediation = "Add the required review-before-use constraint, then resolve a new plan."
    elif release_policy.get("mode") != _RESULT_REVIEW_POLICY:
        severity = "red"
        gap = "The plan did not declare a human-review-before-release result control."
        remediation = "Bind the post-result release policy into the resolved plan."
    elif plan.get("eligibility_preceded_application_invoke") is not True:
        severity = "red"
        gap = "Application invocation was not proven to follow the eligibility decision."
        remediation = "Evaluate and record plan eligibility before the first application invocation."
    elif not draft:
        severity = "red" if release else "amber"
        gap = "No held draft and result digest were observed after application execution."
        remediation = "Freeze the completed AU output as a draft and compute its result digest."
    elif plan.get("application_completed_before_draft") is not True:
        severity = "red"
        gap = "The draft was not proven to follow completion of the application AU sequence."
        remediation = "Create the reviewable draft only after all application responses are recorded."
    elif not result_hold:
        severity = "red" if release else "amber"
        gap = "The result was not held for review before release."
        remediation = "Record a result hold for the exact draft digest."
    elif not review:
        severity = "red" if release or quarantine else "amber"
        gap = "The draft is held and awaiting a human result review."
        remediation = "Review the actual draft and approve or reject its exact result digest."
    elif not result_digest or review_digest != result_digest:
        severity = "red"
        gap = "The human review does not bind to the held draft result digest."
        remediation = "Accept review only for the exact result digest currently held."
    elif plan.get("draft_preceded_review") is not True:
        severity = "red"
        gap = "The human review was not proven to follow creation of the draft."
        remediation = "Expose the completed draft before recording review."
    elif review_decision == "approve":
        if quarantine:
            severity = "red"
            gap = "An approved result was quarantined instead of released."
            remediation = "Release only the approved draft payload."
        elif not release:
            severity = "amber"
            gap = "Approval is recorded but result release is not observed."
            remediation = "Release the exact approved draft payload."
        elif plan.get("review_preceded_release") is not True:
            severity = "red"
            gap = "Result release was not proven to follow human approval."
            remediation = "Record review before release."
        elif plan.get("released_result_matches_draft") is not True:
            severity = "red"
            gap = "The released result does not match the approved draft and digest."
            remediation = "Release the immutable payload bound to the reviewed result digest."
        elif execution_status != "released":
            severity = "amber"
            gap = "Release evidence exists but the final flow status is not released."
            remediation = "Complete the release record and flow finish event."
    elif review_decision == "reject":
        if release:
            severity = "red"
            gap = "A human-rejected draft was released."
            remediation = "Quarantine rejected results and emit no released output."
        elif not quarantine:
            severity = "amber"
            gap = "Rejection is recorded but quarantine is not observed."
            remediation = "Quarantine the exact rejected result digest."
        elif plan.get("review_preceded_quarantine") is not True:
            severity = "red"
            gap = "Quarantine was not proven to follow human rejection."
            remediation = "Record review before quarantine."
        elif execution_status != "quarantined":
            severity = "amber"
            gap = "Quarantine evidence exists but the final flow status is not quarantined."
            remediation = "Complete the quarantine and flow finish event."
    else:
        severity = "red"
        gap = "The result review decision is missing or unrecognised."
        remediation = "Record an approve or reject decision with reviewer notes."

    evidence = {
        "trace_id": trace_id,
        "workflow": plan.get("workflow"),
        "use_context": plan.get("use_context") or {},
        "capability_ids": plan.get("capability_ids") or [],
        "plan_digest": plan_digest,
        "release_policy": release_policy,
        "card_eligibility": card_eligibility,
        "governance_decision": decision or "not observed",
        "knowledge_evidence": governance.get("knowledge_evidence") or {},
        "eligibility_preceded_application_invoke": plan.get("eligibility_preceded_application_invoke"),
        "application_completed_before_draft": plan.get("application_completed_before_draft"),
        "draft": (
            {key: draft.get(key) for key in ("timestamp", "plan_digest", "result_digest")}
            if draft else "not observed"
        ),
        "result_hold": result_hold or "not observed",
        "review": review or "not observed",
        "release": (
            {key: release.get(key) for key in ("timestamp", "plan_digest", "result_digest", "actor_id")}
            if release else "not observed"
        ),
        "quarantine": quarantine or "not observed",
        "draft_preceded_review": plan.get("draft_preceded_review"),
        "review_preceded_release": plan.get("review_preceded_release"),
        "review_preceded_quarantine": plan.get("review_preceded_quarantine"),
        "released_result_matches_draft": plan.get("released_result_matches_draft"),
        "execution_status": execution_status,
        "outcome": outcome,
    }
    return {
        "finding_id": f"{trace_id}/result-governance",
        "scope": "plan",
        "trace_id": trace_id,
        "plan_digest": plan_digest,
        "result_digest": result_digest,
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
            "This is operational evidence about card eligibility and review-before-release. "
            "It does not establish effective human oversight, satisfy Article 14, or confer legal permission."
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
        present = bool(item.get("human_review_before_use_declared"))
        return (
            "the card declares every verdict draft-only until human review before employment use",
            present,
            {"kind": "card_field", "ref": "constraints",
             "value": item.get("human_review_before_use_evidence")},
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
        "Art 14": "No declaration makes every verdict draft-only until human review before employment use.",
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
        "Art 14": "Declare that every verdict is a draft requiring human review before candidate screening, interview, or employment action (hot-reloads and re-registers).",
        "Art 72": "Approve the card via the registry lifecycle and keep observed signals flowing.",
    }
    return hints.get(article, "")


if __name__ == "__main__":
    run(handle)
