"""reporter agent.

One Python process serving five capabilities through capability-id dispatch
in ``handle``: ``reporter-cv-fit`` (Session 1), ``reporter-answer`` and
``reporter-ingest-summary`` (Session 2), and the Session 4 governance pair
``reporter-agent-evidence`` and ``reporter-flow-audit``.

Only ``reporter-cv-fit`` is model-backed; the rest render structured inputs
into markdown deterministically. Some capabilities only consume structured
data; ``reporter-ingest-summary`` uses the declared ``tool-wiki-store`` to
store the finished result.
"""
from __future__ import annotations

import json
import time as _time

from _base.base import Context, run
from _base.json_utils import error_envelope, parse_json


SYSTEM_PROMPT = (
    "You are a hiring report writer. Given a parsed CV and a JD evaluation, "
    "you produce a short, decisive report for a human reader. You always "
    "respond with a single JSON object - no preamble, no commentary, "
    "no code fence."
)

ANSWER_SYSTEM_PROMPT = (
    "You are a grounded knowledge-base answer writer. You answer using only "
    "the provided parsed note and evaluation. You always respond with a "
    "single JSON object - no preamble, no commentary, no code fence."
)


async def handle(capability_id: str, inputs: dict, ctx: Context) -> dict:
    if capability_id == "reporter-cv-fit":
        return await _report_cv_fit(inputs, ctx)
    if capability_id == "reporter-answer":
        return await _report_answer(inputs, ctx)
    if capability_id == "reporter-ingest-summary":
        return await _report_ingest_summary(inputs, ctx)
    if capability_id == "reporter-agent-evidence":
        return await _report_agent_evidence(inputs, ctx)
    if capability_id == "reporter-flow-audit":
        return await _report_flow_audit(inputs, ctx)
    return error_envelope(f"reporter does not back capability {capability_id!r}")


async def _report_cv_fit(inputs: dict, ctx: Context) -> dict:
    cv = inputs.get("cv")
    evaluation = inputs.get("evaluation")
    if not isinstance(cv, dict):
        return error_envelope("cv (parsed object) is required")
    if not isinstance(evaluation, dict):
        return error_envelope("evaluation (object) is required")

    prompt = (
        f"{ctx.skills}\n\n"
        f"## Parsed CV\n\n```json\n{json.dumps(cv, indent=2)}\n```\n\n"
        f"## Evaluation\n\n```json\n{json.dumps(evaluation, indent=2)}\n```\n"
    )
    completion = ctx.model.complete(prompt, system=SYSTEM_PROMPT, temperature=0.2)
    report, err = parse_json(completion.text)
    if err is not None:
        return error_envelope(err)
    if not isinstance(report, dict):
        return error_envelope("report must be a JSON object")

    headline = report.get("headline")
    recommendation = report.get("recommendation")
    report["report_markdown"] = _cv_report_markdown(report)
    return {
        "outputs": report,
        "signals": {
            "valid_output_shape": True,
            "has_headline": isinstance(headline, str) and len(headline) > 0,
            "has_recommendation": recommendation in {"interview", "hold", "pass"},
            "has_markdown": bool(report.get("report_markdown")),
            "latency_seconds": completion.latency_seconds,
        },
    }


async def _report_answer(inputs: dict, ctx: Context) -> dict:
    started = _time.monotonic()
    question = inputs.get("question")
    parsed_note = inputs.get("parsed_note")
    evaluation = inputs.get("evaluation")
    if not isinstance(question, str) or not question.strip():
        return error_envelope("question is required")
    if not isinstance(parsed_note, dict):
        return error_envelope("parsed_note (object) is required")
    if not isinstance(evaluation, dict):
        return error_envelope("evaluation (object) is required")

    answer = _grounded_wiki_answer(question, parsed_note, evaluation)
    citations = answer.get("citations")
    answer["answer_markdown"] = _answer_markdown(answer)
    return {
        "outputs": answer,
        "signals": {
            "valid_output_shape": True,
            "has_answer": isinstance(answer.get("answer"), str) and bool(answer.get("answer")),
            "has_citations": isinstance(citations, list) and len(citations) > 0,
            "has_markdown": bool(answer.get("answer_markdown")),
            "grounded_from_passages": True,
            "latency_seconds": round(_time.monotonic() - started, 3),
        },
    }


