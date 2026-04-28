---
title: Registries and observed quality
source_type: curated-raw-note
curated_from:
  - aoa-knowledge/raw/research/2026-04-18-registry-landscape-synthesis.md
  - aoa-knowledge/raw/research/2026-04-18-aws-agentcore-registry.md
  - aoa-knowledge/raw/research/2026-04-18-salesforce-servicenow-registries.md
  - aoa-knowledge/raw/research/2026-04-18-azure-microsoft-registries.md
  - aoa-knowledge/raw/research/2026-04-18-other-registries-landscape.md
---

# Registries and Observed Quality

In AOA, a registry is not just a list of agents. It is part of the selection
control loop. A useful registry helps a planner answer five questions:

1. Which capabilities exist?
2. What does each capability claim to do?
3. Is it alive and invokable now?
4. Which candidate is best for this intent?
5. Is the caller allowed to use it, and can the use be audited?

## Registry shapes in the market

| Shape | Primary question | Examples |
| --- | --- | --- |
| Identity and governance registry | Who is this agent, and may it be invoked? | Microsoft Entra Agent Registry, ServiceNow AI Control Tower, AWS AgentCore Registry |
| Marketplace or catalogue | What agents can users browse, install, or buy? | M365 Copilot Agent Store, Salesforce AgentExchange, GPT Store, Hugging Face agents |
| Integration fabric or broker | How do agents and tools connect across systems? | MuleSoft Agent Fabric, AWS AgentCore Gateway, Azure API Center for MCP |
| Live-performance evaluator | Which candidate should the planner pick now? | AOA's distinctive design direction |

Most commercial products have strong catalogue, governance, and platform
features. The recurring gap is that runtime observation usually does not feed
directly into future selection.

## Observed-over-claimed

An Agent Card or capability card is a claim. It says what a capability is
intended to do. The runtime trace is evidence. It shows what happened when the
capability was actually used.

AOA's registry story should privilege evidence over assertion:

- latency beats declared latency targets
- success rate beats marketing claims
- groundedness beats "can answer questions"
- policy denial beats "safe tool use"
- evaluation score beats a broad capability description

The registry should start with self-reported metadata because nothing else is
available before first use. Over time, observed behaviour should replace or
discount the claim.

## Why this matters for agents

Agentic Units are probabilistic. A service can either be up or down; an agent
can be up, syntactically valid, plausible, and wrong. That means AOA needs a
selection model that can consider quality as well as availability.

The course version can show the idea simply:

- a capability card advertises inputs, outputs, constraints, and signals
- the planner selects a capability through the registry
- each invocation emits a trace
- the trace contains latency, errors, output shape, and evaluation signals
- the registry can later use these signals to rank candidates

## Teaching point

The registry is not the intelligence. The planner still reasons about the
intent. The registry provides bounded, inspectable evidence about available
capabilities. That split keeps selection more reproducible and avoids putting
an LLM into every routing decision.
