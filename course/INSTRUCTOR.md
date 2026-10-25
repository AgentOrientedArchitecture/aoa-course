# Instructor runbook

## Before the class

- Use `main` in `aoa-course`, on Spark or the teaching laptop, and record the commit used for rehearsal. Follow the [checkout instructions](pre-work/SETUP.md#existing-checkouts) when updating an existing installation, then use the [launcher table](pre-work/SETUP.md#start-and-stop) for macOS/Linux and Windows commands.
- Use the [architecture diagrams](ARCHITECTURE.md) to locate each component before running its example. Read the [EVE/AGNTCY adoption explanation](sessions/session-03-eve/ADOPTION.md) before Session 3; the practical integration is a main course argument, not an optional product overview.
- Use the [provider setup](pre-work/SETUP.md), with `LLM_API_KEY` for generation and `DECISION_API_KEY` for decisions. Verify actual calls, account quota and access for the selected endpoints from the teaching environment. Cerebras and TypeSafe remain the default examples; a different compatible provider needs its own acceptance check. Keep the local route ready and label it when used.
- Build all images before the session. EVE retains its pinned native workspace and framework version; do not replace learner files to make a demo pass.
- Run `.venv-course/bin/python -m pytest -q tests` after installing `tests/requirements.txt` into that isolated environment. These are adapter/policy/storage checks, not model-quality certification.
- After Session 3 adoption, check automatic AU publication, AGNTCY catalogue cards and the Directory content IDs in the executed plan. Session 4 continues through AGNTCY.
- Preserve the original material. Do not clear existing wiki, traces, workshop files or cards to manufacture a clean run. Use labelled synthetic inputs and explain persisted history.

## Delivery sequence

Follow the four [session walkthroughs](sessions/README.md). Introduce each business task before its mechanism. Let learners predict the result before exposing the decision table or saved trace.

1. CV: one complete run, inspect the plan, switch assessment speciality, compare the output with the same generation model.
2. Wiki: relevant note, irrelevant note, uncertain note. Separate extraction fidelity, semantic judgement and publication.
3. EVE: native authoring and acceptance, adoption, automatic publication of the AU estate, then an AGNTCY-discovered CV/interview run. Inspect the local approval check and the EVE content ID before its A2A invocation.
4. Compliance: wiki evidence, red general evaluator card, blocked CV run, one card edit and Directory sync, held assessment, human review, audit. Restart recovery and duplicate-request checks are optional extensions.

The existing slide placeholders can still lead into these live examples. The repository's hands-on session numbers are not a proposal to renumber the deck.

## Session 3 evidence to show

Show the same learner agent working in native EVE, then the registered AOA contract, then a CV/interview run calling it across the bridge. Explain the course-owned adapter and inspect the actual `eve/client` session call if asked how real the integration is. Generic bridge signals check field presence; inspect five-question quality and limits explicitly.

Inspect automatic publication and retrieve an OASF record through the real local Directory. Compare its content ID, contract digest and local Agent ID; they identify different things. Show the comparison returning `execution_authorised: false` even when the declaration matches. Finish with the executed composition and its `directory-discovery` evidence. Stop Directory and submit a new intent: it must fail before any AU invocation. Restart it before continuing. Explain that the local registry retains adoption and tool lookup while AGNTCY supplies AU discovery.

Keep the scope explicit: real third-party framework and discovery infrastructure, learner-owned agent, course-owned adapter, local seeded approval. An externally owned agent would still need identity, permission, contract, quality and operational acceptance. The [adoption guide](sessions/session-03-eve/ADOPTION.md#adopting-an-externally-owned-agent) supplies that discussion without claiming it has already been implemented.

## Record the comparison

For each run capture: input fixture, model/version, candidate/card hashes, instructions hash, expected outcome, actual outcome, abstention, total latency, decision latency, usage, provider charge estimate and reviewer effort. Include failures. The TypeSafe price in the trace is a dated estimate; local cost is unestimated, not zero.

For stable-model utility, judge each output against explicit task criteria before considering a model change. A specialist model can reduce the amount of generation required by a product; it does not remove the surrounding contract, knowledge, policy and state responsibilities.

## Remote use

Spark remains available for remote builds and execution; a local laptop checkout can run the same course independently. From an authorised computer, forward port 8080 to view Spark's Studio; no public exposure is required. The Docker services, including AGNTCY Directory, can outlive the Mac connection. Use `main` and confirm the same reviewed commit when continuing from another client. Private provider keys and persisted runtime data do not travel with Git. Final presentation rendering can remain on the Mac.

## Scope still open for a later course iteration

Full AGNTCY federation/identity/messaging, production durable-object deployment, semantic calibration over a labelled dataset, automatic decision training, and the separate expense course-v2 are not represented as completed lessons here. The current course teaches the working boundaries within the four retained examples.