async def _report_ingest_summary(inputs: dict, ctx: Context) -> dict:
    started = _time.monotonic()
    promotion = inputs.get("promotion")
    source_path = inputs.get("source_path")
    if not isinstance(promotion, dict):
        return error_envelope("promotion (object) is required")
    if not isinstance(source_path, str) or not source_path.strip():
        return error_envelope("source_path is required")

    if promotion.get("promote") is False:
        stored = {
            "document_id": "",
            "raw_path": "",
            "promoted_path": "",
            "passage_count": 0,
            "skipped": True,
            "reason": str(promotion.get("rejection_reason") or "Not promoted").strip(),
        }
        markdown = _ingest_markdown(promotion, source_path, stored)
        return {
            "outputs": {
                "stored": stored,
                "ingest_markdown": markdown,
            },
            "signals": {
                "valid_output_shape": True,
                "stored_document": False,
                "has_markdown": bool(markdown),
                "passage_count": 0,
                "latency_seconds": round(_time.monotonic() - started, 3),
            },
        }

    wiki_store = ctx.tools.get("tool-wiki-store")
    if wiki_store is None:
        return error_envelope("tool-wiki-store is not available")

    stored_outputs = await wiki_store({
        "op": "write_ingest",
        "promotion": promotion,
        "source_path": source_path,
    })
    stored = stored_outputs.get("stored")
    if not isinstance(stored, dict):
        return error_envelope(stored_outputs.get("error") or "wiki store did not return stored result")

    markdown = _ingest_markdown(promotion, source_path, stored)
    return {
        "outputs": {
            "stored": stored,
            "ingest_markdown": markdown,
        },
        "signals": {
            "valid_output_shape": True,
            "stored_document": bool(stored.get("document_id")),
            "has_markdown": bool(markdown),
            "passage_count": stored.get("passage_count", 0),
            "latency_seconds": round(_time.monotonic() - started, 3),
        },
    }


def _cv_report_markdown(report: dict) -> str:
    headline = str(report.get("headline") or "CV fit report").strip()
    summary = str(report.get("summary") or "").strip()
    recommendation = str(report.get("recommendation") or "").strip()
    highlights = report.get("highlights") if isinstance(report.get("highlights"), list) else []
    concerns = report.get("concerns") if isinstance(report.get("concerns"), list) else []

    lines = [f"# {headline}", ""]
    if recommendation:
        lines += [f"**Recommendation:** {recommendation}", ""]
    if summary:
        lines += [summary, ""]
    lines += _markdown_list("Highlights", highlights)
    lines += _markdown_list("Concerns", concerns)
    return "\n".join(lines).strip()


def _answer_markdown(answer: dict) -> str:
    body = str(answer.get("answer") or "").strip()
    confidence = str(answer.get("confidence") or "").strip()
    citations = answer.get("citations") if isinstance(answer.get("citations"), list) else []
    gaps = answer.get("gaps") if isinstance(answer.get("gaps"), list) else []
    follow_ups = answer.get("follow_ups") if isinstance(answer.get("follow_ups"), list) else []

    lines = ["# Answer", ""]
    if body:
        lines += [body, ""]
    if confidence:
        lines += [f"**Confidence:** {confidence}", ""]
    lines += _markdown_list("Citations", citations)
    lines += _markdown_list("Gaps", gaps)
    lines += _markdown_list("Follow-ups", follow_ups)
    return "\n".join(lines).strip()


def _grounded_wiki_answer(question: str, parsed_note: dict, evaluation: dict) -> dict:
    """Build the wiki answer from retrieved passages only.

    This is stricter than the CV reporter path on purpose: it prevents the
    model's prior knowledge from leaking into the Session 2 knowledge-base
    answer and makes citation behaviour easy to inspect.
    """
    passages = parsed_note.get("passages") if isinstance(parsed_note.get("passages"), list) else []
    by_id = {
        str(p.get("passage_id")): p
        for p in passages
        if isinstance(p, dict) and p.get("passage_id")
    }
    ranked = evaluation.get("ranked_passages") if isinstance(evaluation.get("ranked_passages"), list) else []
    cited: list[dict] = []
    seen: set[str] = set()
    for item in ranked:
        if not isinstance(item, dict):
            continue
        passage_id = str(item.get("passage_id") or "")
        if passage_id in by_id and passage_id not in seen:
            cited.append(by_id[passage_id])
            seen.add(passage_id)
        if len(cited) >= 8:
            break

    if not cited:
        return {
            "answer": "The wiki does not currently contain enough cited evidence to answer this question.",
            "citations": [],
            "gaps": _string_list(evaluation.get("gaps")) or ["No relevant passages were retrieved."],
            "follow_ups": ["Ingest source material that directly addresses the question."],
            "confidence": "low",
        }

    principle_rows = _principle_rows(cited)
    if _asks_for_principles(question) and principle_rows:
        answer = "The retrieved wiki evidence supports these AOA principles: " + "; ".join(
            f"{name}: {quote}" for name, quote, _pid in principle_rows
        ) + "."
        citations = [pid for _name, _quote, pid in principle_rows]
    else:
        answer = "The retrieved wiki evidence says: " + " ".join(
            f"{_clean_sentence(str(p.get('quote') or ''))} ({p.get('passage_id')})."
            for p in cited[:3]
            if str(p.get("quote") or "").strip()
        ).strip()
        citations = [str(p.get("passage_id")) for p in cited[:3]]

    direct = bool(evaluation.get("direct_answer_possible"))
    return {
        "answer": answer,
        "citations": citations,
        "gaps": _string_list(evaluation.get("gaps")) if direct else (
            _string_list(evaluation.get("gaps")) or ["The answer is partial because retrieval did not mark the evidence as directly sufficient."]
        ),
        "follow_ups": [],
        "confidence": "high" if direct and len(citations) >= 3 else "medium",
    }


