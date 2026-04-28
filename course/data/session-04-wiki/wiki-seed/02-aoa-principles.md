---
title: Four working principles for AOA
source_type: curated-raw-note
curated_from:
  - aoa-knowledge/raw/research/2026-04-21-aoa-principles-lineage-chains.md
  - aoa-knowledge/raw/research/2026-04-27-aoa-scale-lessons-from-soa-microservices.md
---

# Four Working Principles for AOA

These principles are the useful starter set for the course wiki. They are
phrased for Agentic Units, but most of the lineage comes from SOA,
microservices, and SRE.

## 1. Decompose: bounded, contracted scope

An Agentic Unit should do one thing well enough to be named, contracted,
tested, observed, and replaced. Decomposition is not just "make it smaller."
The boundary should follow ownership, capability, change frequency, risk, and
the evidence needed to judge output quality.

In AOA, the capability card is the boundary surface. It says what the AU
accepts, what it returns, what constraints apply, and which signals show
whether it behaved acceptably.

## 2. Compose: composition lives at the contract

Composition should happen through explicit contracts rather than hidden code
coupling or shared prompt conventions. A planner can assemble work dynamically
only when each candidate capability has a machine-readable contract.

The practical lesson from SOA is that composability must be designed in. The
practical lesson from microservices is that smart endpoints need explicit,
consumer-friendly contracts. AOA carries both lessons forward into capability
cards, Agent Cards, and tool schemas.

## 3. Substitute: replacement is registration, not a rewrite

An AU should be replaceable by registering a better candidate, not by rewriting
the caller. Replacement needs more than a new endpoint. It needs compatibility,
versioning, evaluation, rollout, rollback, and deprecation.

This is why the registry is a control-plane primitive. If replacement is a
registry operation, the architecture can evolve without hard-coded workflow
rewrites.

## 4. Trust: observed, not asserted

Self-reported metadata is useful for bootstrapping, but it should not be the
final source of truth. A probabilistic AU can satisfy a schema and still return
a weak answer. Trust therefore needs traces, evaluation, runtime metrics, and
quality signals.

Observed-over-claimed is the principle that makes AOA different from a static
catalogue. The registry should eventually learn from latency, reliability,
cost, policy failures, groundedness, and human or evaluator feedback.

## Summary table

| Principle | Historical ancestor | AOA expression |
| --- | --- | --- |
| Decompose | information hiding, bounded contexts, service abstraction | bounded AU with explicit capability contract |
| Compose | SOA composability, smart endpoints | runtime planning over discoverable contracts |
| Substitute | independent deployment, circuit breakers, service replacement | new AU version enters through registration and evaluation |
| Trust | observability, SRE, design for failure | observed quality feeds future selection |

## Open question

The hard part is not naming the principles. The hard part is making them
operational in a small enough demo that participants can build and inspect in
one course.
