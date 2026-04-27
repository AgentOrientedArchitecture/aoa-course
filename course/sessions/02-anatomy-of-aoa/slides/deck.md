---
marp: true
title: "Session 2 - The Anatomy of AOA"
theme: default
paginate: true
size: 16:9
footer: Agent-Oriented Architecture - O'Reilly Live Course
---

# Session 2 - The Anatomy of AOA


Repo anchor: `aoa-course/system/`

---

# What we are opening up

Session 1 named the system shape.

Session 2 opens one working system:

- Model
- Capability
- Skills
- Tools
- Loop
- Registry
- Trace

---

# The v0.1 course system

Workflow:

```text
parser-cv -> evaluator-cv -> reporter-cv-fit
```

Visible pieces:

- Registry
- Planner
- Studio
- Filesystem MCP tool
- Three agents
- Capability cards and skills files

---

# Agentic Unit anatomy

Every AU has four addressable parts:

- Capability card - the contract
- `skills.md` - practical know-how
- `tools.yaml` - dependencies it may call
- `agent.py` - wiring between model, skills, tools, and HTTP boundary


---

# Capability card as contract

The card tells the rest of the system:

- Stable identity
- Purpose
- Inputs
- Outputs
- Constraints
- Evaluation signals
- Provenance
- Endpoint


---

# Skills give the capability its identity

Same model.

Same code.

Different `skills.md`.

Different capability.

Course demo: edit a skill and watch the registry show the changed skills hash.


---

# Tools are not capabilities

- A tool is something a unit reaches for
- A capability is something a unit promises
- MCP is a good tool boundary
- A2A is the peer-agent boundary


---

# The filesystem tool

In the course repo:

- Registered capability: `tool-filesystem`
- Kind: `tool`
- Exposes file read/list operations
- Called by parser and evaluator
- Shows that registries can hold tools and AUs

---

# The parser

Capability: `parser-cv`

- Reads a CV path through the filesystem tool
- Parses plain text into structured CV data
- Does not evaluate
- Emits schema and simple validity signals


---

# The evaluator

Capability: `evaluator-cv`

- Receives parsed CV
- Reads job description
- Scores fit against rubric
- Returns verdict, strengths, gaps, rationale
- Emits validity and verdict signals


---

# The reporter

Capability: `reporter-cv-fit`

- Consumes structured upstream outputs
- Produces a human-readable report
- Has no tool dependencies
- Shows that not every AU needs tools

---

# The planner

In v0.1 this is deliberately small:

- Receives intent
- Selects known workflow
- Looks up each capability in the registry
- Invokes each endpoint
- Records trace events

Course note: useful precisely because it is readable.

---

# The registry

The registry:

- Stores cards by capability id
- Receives registrations on boot
- Streams updates to the studio
- Lets the planner look up capabilities
- Makes hot-reload visible


---

# The studio

The studio gives participants:

- Registry pane
- Trace pane
- Capability card pane
- CV and job description input
- A visible path from intent to output

Course note: this is the main Session 2 teaching surface.

---

# Evaluation signals

Signals should be:

- Declared on the card
- Emitted at runtime
- Machine-checkable where possible
- Useful for humans when not fully automated

Examples:

- Valid output shape
- Has required fields
- Latency
- Verdict consistency


---

# Hands-on - inspect and change

Participant path:

1. Run the system
2. Submit one CV/JD pair
3. Inspect the trace
4. Open one capability card
5. Edit one `skills.md`
6. Observe the registry update
7. Re-run and compare output

---

# Discussion - what should not be inside an AU?

- Cross-workflow orchestration
- Hidden policy decisions
- Unbounded tool access
- Multiple unrelated responsibilities
- Business ownership ambiguity

Follow-up wiki gap: `what-belongs-inside-an-au`.

---

# Bridge to Session 3

You have now seen a working AOA system from the inside.

Next: where this sits relative to frameworks, vendor platforms, sovereignty, and the real agent landscape.