def _asks_for_principles(question: str) -> bool:
    lowered = question.lower()
    return "principle" in lowered and ("aoa" in lowered or "agent" in lowered)


def _principle_rows(passages: list[dict]) -> list[tuple[str, str, str]]:
    rows = []
    for passage in passages:
        pid = str(passage.get("passage_id") or "")
        quote = _clean_sentence(str(passage.get("quote") or ""))
        why = str(passage.get("why_it_matters") or "")
        name = _principle_name(why)
        if name and quote and pid:
            rows.append((name, quote, pid))
    order = {"Decompose": 0, "Compose": 1, "Substitute": 2, "Trust": 3}
    rows.sort(key=lambda row: (order.get(row[0], 99), row[0]))
    unique = []
    seen = set()
    for row in rows:
        if row[0] not in seen:
            unique.append(row)
            seen.add(row[0])
    return unique


def _principle_name(text: str) -> str:
    for name in ("Decompose", "Compose", "Substitute", "Trust"):
        if name.lower() in text.lower():
            return name
    return ""


def _clean_sentence(text: str) -> str:
    return text.strip().rstrip(".")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _ingest_markdown(promotion: dict, source_path: str, stored: dict) -> str:
    title = str(promotion.get("title") or "Wiki ingest").strip()
    summary = str(promotion.get("summary") or "").strip()
    rejection_reason = str(promotion.get("rejection_reason") or stored.get("reason") or "").strip()
    concepts = promotion.get("concepts") if isinstance(promotion.get("concepts"), list) else []
    open_questions = (
        promotion.get("open_questions")
        if isinstance(promotion.get("open_questions"), list)
        else []
    )
    promoted_passages = (
        promotion.get("promoted_passages")
        if isinstance(promotion.get("promoted_passages"), list)
        else []
    )

    if stored.get("skipped"):
        lines = [f"# Not ingested: {title}", "", f"**Source:** `{source_path}`", ""]
        if rejection_reason:
            lines += [f"**Reason:** {rejection_reason}", ""]
        if summary:
            lines += [summary, ""]
        return "\n".join(lines).strip()

    lines = [f"# Ingested: {title}", "", f"**Source:** `{source_path}`", ""]
    if summary:
        lines += [summary, ""]
    lines += [
        "## Stored",
        f"- Raw: `{stored.get('raw_path', '')}`",
        f"- Promoted: `{stored.get('promoted_path', '')}`",
        f"- Passages indexed: {stored.get('passage_count', 0)}",
        "",
    ]
    lines += _markdown_list(
        "Concepts",
        [_concept_label(item) for item in concepts],
    )
    lines += _markdown_list(
        "Promoted Passages",
        [_passage_label(item) for item in promoted_passages],
    )
    lines += _markdown_list("Open Questions", open_questions)
    return "\n".join(lines).strip()


def _concept_label(value: object) -> str:
    if isinstance(value, dict):
        name = str(value.get("name") or "").strip()
        description = str(value.get("description") or "").strip()
        return f"{name}: {description}" if name and description else name or description
    return str(value).strip()


def _passage_label(value: object) -> str:
    if isinstance(value, dict):
        passage_id = str(value.get("passage_id") or "").strip()
        why = str(value.get("why_it_matters") or "").strip()
        return f"{passage_id}: {why}" if passage_id and why else passage_id or why
    return str(value).strip()


def _markdown_list(title: str, values: list) -> list[str]:
    if not values:
        return []
    lines = [f"## {title}"]
    for value in values:
        text = str(value).strip()
        if text:
            lines.append(f"- {text}")
    return lines + [""]

# ----------------------------------------------------------------------
# reporter-agent-evidence / reporter-flow-audit — deterministic governance
# evidence reports (no model call)
# ----------------------------------------------------------------------

_SCOPE_BANNER = (
    "> **Findings and evidence only. This is not a classification or compliance determination.**\n"
    "> Scope: EU AI Act (Regulation 2024/1689) only; estate artefacts only "
    "(capability cards, registry lifecycle, traces) - not source code, models, "
    "training data, or the legal context of a real deployment.\n"
    "> Annex III marker matches require contextual legal assessment. Verify the "
    "enacted application schedule and current guidance before deployment.\n"
)

_FOOTER = (
    "\n---\n\n*AOA does not confer permission or compliance; it makes evidence "
    "hooks and control surfaces explicit.*\n"
)

