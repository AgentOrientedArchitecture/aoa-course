# Local course rehearsal — 25 October 2026

**Result: partial rehearsal with unresolved failures. This was not a full-course
pass.** Further local-model investigation was deferred at Lewis's request.

The [evidence archive](evidence.zip) preserves requests, responses, traces,
independent quality reviews and the experimental test harness. The harness is
an investigation snapshot, **not another learner setup or walkthrough**. Continue
to use the [course setup guide](../../pre-work/SETUP.md) and normal session paths.

## Configuration and scope

- Course baseline: `66c02b0eb197b830b1510dabf95899748aac84cc`.
- Generation: local `Qwen3.8-27B-4bit` through **oMLX 0.7.2** on the Mac.
- Decisions: local `clef-flash-oQ4e` through native `/v1/systemone`.
- Decision gate: **0.65**, with unscored choices disabled throughout. The gate
  was not lowered to make a run complete; it is not a calibrated accuracy claim.
- EVE: **0.17.1**, using the authored example from the Session 3 walkthrough.
- Separate checkout, Compose project, image tags, ports and data were used for
  the rehearsal, preserving the hosted Cerebras/Jev walkthrough configuration.

This went beyond the earlier [decision-interface checks](../2026-10-25-local-models/README.md):
CV and wiki inputs entered through Studio's API and executed the application AUs
and tools. Native EVE was exercised separately. Browser interaction and Windows
local inference were not tested.

## Findings

| Area | What worked | What remains unresolved |
|---|---|---|
| CV assessment | Valid model-proposed plans; frontend and mismatched CV/job runs completed with the expected specialist and consistent broad verdict/recommendation. | The original data example selected the data AU at **0.6129** and correctly held before execution. A separately clarified input completed but chose the general AU at **0.7063**. Contradictory image-generation emphasis did not cause abstention. |
| Wiki curation | All eight workflows completed with model-proposed plans. Relevant notes were promoted; fiction was rejected and the unsupported claim sent to review. Both withheld inputs made no publication call. | One stored passage joined separate source bullets into a non-verbatim quote. Summaries incorrectly expanded AOA. |
| Wiki query | The supported question returned actual passage citations and an answer assembled from stored evidence. | A question about an absent Clef production measurement returned unrelated passages, **high confidence** and no declared gap. The query parser retained the constraints; the deterministic retrieval/sufficiency logic did not enforce them. |
| Native EVE | Local model communication worked. Later experimental restrictions produced mechanically valid five-question JSON for rich and sparse inputs. | The original agent parked both inputs using `ask_question`. Later runs still delegated through an `agent` action despite the reported tool inventory being empty. The intended action-free boundary was not established. |

The CV content review also found unsupported seniority and regulated-work
assumptions, missing relevant side-project evidence, and wording that converted
“not evidenced in this CV” into “no experience”. Valid output shapes did not
establish sound assessment. The wiki's preserved parser text likewise did not
prove faithful extraction or summary accuracy.

The clarified CV run and EVE retries are retained separately from their failed
baselines. No experimental EVE tool restriction or prompt rewrite was adopted
as a verified course fix. One CV inspection defect was corrected: output checks
must inspect the AU that actually ran while reporting unexpected selection
separately. The original evidence remains preserved.

## Not reached

The **adopted EVE/AGNTCY flow in Session 3** and **Session 4 governance, held-result
review and restart recovery** were not reached in this local-model rehearsal.
Earlier unit or container checks do not fill that gap. Complete those stages
after resolving native EVE acceptance and deciding how to address selection,
source fidelity and answer sufficiency; do not present this record as approval
of a fully local classroom configuration.

The isolated containers and model server were stopped after the rehearsal.
The installed oMLX 0.7.0 helper was restored from its pre-test backup. Evidence,
models and local test data were retained. The separate provider-neutral
configuration change passed both live Cerebras and Jev smoke checks and the
automated course checks; those results do not change the local findings above.
