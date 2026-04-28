---
title: Real-world implementations and market anchors
source_type: curated-raw-note
curated_from:
  - aoa-knowledge/raw/research/2026-04-18-vendor-reference-architectures.md
  - aoa-knowledge/raw/research/2026-04-18-enterprise-reference-architectures-synthesis.md
  - aoa-knowledge/raw/research/2026-04-18-registry-landscape-synthesis.md
  - aoa-knowledge/raw/research/2026-04-18-aws-agentcore-registry.md
  - aoa-knowledge/raw/research/2026-04-18-salesforce-servicenow-registries.md
---

# Real-World Implementations and Market Anchors

AOA should be anchored in what vendors and platforms are already building. The
market has not converged on AOA vocabulary, but it has converged on many of
the same architectural concerns: agent runtimes, registries, tool gateways,
identity, observability, evaluation, policy, and knowledge grounding.

## AWS Bedrock AgentCore

AgentCore is a strong real-world anchor because it bundles many production
concerns explicitly: Runtime, Memory, Gateway, Identity, Code Interpreter,
Browser, Observability, Evaluations, Policy, and Registry.

The registry and gateway support MCP and A2A-facing patterns. AgentCore also
has observability and evaluation features, but the raw research noted an
important gap: metrics are documented as observability outputs, not as an
automatic feedback loop into registry selection.

AOA teaching angle: AgentCore validates the component set, while AOA sharpens
the selection argument around observed behaviour.

## Microsoft Entra, Foundry, M365, and API Center

Microsoft splits the registry job across several products:

- Entra Agent Registry for identity and governance
- Foundry Agent Catalog and Agent Service for development/runtime
- M365 Copilot Agent Store for user-facing agent discovery
- Azure API Center for MCP/tool registry patterns

AOA teaching angle: enterprise agent architecture may not have one registry.
It may have several catalogues and control planes, which makes clear contracts
and traceable selection even more important.

## Salesforce and MuleSoft Agent Fabric

MuleSoft Agent Fabric is one of the closest commercial cousins to AOA because
it combines agents, MCP servers, LLMs, gateway policy, and brokered routing.
The raw research highlights policy controls such as JWT validation, schema
validation, PII detection, attribute-based access control, prompt decoration,
audit logging, and rate limiting.

AOA teaching angle: MuleSoft shows the integration-fabric version of agent
architecture. AOA can contrast deterministic fitness plus planner reasoning
with LLM routing inside the broker.

## ServiceNow AI Control Tower

ServiceNow is a governance-heavy implementation. It tracks agents, tools,
models, skills, prompts, datasets, and use cases through platform records and
roles. It is strong on inventory, stewardship, access control, evaluation, and
enterprise governance.

AOA teaching angle: governance platforms may do catalogue and approval better
than a small open reference implementation. AOA's distinctive contribution is
the architectural shape and the observed-quality selection loop.

## Google, IBM, SAP, Snowflake, Databricks, and others

Other vendors show recurring architectural pieces:

- Google reference architectures use coordinators, subagents, ADK, Cloud Run,
  GKE, Vertex AI Agent Engine, Model Armor, and MCP tooling.
- IBM patterns emphasise watsonx, agent catalogues, governance, and enterprise
  integration.
- SAP Joule uses role-aware agents grounded in business data and the SAP
  knowledge graph.
- Snowflake Cortex Agents combine planning, task decomposition, Cortex Search,
  Cortex Analyst, semantic views, and custom tools.
- Databricks combines orchestration, MLflow tracing/evaluation, Unity Catalog
  governance, vector search, serving, and workflow infrastructure.

## Course takeaway

AOA is not trying to claim that nobody else has agent architecture. The useful
claim is narrower: AOA offers a clean teaching and reference shape for composing
Agentic Units through contracts, discovery, planning, orchestration, tools,
traces, and observed quality.