_SEVERITY_MARK = {"green": "🟢", "amber": "🟠", "red": "🔴", "unknown": "⚪"}
_ARTICLE_ORDER = ["Art 9", "Art 10", "Art 11", "Art 12", "Art 13", "Art 14", "Art 72"]
_BANNED_WORDS = ("compliant", "complies", "certified")


async def _report_agent_evidence(inputs: dict, ctx: Context) -> dict:
    inventory = inputs.get("inventory")
    findings_obj = inputs.get("findings")
    if not isinstance(inventory, list):
        return error_envelope("inventory (array) is required")
    if not isinstance(findings_obj, dict):
        return error_envelope("findings (object) is required")

    findings = [
        finding
        for finding in findings_obj.get("findings") or []
        if isinstance(finding, dict) and not _is_plan_finding(finding)
    ]
    summary = findings_obj.get("summary") or {}
    if not isinstance(summary, dict):
        summary = {}

    lines: list[str] = ["# Agent card evidence check", "", _SCOPE_BANNER]
    lines.append(
        f"Scanned **{summary.get('aus_scanned', len(inventory))} AUs** - "
        f"{summary.get('annex_iii_candidates', 0)} Annex III candidates for contextual legal review. "
        f"Card findings: {summary.get('red', 0)} red / "
        f"{summary.get('amber', 0)} amber / {summary.get('green', 0)} green / "
        f"{summary.get('unknown', 0)} corpus-silent."
    )
    lines.append("")
    _append_knowledge_usage(lines, summary, "agent-card evidence")
    _append_component_evidence(lines, findings, heading="Agent card evidence")
    _append_corpus_gaps(lines, findings)
    lines.append(_FOOTER)
    markdown = "\n".join(lines)
    lowered = markdown.lower()
    all_findings_rendered = all(
        str(finding.get("capability_id") or "?") in markdown
        and str(finding.get("article") or "?") in markdown
        for finding in findings
    )
    return {
        "outputs": {"findings_markdown": markdown},
        "signals": {
            "valid_output_shape": True,
            "has_markdown": bool(markdown.strip()),
            "no_compliance_verdict": not any(
                word in lowered for word in _BANNED_WORDS
            ),
            "all_findings_rendered": all_findings_rendered,
        },
    }


async def _report_flow_audit(inputs: dict, ctx: Context) -> dict:
    plans = inputs.get("plans")
    findings_obj = inputs.get("findings")
    audit_scope = inputs.get("audit_scope")
    if not isinstance(plans, list):
        return error_envelope("plans (array) is required")
    if not isinstance(findings_obj, dict):
        return error_envelope("findings (object) is required")
    if not isinstance(audit_scope, dict):
        audit_scope = {}

    plan_findings = _plan_findings(findings_obj, [], [])
    audited_plans = [
        plan
        for index, plan in enumerate(plans)
        if isinstance(plan, dict) and _findings_for_plan(plan, index, plan_findings)
    ]
    summary = findings_obj.get("summary") or {}
    if not isinstance(summary, dict):
        summary = {}

    counts = summary.get("plan_counts") or {}
    if not isinstance(counts, dict):
        counts = {}
    lines: list[str] = ["# Flow audit - execution evidence", "", _SCOPE_BANNER]
    if audit_scope.get("include_legacy"):
        lines.append(
            "**Audit scope:** current result-governance traces plus "
            f"**{audit_scope.get('legacy_employment_plans_included', 0)} legacy employment traces**."
        )
    else:
        hidden = int(audit_scope.get("legacy_employment_plans_excluded") or 0)
        lines.append(
            "**Audit scope:** current `human-review-before-release` traces only. "
            f"**{hidden} legacy employment traces hidden**; enable **Show legacy history** "
            "in Studio to include them."
        )
    lines.append("")
    lines.append(
        f"Observed **{summary.get('plans_observed', len(plans))} plans/traces** and assessed "
        f"**{summary.get('employment_plans_assessed', len(audited_plans))} employment-shaped flows**. "
        f"Flow findings: {counts.get('red', 0)} red / {counts.get('amber', 0)} amber / "
        f"{counts.get('green', 0)} green / {counts.get('unknown', 0)} corpus-silent."
    )
    lines.append("")
    _append_plan_governance(
        lines,
        audited_plans,
        plan_findings,
        heading="Flow audit evidence",
        intro=(
            "Post-execution evidence checks selected-card eligibility, draft creation, "
            "exact-result review, and review-before-release or quarantine for employment-shaped flows."
        ),
        include_green_details=True,
    )
    _append_knowledge_usage(lines, summary, "flow evidence")
    _append_corpus_gaps(lines, plan_findings)
    lines.append(_FOOTER)
    markdown = "\n".join(lines)
    lowered = markdown.lower()
    all_plans_rendered = all(
        _plan_label(plan, index) in markdown
        for index, plan in enumerate(audited_plans)
    )
    all_findings_rendered = all(
        _flow_finding_rendered(finding, markdown)
        for finding in plan_findings
    )
    return {
        "outputs": {"findings_markdown": markdown},
        "signals": {
            "valid_output_shape": True,
            "has_markdown": bool(markdown.strip()),
            "no_compliance_verdict": not any(
                word in lowered for word in _BANNED_WORDS
            ),
            "all_plans_rendered": all_plans_rendered,
            "all_findings_rendered": all_findings_rendered,
        },
    }


