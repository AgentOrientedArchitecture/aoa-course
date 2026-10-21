# Revised course delivery

## Before the class

- Start on the reviewed revision of `codex/october-course-rebuild` in Spark's `aoa-course`.
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

## Record the comparison

For each run capture: input fixture, model/version, candidate/card hashes, instructions hash, expected outcome, actual outcome, abstention, total latency, decision latency, usage, provider charge estimate and reviewer effort. Include failures. The TypeSafe price in the trace is a dated estimate; local cost is unestimated, not zero.

For stable-model utility, judge each output against explicit task criteria before considering a model change. A specialist model can reduce the amount of generation required by a product; it does not remove the surrounding contract, knowledge, policy and state responsibilities.

## Remote use

Spark remains the build and execution location. From an authorised computer, forward port 8080 to view Studio; no public exposure is required. Docker services and Directory's detached process can outlive the Mac connection. Use the branch and commit in the validation record when continuing from another client. Final presentation rendering can remain on the Mac.

## Scope still open for a later course iteration

Full AGNTCY federation/identity/messaging, production durable-object deployment, semantic calibration over a labelled dataset, automatic decision training, and the separate expense course-v2 are not represented as completed lessons here. The current course teaches the working boundaries within the four retained examples.
