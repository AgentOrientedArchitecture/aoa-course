# Capstone exercise — put a vendor-authored agent behind an AOA contract

The course already contains an EVE-authored interviewer running as an Agentic
Unit. This lab works from the other direction: start a second EVE agent through
its native runtime, identify what the vendor framework does and does not own,
then expose the same agent through the AOA composition boundary.

The point is complementarity:

- **EVE owns the interior** — model wiring, instructions, tools, sessions and
  runtime behaviour.
- **AOA owns the composition surface** — contract, governed identity,
  discovery, lifecycle, trace and the outward agent protocol.
- **The behaviour files do not change when the boundary changes.** A different
  agent framework could replace EVE behind the same public contract.

All Node, EVE and package dependencies live in the lab image. Participants need
Docker and the course `.env`; host Node/npm and venue network access are not
required.

## The agent

The authored agent lives in `system/agents-eve/red-flags/`:

```text
red-flags/
  agent.ts                model/provider wiring — EVE
  instructions.md         behaviour — EVE
  capability-card.yaml    public promise — AOA
  boot.mjs                small mapping into the generic AOA adapter
```

It reviews a CV-fit evaluation and returns risks a human interviewer should
probe. It never makes or recommends a hiring decision.

## Checkpoint 1 — run the vendor-native agent

Start the Session 3 system and the red-flags agent in native EVE mode:

```bash
./scripts/session3-lab-native.sh
```

The script builds one pinned dependency image at home and reuses it for both
halves of the lab. EVE's native API is available on `localhost:7310`.

Create a native EVE session:

```bash
curl -i -X POST http://127.0.0.1:7310/eve/v1/session \
  -H 'content-type: application/json' \
  -d '{"message":"Evaluation: {\"scores\":{\"seniority_match\":2},\"verdict\":\"fit\",\"gaps\":[\"No production ownership\"]}"}'
```

The response's `x-eve-session-id` identifies the durable EVE session. The agent
works: EVE has supplied a useful authoring model and runtime.

Now open `http://localhost:8080` and inspect the Registry pane, or run:

```bash
curl -s 'http://localhost:7100/find?id=red-flags-review'
```

The capability is absent. The AOA planner cannot discover or select a runtime
that has not published a contract.

## Checkpoint 2 — name the boundary gap

Map the native agent against the course's public surfaces:

| Surface | Native EVE agent |
|---|---|
| Behaviour and model wiring | present in `instructions.md` and `agent.ts` |
| Runtime and session API | present at `/eve/v1/session` |
| Capability contract | not published |
| Governed identity and lifecycle | not published |
| Registry discovery | absent |
| AOA trace boundary | absent |
| Outward A2A face | absent |

These are not EVE defects. They are responsibilities at a different altitude:
EVE is an agent framework; AOA governs composition across agents, teams and
runtimes.

Before wrapping the agent, open
`system/agents-eve/red-flags/capability-card.yaml` and add one constraint that
would matter in your employment context. Examples:

- every high-severity flag requires a cited gap from the input evaluation;
- protected characteristics must never be inferred or emitted;
- the output is advisory and cannot trigger a hiring decision;
- personal data must not be retained beyond the invocation trace policy.

This is the participant-authored decision in the lab: the framework supplies
capability; you decide the public promise and operating constraint.

## Checkpoint 3 — expose the same agent as an Agentic Unit

Switch the same image and behaviour files to the wrapped service:

```bash
./scripts/session3-lab-wrap.sh
```

The script stops the native-only service and starts the generic `aoa-eve`
adapter. It does not reinstall dependencies or rewrite `agent.ts` or
`instructions.md`.

Watch the capability appear:

```bash
curl -s 'http://localhost:7100/find?id=red-flags-review'
curl -s 'http://localhost:7311/.well-known/agent-card.json'
```

The same EVE agent now has:

- the `red-flags-review` public contract;
- stable Agent ID `urn:aoa:agent:eve-red-flags`;
- registry lifecycle and provenance;
- an outward A2A endpoint;
- `skills_hash` visibility for behaviour changes;
- trace events at the AU boundary.

Edit `instructions.md` and watch `skills_hash` change while the Agent ID and
capability ID remain stable. That is a behaviour revision behind a stable
contract, not a new integration.

## Debrief

| EVE gives the agent | AOA adds around it |
|---|---|
| `instructions.md`, `agent.ts`, tools | `capability-card.yaml` |
| durable native runtime | registry registration and lifecycle |
| vendor session API | portable outward agent boundary |
| framework-local evaluation | estate trace and governance hooks |

The conclusion is not that every EVE agent needs AOA. The boundary earns its
keep when another team or runtime must discover, trust, compose, observe,
replace or retire the capability. EVE can later be replaced by another
framework without changing what consumers compose against.

## Fallback

If participant machines cannot run the lab, the instructor runs the same three
checkpoints on screen. Pairs still inspect the four files, supply the contract
constraint, and call out which public surface appears at each step.
