---
marp: true
title: "Session 4 - Let's Build"
theme: default
paginate: true
size: 16:9
footer: Agent-Oriented Architecture - O'Reilly Live Course
---

# Session 4 - Let's Build


Repo anchor: `aoa-course`

---

# What this session is for

- Consolidate the day
- Build or inspect a working AOA system
- Show replacement and evolution
- Leave with a runnable repo
- Turn theory into a Monday-morning starting point

---

# The teaching artefact

The repo is not a product.

It is:

- Small
- Readable
- Runnable
- Complete enough to teach the architecture
- Honest about what it omits


---

# Complete but minimal

The goal is not enterprise completeness.

The goal is:

- Every major concept has a concrete file
- Every file has a reason to exist
- Participants can read the whole thing
- The important change is visible


---

# What the v0.1 repo demonstrates

- A registry with live capability cards
- A planner that looks up capabilities
- Three AUs in a chain
- One MCP-style filesystem tool
- A browser studio
- Trace visibility
- Skill hot reload
- Smaller local or hosted model configuration

---

# The Session 2 chain

```text
parser-cv -> evaluator-cv -> reporter-cv-fit
```

The important point:

The system is not "a CV app".

It is a small AOA system whose first workflow is CV fit.

---

# The Session 4 move

Same architecture.

New capabilities.

The build reuses the Session 2 three-agent pattern:

- Parser becomes note parser
- Evaluator becomes passage relevance evaluator
- Reporter becomes answer/report writer
- The registry and planner shape stay recognisable
- The domain changes from CV fit to cut-down knowledge management

---

# Publish, discover, select, replace

The verbs:

- Publish a capability
- Discover it through the registry
- Select it for an intent
- Replace it without rewriting callers


---

# Evaluation closes the loop

Without signals:

- The registry is just a catalogue

With signals:

- Capabilities can be compared
- Bad replacements can be detected
- Selection can improve over time
- Governance has evidence


---

# Demo path A - baseline

Use the current repo.

1. Start the system
2. Submit CV/JD
3. Inspect registry
4. Inspect trace
5. Edit `skills.md`
6. Watch `skills_hash` change
7. Re-run and compare

This remains the fallback if the knowledge-management path is not stable.

---

# Demo path B - target for v0.1

Build the cut-down knowledge-management capabilities:

```text
parser-notes -> evaluator-query -> reporter-answer
```

This is the course target: same architecture, same three agents, new capability set.

---

# Smaller models, local or hosted

Same cards.

Same registry.

Same planner.

Different reasoning backend:

- Ollama with `gpt-oss:120b` or a Qwen-family model
- OpenAI-compatible hosted endpoint for smaller models
- Frontier API only as an optional fallback

The architecture should not care where reasoning happens.

---

# Participant modes

Both are first-class:

- Follow along locally
- Watch and inspect later

The course must work even if a participant's Docker setup fails.

Required fallback: recorded demo or hosted instance.

---

# What participants take away

- Vocabulary for AOA
- A mental model for boundaries
- A capability-card pattern
- A small runnable reference system
- A method for evaluating platforms and frameworks
- A Monday-morning decomposition exercise

---

# Monday morning actions

1. Pick one workflow still orchestrated by a human
2. Identify three candidate AUs
3. Write one capability card
4. Decide what signal would prove the AU works
5. Decide where a human must approve or escalate

---

# Close

AOA is not a tool choice.

It is a way to make agentic systems governable, observable, replaceable, and evolvable.
