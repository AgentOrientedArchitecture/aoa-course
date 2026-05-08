---
title: AOA adoption action plan
source_type: curated-action-kit
---

# AOA Adoption Action Plan

AOA adoption should start with visibility and ownership, not with a grand
enterprise agent platform. The first useful question is not "how do we build
an agent mesh?" It is "what agentic work already exists, who owns it, what
does it touch, and which parts are mature enough to become Agentic Units?"

## The practical starting point

Use one business domain or value stream as the boundary. Keep the first
assessment small enough to finish. A focused assessment produces better
evidence than an enterprise-wide survey that never settles.

The first six artefacts are:

1. AI and agent inventory
2. Agentic Unit candidate list
3. Maturity profile
4. Principles map
5. Roadmap backlog
6. Governance cadence

## 1. AI and agent inventory

Purpose: establish what already exists before governing or composing it.

Minimum fields:

| Field | Notes |
| --- | --- |
| Name | Tool, agent, automation, copilot, script, or vendor feature |
| Business domain | Where it is used |
| Owner | Business owner and technical owner |
| Lifecycle state | Idea, POC, pilot, production, deprecated, retired |
| Data touched | Customer, employee, regulated, operational, public, synthetic |
| Tools or systems touched | APIs, databases, file stores, SaaS tools, queues, human channels |
| Autonomy level | Advisory, drafted action, supervised action, bounded autonomous action |
| Risk tier | Local risk category |
| Human oversight | Approval, review, escalation, timeout |
| Evaluation evidence | Tests, acceptance results, user feedback, incidents, red-team notes |

## 2. Agentic Unit candidate list

Purpose: decide which initiatives deserve formal Agentic Unit treatment.

A good candidate AU has:

- a stable capability boundary
- a named owner
- clear inputs and outputs
- declared tool or system access
- a known autonomy level
- a risk tier
- evidence that it does useful work
- a reason to be discovered or reused by others

Not every AI feature should become an AU. Some should stay local, some should
be retired, and some should be merged into a larger capability.

## 3. Maturity profile

Purpose: show uneven readiness across the dimensions that matter.

Score each dimension separately. Do not average the scores into one maturity
number. The weak dimension is often the one that breaks the roadmap.

Dimensions:

- strategic intent
- portfolio visibility
- AU definition
- discovery and registry
- standards and integration
- context and data access
- orchestration and runtime control
- evaluation and observability
- governance and risk
- people and work redesign

Use a simple five-point scale:

| Score | Meaning |
| --- | --- |
| 1 | Ad hoc |
| 2 | Emerging |
| 3 | Defined |
| 4 | Managed |
| 5 | Adaptive |

## 4. Principles map

Purpose: translate generic AOA principles into local rules.

For each principle, record:

- local interpretation
- non-negotiable rule
- example
- owner
- evidence required

Example:

| Generic principle | Local rule |
| --- | --- |
| Human oversight is designed, not improvised | Customer-impacting decisions require accountable human approval until the domain has agreed evidence of safe automation |

## 5. Roadmap backlog

Purpose: convert maturity gaps into sequenced adoption work.

Use Now / Next / Later rather than false-precision dates.

| Horizon | Focus | Example actions |
| --- | --- | --- |
| Now | Visibility and safe learning | Inventory existing activity, identify owners, choose risk tiers, write AU template |
| Next | Discoverability and controlled reuse | Publish capability cards, launch a small registry, add evaluation evidence |
| Later | Orchestration and adaptive work discovery | Compose multi-AU workflows, add NFR-based selection, automate governance checks |

Prioritise where value, readiness, control, learning, and reuse overlap.

## 6. Governance cadence

Purpose: keep adoption alive as systems, standards, and risks change.

Decide:

- who reviews the inventory
- who approves new registered AUs
- how often maturity is reassessed
- how incidents are reviewed
- how principles are updated
- which metrics are reported

## First week checklist

1. Pick one domain or value stream.
2. List existing AI and agentic activity in that boundary.
3. Choose one candidate AU and write a lightweight inventory record.
4. Score the ten maturity dimensions with evidence.
5. Identify the one or two bottleneck dimensions blocking safe adoption.
6. Draft a Now / Next / Later roadmap.
7. Schedule the first governance review.

