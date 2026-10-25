# Revised course delivery

## Before the class

- Start on the reviewed revision of `codex/october-course-rebuild` in `aoa-course`, on Spark or the teaching laptop. Use the [launcher table](pre-work/01-revised-model-access.md#start-and-stop) for macOS/Linux and Windows commands.
- Use the [architecture diagrams](ARCHITECTURE.md) to locate each component before running its example. Read the [EVE/AGNTCY adoption explanation](sessions/session-03-eve/ADOPTION.md) before Session 3; the practical integration is a main course argument, not an optional product overview.
- Use the [provider setup](pre-work/01-revised-model-access.md). Verify actual Cerebras and TypeSafe calls, account quota and access from the teaching environment. Keep the local route ready and label it when used.
- Build all images before the session. EVE retains its pinned native workspace and framework version; do not replace learner files to make a demo pass.
- Run `.venv-course/bin/python -m pytest -q tests` after installing `tests/requirements.txt` into that isolated environment. These are adapter/policy/storage checks, not model-quality certification.
- Start the local AGNTCY Directory, verify publish/pull/search and check its record against the local card.
- Preserve the original material. Do not clear existing wiki, traces, workshop files or cards to manufacture a clean run. Use labelled synthetic inputs and explain persisted history.

## Delivery sequence

Introduce each existing story before its new mechanism. Let learners predict the result before exposing the decision table or saved trace.

1. CV: one complete run, inspect the plan, switch assessment speciality, compare the output with the same generation model.
2. Wiki: relevant note, irrelevant note, uncertain note. Separate extraction fidelity, semantic judgement and publication.
3. EVE: native authoring and acceptance first, local Directory discovery and AOA adoption next. Inspect the added boundary rather than presenting an external record as permission.
4. Compliance: red card, declared review, exact held result, restart, review, duplicate request, audit.

The existing slide placeholders can still lead into these live examples. The repository's hands-on session numbers are not a proposal to renumber the deck.

## Session 3 evidence to show

Show the same learner agent working in native EVE, then the registered AOA contract, then a CV/interview run calling it across the bridge. Explain the course-owned adapter and inspect the actual `eve/client` session call if asked how real the integration is. Generic bridge signals check field presence; inspect five-question quality and limits explicitly.

Publish and retrieve an OASF record through the real local Directory. Compare its content ID, contract digest and local Agent ID; they identify different things. Show the comparison returning `execution_authorised: false` even when the declaration matches. Finish with the executed local composition so discovery is connected to useful work.

Keep the scope explicit: real third-party framework and discovery infrastructure, learner-owned agent, course-owned adapter, local seeded approval. An externally owned agent would still need identity, permission, contract, quality and operational acceptance. The [adoption guide](sessions/session-03-eve/ADOPTION.md#adopting-an-externally-owned-agent) supplies that discussion without claiming it has already been implemented.

## Record the comparison

For each run capture: input fixture, model/version, candidate/card hashes, instructions hash, expected outcome, actual outcome, abstention, total latency, decision latency, usage, provider charge estimate and reviewer effort. Include failures. The TypeSafe price in the trace is a dated estimate; local cost is unestimated, not zero.

For stable-model utility, judge each output against explicit task criteria before considering a model change. A specialist model can reduce the amount of generation required by a product; it does not remove the surrounding contract, knowledge, policy and state responsibilities.

## Remote use

Spark remains available for remote builds and execution; a local laptop checkout can run the same course independently. From an authorised computer, forward port 8080 to view Spark's Studio; no public exposure is required. Docker services and a Directory process in a persistent terminal can outlive the Mac connection. Use the reviewed branch and commit when continuing from another client. Private provider keys and persisted runtime data do not travel with Git. Final presentation rendering can remain on the Mac.

## Scope still open for a later course iteration

Full AGNTCY federation/identity/messaging, production durable-object deployment, semantic calibration over a labelled dataset, automatic decision training, and the separate expense course-v2 are not represented as completed lessons here. The current course teaches the working boundaries within the four retained examples.