def _append_plan_governance(
    lines: list[str],
    plans: list,
    plan_findings: list[dict],
    heading: str = "End-to-end plan governance",
    intro: str = (
        "Plan-level evidence evaluates observed composition and declared use context; "
        "it is the primary governance view in this report."
    ),
    include_green_details: bool = False,
) -> None:
    lines += [f"## {heading}", ""]
    lines.append(intro)
    lines.append("")

    if not plans:
        lines.append(
            "No plans/traces were observed. End-to-end composition and use-context "
            "appropriateness therefore cannot be established from this estate scan."
        )
        lines.append("")
        return

    for index, plan in enumerate(plans):
        if not isinstance(plan, dict):
            plan = {"plan_id": f"plan-{index + 1}", "value": plan}
        matched = _findings_for_plan(plan, index, plan_findings)
        lines += [f"### {_plan_label(plan, index)}", ""]
        lines.append("| Plan field / evaluator check | Observed value / posture |")
        lines.append("|---|---|")
        lines.append(
            f"| Workflow | {_markdown_cell(_plan_value(plan, matched, 'workflow'))} |"
        )
        if plan.get("plan_digest"):
            lines.append(f"| Plan digest | `{_markdown_cell(plan['plan_digest'])}` |")
        lines.append(
            f"| Resolved composition | {_markdown_cell(_plan_composition(plan, matched))} |"
        )
        lines.append(
            f"| Use context | {_markdown_cell(_plan_value(plan, matched, 'use_context'))} |"
        )
        governance = plan.get("governance") if isinstance(plan.get("governance"), dict) else {}
        decision = governance.get("decision") or "not observed"
        card_eligibility = (
            governance.get("card_eligibility")
            if isinstance(governance.get("card_eligibility"), dict)
            else {}
        )
        lines.append(f"| Plan eligibility decision | `{_markdown_cell(decision)}` |")
        lines.append(
            f"| Selected evaluator eligible | {_markdown_cell(card_eligibility.get('eligible', 'not observed'))} |"
        )
        lines.append(
            f"| Matched card constraint | {_markdown_cell(card_eligibility.get('matched_constraint') or 'not observed')} |"
        )
        lines.append(
            f"| Result release policy | {_markdown_cell(plan.get('release_policy') or governance.get('release_policy') or 'not observed')} |"
        )
        lines.append(
            f"| Eligibility before application | {_order_evidence(plan.get('eligibility_preceded_application_invoke'))} |"
        )
        lines.append(
            f"| First application invocation | {_markdown_cell(plan.get('first_application_invoke_at') or 'not observed')} |"
        )
        lines.append(
            f"| Application complete before draft | {_order_evidence(plan.get('application_completed_before_draft'))} |"
        )
        draft = plan.get("draft") if isinstance(plan.get("draft"), dict) else {}
        lines.append(
            f"| Draft result digest | `{_markdown_cell(draft.get('result_digest') or 'not observed')}` |"
        )
        result_hold = plan.get("result_hold") if isinstance(plan.get("result_hold"), dict) else {}
        lines.append(f"| Draft held for review | {'yes' if result_hold else 'no'} |")
        review = plan.get("review") if isinstance(plan.get("review"), dict) else {}
        lines.append(f"| Human result review | {_markdown_cell(review or 'not observed')} |")
        lines.append(
            f"| Draft before review | {_order_evidence(plan.get('draft_preceded_review'))} |"
        )
        release = plan.get("release") if isinstance(plan.get("release"), dict) else {}
        quarantine = plan.get("quarantine") if isinstance(plan.get("quarantine"), dict) else {}
        release_summary = {
            key: release.get(key)
            for key in ("timestamp", "result_digest", "actor_id")
            if release.get(key)
        }
        lines.append(
            f"| Result release | {_markdown_cell(release_summary or 'not observed')} |"
        )
        lines.append(
            f"| Result quarantine | {_markdown_cell(quarantine or 'not observed')} |"
        )
        lines.append(
            f"| Review before release | {_order_evidence(plan.get('review_preceded_release'))} |"
        )
        lines.append(
            f"| Review before quarantine | {_order_evidence(plan.get('review_preceded_quarantine'))} |"
        )
        lines.append(
            f"| Released result matches approved draft | {_order_evidence(plan.get('released_result_matches_draft'))} |"
        )
        lines.append(
            f"| Final flow status | `{_markdown_cell(plan.get('execution_status') or 'unknown')}` |"
        )
        if matched:
            for finding_index, finding in enumerate(matched):
                severity = str(finding.get("severity") or "unknown").lower()
                mark = _SEVERITY_MARK.get(severity, _SEVERITY_MARK["unknown"])
                check = _plan_check_label(finding, finding_index)
                lines.append(
                    f"| {_markdown_cell(check)} | {_markdown_cell(f'{mark} {severity}')} |"
                )
        elif plan.get("severity"):
            severity = str(plan["severity"]).lower()
            mark = _SEVERITY_MARK.get(severity, _SEVERITY_MARK["unknown"])
            lines.append(f"| Plan evidence finding | {mark} {_markdown_cell(severity)} |")
        lines.append("")
    lines.append(
        "_Green means evaluator evidence is present for the observed composition; "
        "it is not a legal or deployment determination._"
    )
    lines.append("")

    attention = [
        finding
        for finding in plan_findings
        if include_green_details
        or str(finding.get("severity") or "unknown").lower() != "green"
    ]
    if not attention:
        return

    detail_heading = "Flow evidence details" if include_green_details else "Non-green plan details"
    lines += [f"### {detail_heading}", ""]
    for index, finding in enumerate(attention):
        severity = str(finding.get("severity") or "unknown").lower()
        mark = _SEVERITY_MARK.get(severity, _SEVERITY_MARK["unknown"])
        label = _plan_finding_label(finding, index)
        lines += [f"#### {mark} {label}", ""]
        if finding.get("checked"):
            lines.append(f"- **Checked:** {finding['checked']}")
        _append_evidence(lines, finding.get("evidence"))
        _append_regulation_citations(lines, finding)
        if finding.get("gap"):
            lines.append(f"- **Gap:** {finding['gap']}")
        if finding.get("remediation_hint"):
            lines.append(f"- **Next step:** {finding['remediation_hint']}")
        if finding.get("control"):
            lines.append(f"- **Control:** {finding['control']}")
        if finding.get("interpretation"):
            lines.append(f"- **Boundary:** {finding['interpretation']}")
        lines.append("")


