---
title: Scale and operational lessons for AOA
source_type: curated-raw-note
curated_from:
  - aoa-knowledge/raw/research/2026-04-27-aoa-scale-lessons-from-soa-microservices.md
  - aoa-knowledge/raw/research/2026-04-26-evaluation-observability-gap.md
---

# Scale and Operational Lessons for AOA

Scaling AOA is not only about requests per second. It is about quality, cost,
side effects, replacement, trust, and operational control.

## Scale corollaries for the core principles

| AOA principle | Scale corollary |
| --- | --- |
| Bounded, contracted scope | AU contracts need capacity, concurrency, quota, cost, tenancy, and degradation semantics. |
| Composition at the contract | Contracts must carry trace context, tool permissions, SLOs, failure modes, and dependency metadata. |
| Replacement as registration | Replacement needs shadowing, canarying, rollback, load-aware routing, and fleet management. |
| Observed, not asserted | Observation must support circuit breaking, cost enforcement, quality sampling, and anomaly detection. |

## Failure modes AOA must avoid

| Historical failure mode | AOA version |
| --- | --- |
| ESB hairball | The orchestrator or control tower becomes the only place that understands how work happens. |
| Distributed monolith | AUs are separately registered but cannot be replaced independently because prompts, tools, memory, and workflows are entangled. |
| Service sprawl | Overlapping AUs, shadow agents, stale cards, duplicated tools, and unmanaged cost. |
| Observability gap | Traces cannot explain why a decision was made or which tool output changed the result. |
| Retry storm | Agents retry, re-plan, or spawn more work until model, tool, or budget limits saturate. |
| Hidden data coupling | AUs depend on undocumented memory, prompt conventions, or vector-store assumptions. |
| Cost invisibility | Token, tool, retrieval, and routing cost are visible only after the fact. |
| Governance lag | Manual approvals cannot keep up, so teams bypass the registry. |

## Runtime controls

Useful AOA contracts eventually need fields for:

- concurrency limit
- queue policy
- token budget
- cost budget
- tool rate limits
- fanout limit
- degradation policy
- circuit-breaker policy
- idempotency policy
- compensation policy for side effects

The course system does not need to implement all of these. It should name them
so participants can see the path from toy demo to production architecture.

## Operational model

AOA needs a platform-team shape similar to cloud-native platforms and SRE:

- registry validation and approval workflow
- AU identity and tool credentials
- runtime policy and orchestration substrate
- traces, metrics, logs, evaluation, and audit
- cost budgets and chargeback/showback
- safety gates and incident response

## Teaching point

The danger is not that agents are too different from services. The danger is
that they are similar enough that we repeat the same distributed-systems
mistakes while adding probabilistic output, model cost, prompt coupling, and
tool side effects.
