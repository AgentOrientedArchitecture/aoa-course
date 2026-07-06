---
title: Context-aware AOA principles workshop
source_type: curated-action-kit
---

# Context-Aware AOA Principles Workshop

AOA is a set of architectural principles, not a product with one universal
configuration. Each organisation needs to localise the principles against its
own risk appetite, data landscape, operating model, regulatory obligations,
vendor posture, and culture.

Run the principles workshop after the initial inventory, but before the
roadmap is finalised. Principles written before the inventory tend to become
slogans. Principles written after the inventory can respond to real risks,
duplication, integration debt, and adoption bottlenecks.

## Workshop inputs

Bring:

- the AI and agent inventory
- the candidate AU list
- known regulatory or policy constraints
- examples of high-value workflows
- examples of unacceptable agent behaviour
- existing platform and integration standards
- security, data, risk, product, architecture, and operations voices

## Seven workshop steps

### 1. Identify non-negotiables

Question: what must never be delegated, exposed, automated, inferred, or
executed without approval?

Output:

- prohibited actions
- prohibited data use
- required escalation paths
- hard policy boundaries

### 2. Define bounded autonomy

Question: where can agents recommend, draft, act with approval, or act within
a bounded scope?

Output:

- autonomy levels by domain
- autonomy levels by risk tier
- actions that always require human approval
- conditions for increasing or reducing autonomy

### 3. Set evidence standards

Question: what proof is required before a capability moves from experiment to
pilot or production?

Output:

- evaluation requirements
- red-team or safety checks
- acceptance criteria
- incident review requirements
- minimum observability

### 4. Set interoperability rules

Question: where should MCP, A2A, APIs, events, or workflow engines be used?

Output:

- tool and data access rules
- agent-to-agent delegation rules
- workflow engine boundaries
- identity and permission expectations
- exceptions process

### 5. Define registry criteria

Question: what metadata makes a capability discoverable and safe to reuse?

Output:

- required capability card fields
- lifecycle states
- ownership fields
- risk tier fields
- evaluation and observability fields
- retirement process

### 6. Define fitness criteria

Question: which non-functional requirements affect selection?

Output:

- quality thresholds
- latency expectations
- cost limits
- reliability targets
- security and privacy requirements
- auditability requirements
- domain-specific scoring rules

### 7. Define review cadence

Question: how will principles stay current?

Output:

- review forum
- decision rights
- reassessment frequency
- incident review path
- reporting metrics
- change process

## Principles map template

| Generic AOA principle | Local interpretation | Non-negotiable rule | Evidence required | Owner |
| --- | --- | --- | --- | --- |
| The AU is the architectural unit |  |  |  |  |
| Frameworks are implementation details |  |  |  |  |
| Discovery precedes orchestration |  |  |  |  |
| Semantics beat keyword search |  |  |  |  |
| NFRs are selection criteria |  |  |  |  |
| Standards reduce friction |  |  |  |  |
| Human oversight is designed, not improvised |  |  |  |  |
| Auditability is a product feature |  |  |  |  |

## Example localised principles

| Generic principle | Example local rule |
| --- | --- |
| The AU is the architectural unit | A production AU must have a named business owner, technical owner, lifecycle state, capability card, evaluation evidence, and risk tier before it can be registered for reuse. |
| Discovery precedes orchestration | No orchestrator may call an AU unless its lifecycle state, access scope, NFR profile, human oversight policy, and retirement process are known. |
| Standards reduce friction | MCP is preferred for tool and data access, A2A is preferred for agent-to-agent task delegation, but high-risk flows require additional local approval and audit controls. |
| Human oversight is designed, not improvised | Agents may draft recommendations, but customer-impacting or employee-impacting decisions require accountable human approval until the domain reaches agreed maturity. |
| Auditability is a product feature | Every production AU must emit enough trace data to reconstruct task intent, context used, tools called, outputs produced, and approvals received. |

## Useful workshop questions

- Which decisions would we be embarrassed to discover an agent made alone?
- Which data should an agent never see, even if access would improve quality?
- Which workflows need redesign rather than faster local task completion?
- Which capabilities are being rebuilt by multiple teams?
- Which agentic systems already exist without clear ownership?
- Which standards reduce integration friction in our context?
- Which parts of our current governance process would push teams into shadow adoption?
- What evidence would make us comfortable increasing autonomy?