def _order_evidence(value: object) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "not observed"


def _flow_finding_rendered(finding: dict, markdown: str) -> bool:
    identity = str(
        finding.get("trace_id")
        or finding.get("plan_id")
        or finding.get("plan_digest")
        or finding.get("finding_id")
        or ""
    )
    checked = str(finding.get("checked") or "")
    citation = finding.get("regulation_citation")
    citation_parts: list[str] = []
    if isinstance(citation, dict):
        citation_parts = [
            str(citation.get(key) or "")
            for key in ("passage_id", "source_path", "quote")
            if citation.get(key)
        ]
    return (
        bool(identity and checked)
        and identity in markdown
        and checked in markdown
        and all(part in markdown for part in citation_parts)
    )


def _append_component_evidence(
    lines: list[str],
    findings: list[dict],
    heading: str = "Component evidence appendix",
) -> None:
    by_cap: dict[str, dict[str, dict]] = {}
    risk_by_cap: dict[str, str] = {}
    for finding in findings:
        cap = str(finding.get("capability_id") or "?")
        by_cap.setdefault(cap, {})[str(finding.get("article") or "?")] = finding
        risk_by_cap[cap] = str(finding.get("risk_tier") or "")

    lines += [f"## {heading}", ""]
    lines.append(
        "Individual AU evidence does not establish composition/use-context "
        "appropriateness; it records component-level evidence hooks only."
    )
    lines.append("")
    lines.append("| AU | risk tier | " + " | ".join(_ARTICLE_ORDER) + " |")
    lines.append("|---|---|" + "---|" * len(_ARTICLE_ORDER))
    for cap in sorted(by_cap):
        marks = []
        for article in _ARTICLE_ORDER:
            finding = by_cap[cap].get(article)
            marks.append(
                _SEVERITY_MARK.get(finding.get("severity"), "?") if finding else "-"
            )
        risk = (
            "**Annex III candidate**"
            if risk_by_cap.get(cap, "").startswith("Annex III candidate")
            else "no employment marker found"
        )
        lines.append(f"| `{cap}` | {risk} | " + " | ".join(marks) + " |")
    lines.append("")
    lines.append(
        "_Green means evidence present - never obligation satisfied. "
        "Art 10 is capped at amber by construction._"
    )
    lines.append("")

    attention = [
        finding
        for finding in findings
        if finding.get("severity") in ("red", "amber", "unknown")
    ]
    if not attention:
        return

    lines += ["### Component findings needing attention", ""]
    for finding in sorted(
        attention,
        key=lambda item: (
            {"red": 0, "amber": 1, "unknown": 2}.get(item.get("severity"), 3),
            item.get("capability_id", ""),
            item.get("article", ""),
        ),
    ):
        mark = _SEVERITY_MARK.get(finding.get("severity"), "")
        lines.append(
            f"#### {mark} {finding.get('capability_id')} - "
            f"{finding.get('article')} ({finding.get('obligation')})"
        )
        lines.append("")
        lines.append(f"- **Checked:** {finding.get('checked', '')}")
        _append_evidence(lines, finding.get("evidence"))
        _append_regulation_citations(lines, finding)
        if finding.get("gap"):
            lines.append(f"- **Gap:** {finding['gap']}")
        if finding.get("remediation_hint"):
            lines.append(f"- **Next step:** {finding['remediation_hint']}")
        lines.append("")


