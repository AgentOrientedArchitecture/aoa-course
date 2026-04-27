---
marp: true
title: "Session 3 - AOA in the Real World"
theme: default
paginate: true
size: 16:9
footer: Agent-Oriented Architecture - O'Reilly Live Course
---

# Session 3 - AOA in the Real World


---

# The question after Session 2

You have now seen a small AOA system working.

The real question is:

## Where does this sit in the world?

- Is this new or old?
- Is this architecture or just another framework?
- Are vendors already doing it?
- What should I look for in real platforms?

---

# The short answer

AOA is not a rupture.

It is distributed-systems architecture catching up to a new unit of composition:

## the model-backed, tool-using, probabilistic capability


---

# Architecture déjà vu

Every time software crosses a boundary, the same questions come back:

- What is the unit?
- How does it describe what it can do?
- Where is that description published?
- Who decides which unit to call?
- How do we know whether it worked?
- How do we replace it later?

---

# Every generation rebuilds three things

| Thing | Role |
|---|---|
| Contract | What the unit promises |
| Registry | Where promises can be discovered |
| Orchestrator | What composes units into work |


---

# The lineage

| Era | Unit | Contract | Registry / discovery |
|---|---|---|---|
| CORBA/DCOM | Distributed object | IDL | Trading service |
| SOA | SOAP service | WSDL | UDDI |
| REST/microservices | Service/API | OpenAPI/gRPC | DNS, Consul, K8s |
| Event-driven | Producer/consumer | Avro/Protobuf | Schema registry |
| AOA | Agentic Unit | Capability card | Agent registry |


---

# SOA got the principles right

The durable ideas:

- Standardised contracts
- Loose coupling
- Abstraction
- Autonomy
- Discoverability
- Composability

The mistake was not the principles.

The mistake was the ceremony.


---

# UDDI is the warning

UDDI failed in ways a naïve agent registry could repeat:

- Too much publication friction
- Static records
- No liveness
- No observed-quality layer
- Discovery pattern people did not actually need


---

# AOA's registry must be different

A useful agent registry needs:

- Low-friction publication
- Live capability records
- Intent-based discovery
- Governance before trust
- Runtime observations
- Selection based on behaviour, not only claims


---

# Microservices kept the discipline

The useful inheritance:

- Small autonomous services
- Business-capability boundaries
- Smart endpoints, dumb pipes
- Independent deployability
- Design for failure
- Observability


---

# The agentic failure mode

Microservices had the distributed monolith.

Agent systems have the orchestration monolith:

- Giant graph
- Giant prompt
- Framework-specific wiring everywhere
- Every change touches the centre
- No clean replacement boundary

---

# What is genuinely new

The unit is different.

An Agentic Unit is:

- Probabilistic
- Model-backed
- Tool-using
- Potentially autonomous
- Observable over time
- Replaceable by contract

The contract must carry behaviour, not just types.


---

# The AOA addition

AOA adds three things to the old pattern:

- Probabilistic contracts
- Runtime evaluation signals
- Observed-quality selection

The registry is no longer just a catalogue.

It becomes part of the control loop.


---

# The real world is already showing the shape

Successful agent deployments increasingly show:

- Bounded agents
- Explicit tool boundaries
- Traces and telemetry
- Plugin or capability catalogues
- Human escalation paths
- Governance surfaces


---

# Production pressure signals

Examples to discuss:

- Coding agents ending in pull requests
- Customer-service agents with escalation
- Legal and research workflows with supervised review
- Continuous audit and security triage
- Financial operations using plugin/domain-agent structures


---

# The honest state

The world has not fully adopted AOA.

Most production systems still use:

- Static tool schemas
- Hard-coded plugin lists
- Framework-as-architecture
- Vendor-specific control planes

That is exactly why the architectural lens matters.


---

# Vendor platforms are convergence, not competition

AWS, Azure, Salesforce/MuleSoft, ServiceNow, IBM, Google, LangSmith, and OpenAI all expose parts of the same shape:

- Agent catalogues
- Registries
- Tool registries
- Brokers
- Gateways
- Governance and monitoring surfaces


---

# AOA is a lens, not a product

Do not ask:

## Is AOA better than AgentCore or Foundry?

Ask:

## Which AOA principles does this platform satisfy, and where are the gaps?


---

# How to evaluate a platform

Ask:

- What is the unit of capability?
- What is the contract?
- Is there a registry or only a catalogue?
- Does selection use observed behaviour?
- Where is governance enforced?
- Can I replace one implementation without rewriting consumers?


---

# Frameworks fall into place

LangGraph, CrewAI, AutoGen, Gas Town, and similar tools can be excellent.

They belong:

## inside an AU

The architecture-level question is what sits between independently owned, independently replaceable units.


---

# Personal agents fall into place

A personal agent is:

## one AU with a human on the other end

A fleet of personal agents inside an organisation becomes an AOA governance problem.


---

# Sovereignty becomes a consequence

If replacement is a registry operation, then these become architectural choices:

- Hosted model or local model
- Closed model or open weight
- Smaller model or frontier model
- Vendor agent or owned AU
- Cloud region or controlled infrastructure

The architecture preserves option value.


---

# Activity - architecture mapping

Take a real-world agent platform or deployment description.

Annotate:

- Unit
- Contract
- Registry/catalogue
- Orchestrator
- Observation signals
- Replacement boundary
- Governance point

---

# Debrief prompts

- Where was the contract explicit?
- Where was it only implied?
- Was the registry a catalogue or a control loop?
- What could be replaced without rewriting callers?
- What was locked inside a framework or vendor boundary?

---

# The arc in one slide

SOA taught contracts and discoverability.

Microservices taught bounded ownership and independent replacement.

Agent platforms show the pressure now.

AOA pulls the surviving ideas together for probabilistic, model-backed units.

---

# Bridge to Session 4

Now we build the cut-down knowledge-management system.

Not as a toy app.

As a small teaching artefact that makes the old triad visible:

- Contract
- Registry
- Orchestration
- Observation
