---
title: Standards and governance context for AOA
source_type: curated-raw-note
curated_from:
  - aoa-knowledge/raw/research/2026-04-18-open-standards-reference-architectures.md
  - aoa-knowledge/raw/research/2026-04-27-aoa-course-deep-research-protocols-identity-observability.md
---

# Standards and Governance Context for AOA

There is no mature, TOGAF-level, vendor-neutral reference architecture for
agentic AI yet. There are useful standards, frameworks, and security patterns,
but most cover risk, governance, protocol fragments, or operational controls
rather than a full agent architecture.

## Useful standards and bodies

| Body or standard | Useful for AOA | Limitation |
| --- | --- | --- |
| NIST AI RMF and GenAI Profile | risk framing, governance, measurement | not an agent reference architecture |
| ISO/IEC 42001 | certifiable AI management system | management system, not AOA design |
| MITRE ATLAS | threat knowledge base for AI systems | threat model, not architecture |
| OWASP LLM and Agentic Top 10 | security risks and mitigations | security patterns only |
| EU AI Act | implied controls: risk management, logging, oversight, transparency, monitoring | legal/regulatory frame, not implementation design |
| OpenTelemetry GenAI and OpenInference | traces, spans, evaluation, model/tool telemetry | observability layer, not end-to-end architecture |
| MCP | tool/context protocol | not agent-to-agent delegation |
| A2A | agent-to-agent task delegation and Agent Cards | not a registry ranking or governance system |
| OASF and AGNTCY-style work | schema and infrastructure direction for agent ecosystems | still emerging |

## The gap

The raw research repeatedly identifies a gap: standards and vendors have many
pieces, but no widely accepted agentic reference architecture that ties
contracts, registry, planning, identity, tool permissions, observability,
evaluation, and governance into one coherent pattern.

AOA can occupy that gap as a reference architecture and teaching model.

## Governance primitives to teach early

Even a small course system should name these ideas:

- capability publication and approval
- AU ownership and versioning
- registry visibility and discoverability
- model and provider provenance
- tool permission scope
- user delegation and workload identity
- trace retention and redaction
- evaluator and human review loops
- deprecation and rollback

## Compliance implication

Regulation and standards often require evidence: logs, risk assessments,
human oversight, data governance, model documentation, and post-market
monitoring. AOA's trace and evaluation model can be positioned as the
technical substrate that produces this evidence.

## Teaching point

Do not present AOA as a replacement for NIST, ISO, OWASP, OpenTelemetry, MCP,
or A2A. Present it as an architecture that composes these concerns into a
practical operating model for agentic systems.
