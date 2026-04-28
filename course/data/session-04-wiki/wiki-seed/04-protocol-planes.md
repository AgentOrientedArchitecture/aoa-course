---
title: Protocol planes for AOA
source_type: curated-raw-note
curated_from:
  - aoa-knowledge/raw/research/2026-04-27-aoa-course-deep-research-protocols-identity-observability.md
  - aoa-knowledge/raw/research/2026-04-18-open-standards-reference-architectures.md
  - aoa-knowledge/raw/research/2026-04-26-mcp-tool-protocol-landscape.md
---

# Protocol Planes for AOA

The useful course framing is not "A2A versus MCP." They sit at different
boundaries. AOA needs a protocol-plane model so participants can place each
standard in the architecture.

## Protocol-plane model

| Plane | Boundary | Typical standards or patterns | Course message |
| --- | --- | --- | --- |
| Tool and context plane | agent or model to tools, resources, prompts, and context | MCP | MCP is the natural way to expose tools and context safely. |
| Agent task plane | agent to remote opaque agent | A2A | A2A is for delegating work to another agent through Agent Cards, messages, tasks, parts, and artifacts. |
| REST invocation plane | agents exposed as conventional HTTP APIs | ACP variants, OpenAPI-style patterns | REST remains useful where simple HTTP invocation is enough. |
| Mesh and infrastructure plane | discovery, identity, messaging, and observability across fleets | AGNTCY/OASF/SLIM-style work | Larger fleets need shared infrastructure patterns beyond single-agent calls. |
| API workflow plane | deterministic multi-step API workflows | OpenAPI, AsyncAPI, Arazzo | Not every workflow should be agentic; deterministic APIs still matter. |
| Observability plane | traces, spans, metrics, evaluation and audit | OpenTelemetry GenAI, OpenInference | "Observed, not asserted" needs standard telemetry. |

## How the course demo maps this

The course implementation uses A2A for Agentic Unit to Agentic Unit
orchestration. The planner calls parser, evaluator, and reporter AUs through
A2A JSON-RPC message sending.

The tools are MCP-backed but exposed through registered AOA tool bridges. That
keeps the demo understandable: tools do deterministic work, agents do model
work, and the registry can show both as capabilities.

## Identity and authorization

Production AOA needs more than a shared API key. Agent identity is a compound
of workload identity, user delegation, tenant context, tool authorization, and
auditability.

Useful minimum concepts for the course wiki:

- workload identity identifies the AU runtime
- user delegation preserves the human or upstream subject
- scoped tokens limit what a tool call can do
- RBAC gives stable coarse permissions
- ABAC or policy-as-code handles runtime context and risk
- human approval gates protect high-impact side effects

## Observability and evaluation

The trace is the proof of what happened. A useful AOA trace should eventually
include:

- user intent and orchestration ID
- AU blueprint and capability-card version
- model provider and model
- token counts, latency, and cost signals
- tool inputs, outputs, errors, and policy decisions
- retrieval or memory reads and writes
- evaluator scores, confidence, refusals, and validation signals
- human approvals and side-effect records

Without this layer, "observed, not asserted" remains a slogan rather than a
control loop.