def _append_knowledge_usage(lines: list[str], summary: dict, scope: str) -> None:
    knowledge = summary.get("knowledge_evidence")
    if not isinstance(knowledge, dict):
        return
    queries = knowledge.get("queries") if isinstance(knowledge.get("queries"), dict) else {}
    passage_ids = (
        knowledge.get("passage_ids")
        if isinstance(knowledge.get("passage_ids"), dict)
        else {}
    )
    citations = (
        knowledge.get("citations")
        if isinstance(knowledge.get("citations"), dict)
        else {}
    )
    lines += ["## Wiki governance evidence", ""]
    lines.append(
        f"The deterministic {scope} policy does not contain regulation text. It calls "
        f"`{knowledge.get('tool') or 'tool-wiki-store'}` and preserves the returned passage evidence."
    )
    lines.append("")
    lines.append("| Evidence target | Wiki query | Retrieved passage | Source |")
    lines.append("|---|---|---|---|")
    for label, query in queries.items():
        citation = citations.get(label) if isinstance(citations.get(label), dict) else {}
        lines.append(
            f"| {_markdown_cell(label)} | `{_markdown_cell(query)}` | "
            f"`{_markdown_cell(passage_ids.get(label) or 'corpus silent')}` | "
            f"`{_markdown_cell(citation.get('source_path') or 'not observed')}` |"
        )
    lines.append("")
    lines.append(
        "The responsibility trace shows each corresponding wiki query and returned citation."
    )
    lines.append("")
    for label in queries:
        citation = citations.get(label)
        if not isinstance(citation, dict):
            continue
        quote = str(citation.get("quote") or "").strip()
        if not quote:
            continue
        lines += [f"### Retrieved {label} passage", ""]
        lines.append(
            f"`{citation.get('passage_id')}` from `{citation.get('source_path')}`"
        )
        lines.append("")
        for quote_line in quote.splitlines():
            lines.append(f"> {quote_line}" if quote_line else ">")
        lines.append("")


def _append_corpus_gaps(lines: list[str], findings: list[dict]) -> None:
    silent = sorted({
        finding.get("article", "?")
        for finding in findings
        if finding.get("corpus_silent")
    })
    if not silent:
        return
    lines += ["## Corpus gaps", ""]
    lines.append(
        "The regulations corpus is silent for: " + ", ".join(silent) +
        ". These findings abstain until the relevant regulation note is ingested."
    )
    lines.append("")


def _is_plan_finding(finding: dict) -> bool:
    scope = str(finding.get("scope") or finding.get("finding_scope") or "").lower()
    if scope in {"plan", "trace", "composition", "end-to-end"}:
        return True
    return any(
        finding.get(key) not in (None, "")
        for key in ("trace_id", "plan_id", "plan_digest")
    ) and not finding.get("capability_id")


def _plan_findings(
    findings_obj: dict,
    raw_findings: list[dict],
    plans: list,
) -> list[dict]:
    collected: list[dict] = [
        finding for finding in raw_findings if _is_plan_finding(finding)
    ]
    for key in ("plan_findings", "plan_evaluations"):
        values = findings_obj.get(key)
        if isinstance(values, list):
            collected.extend(value for value in values if isinstance(value, dict))

    evaluated_plans = findings_obj.get("plans")
    if isinstance(evaluated_plans, list):
        for index, evaluation in enumerate(evaluated_plans):
            if isinstance(evaluation, dict):
                collected.extend(_expand_plan_evaluation(evaluation, index))

    for index, plan in enumerate(plans):
        if not isinstance(plan, dict):
            continue
        embedded = plan.get("findings")
        if isinstance(embedded, list):
            collected.extend(
                _inherit_plan_identity(finding, plan, index)
                for finding in embedded
                if isinstance(finding, dict)
            )
        elif plan.get("severity"):
            collected.append(_inherit_plan_identity(plan, plan, index))

    unique: list[dict] = []
    seen: set[str] = set()
    for finding in collected:
        marker = json.dumps(finding, sort_keys=True, default=str)
        if marker not in seen:
            unique.append(finding)
            seen.add(marker)
    return unique


def _expand_plan_evaluation(evaluation: dict, index: int) -> list[dict]:
    nested = evaluation.get("findings")
    if isinstance(nested, list):
        return [
            _inherit_plan_identity(finding, evaluation, index)
            for finding in nested
            if isinstance(finding, dict)
        ]
    return [_inherit_plan_identity(evaluation, evaluation, index)]


