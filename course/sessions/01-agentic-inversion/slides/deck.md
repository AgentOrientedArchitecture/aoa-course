---
marp: true
title: "Session 1 - The Agentic Inversion"
theme: default
paginate: true
size: 16:9
footer: Agent-Oriented Architecture - O'Reilly Live Course
---

# Session 1 - The Agentic Inversion


---

# The shape of most AI systems today

- Human workflow
- AI called at selected moments
- Human carries the process in their head
- AI improves steps, not the shape of the work

Speaker note: this is the "faster horse" frame. Useful, valuable, but not the architectural shift.

---

# The inversion

- From: human workflows augmented by AI
- To: AI workflows augmented by humans
- Humans move from continuous drivers to judgement, approval, escalation, and exception handling
- The workflow itself becomes a system responsibility


---

# The diagnostic question

## Who holds the composition logic?

- If the human decides every next step, it is a copilot pattern
- If the system decomposes, selects, invokes, and observes, it is moving into the inversion
- Vendor labels do not answer this question


---

# The autonomy spectrum

| Pattern | Driver | Human role |
|---|---|---|
| Pure copilot | Human | Accept/reject suggestions |
| Autonomous with approval | AI | Review completed work |
| Batch or scheduled | AI | Investigate exceptions |
| Fully autonomous | AI | Upstream policy, downstream audit |


---

# Where the inversion is already visible

- Coding agents that end in pull requests
- Customer-service agents with human escalation
- Legal and research workflows with supervised review
- Continuous audit and security triage
- Financial operations with domain-agent/plugin registries


---

# The honest state of production

- Most enterprise AI is still assistant-shaped
- Genuine inversion exists, but is unevenly distributed
- Many "agentic" projects remain proof-of-concept or marketing-led
- The architecture matters because failure modes are already visible


---

# Failure modes are architectural

- Monolithic prompts that own too much
- No authoritative grounding
- No escalation path
- No observation surface
- No replaceable boundary
- Vendor/platform dependency as a hidden risk


---

# What changes architecturally?

- Composition moves out of the human and into the system
- Capabilities need explicit contracts
- Selection becomes runtime behaviour
- Observation becomes part of the control loop
- Replacement becomes a normal operation


---

# Welcome to Agent-Oriented Architecture

AOA is the architecture for systems made from discoverable, composable, observable, replaceable agentic capabilities.

- Agentic Unit
- Capability card / agent card
- Registry
- Planner
- Orchestrator
- Evaluation signals

---

# Agentic Unit

- Independently deployable capability
- Explicit contract
- Own lifecycle
- Observable
- Replaceable
- Small enough to govern


---

# Capability card

- The public description of what the unit can do
- Inputs and outputs
- Constraints
- Evaluation signals
- Ownership and provenance
- Runtime endpoint or discovery metadata


---

# Registry

- Where capabilities publish themselves
- Where planners and orchestrators discover candidates
- Where observation can change future selection
- A registry is not just a phone book


---

# Planner and orchestrator

- Planner turns intent into a sequence of capability needs
- Orchestrator invokes selected units
- Registry mediates discovery and selection
- Evaluation signals feed back into future choices

Course note: define whether we keep planner/orchestrator separate in the v0.1 course repo or present them as conceptual roles.

---

# Demo - registration, not rewrite

Show a small workflow:

1. Monolithic version
2. Change request causes rewrite pressure
3. Same workflow decomposed into AUs
4. Replacement happens through registration

Land: "The change was a registration, not a rewrite."

---

# Activity - spot the AUs

Participants choose a workflow from their own organisation.

- Identify candidate capabilities
- Mark likely inputs and outputs
- Mark ownership
- Mark human judgement points
- Separate orchestration concerns from AU responsibilities

---

# Debrief prompts

- Where did people draw different boundaries?
- Which candidate AU is actually two capabilities?
- Which concern belongs in the orchestrator?
- Where must a human remain in the loop?

---

# Bridge to Session 2

You have seen the shape.

Next: open one unit and inspect the anatomy.