def _inherit_plan_identity(finding: dict, plan: dict, index: int) -> dict:
    inherited = dict(finding)
    for key in ("trace_id", "plan_id", "plan_digest", "workflow"):
        if not inherited.get(key) and plan.get(key):
            inherited[key] = plan[key]
    inherited.setdefault("plan_index", index)
    return inherited


def _findings_for_plan(
    plan: dict,
    index: int,
    plan_findings: list[dict],
) -> list[dict]:
    identities = {
        str(plan.get(key))
        for key in ("trace_id", "plan_id", "plan_digest")
        if plan.get(key) not in (None, "")
    }
    matched = []
    for finding in plan_findings:
        finding_ids = {
            str(finding.get(key))
            for key in ("trace_id", "plan_id", "plan_digest")
            if finding.get(key) not in (None, "")
        }
        if identities & finding_ids or finding.get("plan_index") == index:
            matched.append(finding)
    return matched


def _plan_label(plan: dict, index: int) -> str:
    trace_id = str(plan.get("trace_id") or "").strip()
    plan_id = str(plan.get("plan_id") or plan.get("plan_digest") or "").strip()
    if trace_id and plan_id and plan_id != trace_id:
        return f"`{trace_id}` / `{plan_id}`"
    identity = trace_id or plan_id or f"plan-{index + 1}"
    return f"`{identity}`"


def _plan_finding_label(finding: dict, index: int) -> str:
    identity = (
        finding.get("trace_id")
        or finding.get("plan_id")
        or finding.get("plan_digest")
        or finding.get("finding_id")
        or f"plan-finding-{index + 1}"
    )
    subject = finding.get("article") or finding.get("obligation") or finding.get("check")
    return f"{identity} - {subject}" if subject else str(identity)


def _plan_check_label(finding: dict, index: int) -> str:
    return str(
        finding.get("article")
        or finding.get("obligation")
        or finding.get("check")
        or finding.get("finding_id")
        or f"Evaluator check {index + 1}"
    )


def _plan_value(plan: dict, findings: list[dict], key: str) -> object:
    if plan.get(key) not in (None, "", [], {}):
        return plan[key]
    for finding in findings:
        if finding.get(key) not in (None, "", [], {}):
            return finding[key]
        evidence = finding.get("evidence")
        if isinstance(evidence, dict) and evidence.get(key) not in (None, "", [], {}):
            return evidence[key]
    return "not supplied"


def _plan_composition(plan: dict, findings: list[dict]) -> object:
    for key in (
        "capability_ids",
        "resolved_composition",
        "capabilities",
        "composition",
        "resolved_plan",
        "plan",
    ):
        value = _plan_value(plan, findings, key)
        if value != "not supplied":
            if isinstance(value, list):
                capabilities = [
                    str(
                        item.get("capability")
                        or item.get("capability_id")
                        or item.get("id")
                        or ""
                    )
                    if isinstance(item, dict)
                    else str(item)
                    for item in value
                ]
                capabilities = [item for item in capabilities if item]
                if capabilities:
                    return " -> ".join(capabilities)
            return value
    return "not supplied"


def _markdown_cell(value: object) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def _append_evidence(lines: list[str], evidence: object) -> None:
    if evidence in (None, "", [], {}):
        return
    if isinstance(evidence, dict) and any(
        key in evidence for key in ("kind", "ref", "value")
    ):
        kind = str(evidence.get("kind") or "").strip()
        ref = str(evidence.get("ref") or "").strip()
        value = _display_value(evidence.get("value"))
        prefix = " - ".join(part for part in (kind, f"`{ref}`" if ref else "") if part)
        rendered = f"{prefix} = `{value}`" if prefix else f"`{value}`"
        lines.append(f"- **Evidence:** {rendered}")
        return
    lines.append(f"- **Evidence:** `{_display_value(evidence)}`")


def _display_value(value: object) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return str(value)


def _append_regulation_citations(lines: list[str], finding: dict) -> None:
    citations: list[object] = []
    singular = finding.get("regulation_citation")
    if singular:
        citations.append(singular)
    for key in ("regulation_citations", "citations"):
        value = finding.get(key)
        if isinstance(value, list):
            citations.extend(value)
        elif value:
            citations.append(value)

    for citation in citations:
        if not isinstance(citation, dict):
            lines.append(f"- **Regulation:** {citation}")
            continue
        passage_id = str(citation.get("passage_id") or "").strip()
        source = str(citation.get("source_path") or citation.get("source") or "").strip()
        quote = str(citation.get("quote") or citation.get("passage") or "").strip()
        reference = f"`{passage_id}`" if passage_id else "evaluator-supplied passage"
        if source:
            reference += f" from `{source}`"
        lines.append(f"- **Regulation:** {reference}")
        if quote:
            for quote_line in quote.splitlines():
                lines.append(f"  > {quote_line}" if quote_line else "  >")


if __name__ == "__main__":
    run(handle)
