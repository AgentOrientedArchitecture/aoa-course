# Session 1: assess a CV and choose the AU

Run the CV workflow, inspect how its evaluator was chosen, then change that
evaluator's behaviour. This page contains the complete session. Allow about
35 minutes, plus model download and container build time on a first run.

The workflow has three responsibilities: parse the CV, assess it against the
job, and report the result. There are three possible evaluator AUs, each with
the same input/output contract but different assessment instructions. The
generation model proposes work; a decision model helps allocate the work.

![Task proposal, eligible AUs, bounded choice and validated execution](../../diagrams/cv-selection.svg)

## 1. Start and inspect the capabilities

Complete the [course setup](../../pre-work/SETUP.md) once, including `.env`
and the generation-provider check. Run commands from the repository root on
the machine where Docker is running.

| Platform | Start Session 1 |
|---|---|
| macOS/Linux | `./scripts/session1-up.sh` |
| Windows Command Prompt | `scripts\session1-up.bat` |

Open [Studio](http://localhost:8080). Choose **Capability cards**, then select
a card in the registry. Switch between **Readable** and **Complete JSON**.
Both views show the same public contract.

Expect five AU cards and one tool:

| Capability | Responsibility |
|---|---|
| `parser-cv` | Extract a structured CV. |
| `evaluator-cv` | General CV/job assessment. |
| `evaluator-cv-data` | Data-engineering assessment. |
| `evaluator-cv-frontend` | Frontend-engineering assessment. |
| `reporter-cv-fit` | Produce the fit report. |
| `tool-document-text` | Read the supplied documents; this is a tool, not an AU. |

Compare the three evaluator cards: purpose, inputs, outputs and declared
constraints. Under **Identity, lifecycle and technical metadata**, inspect
Agent ID, `provenance.model`, `provenance.skills_hash` and lifecycle status.
The specialist evaluators run as separate agents. The decision service and
planner are infrastructure; they are not additional registered AU cards.

This session uses the course's local HTTP registry. Its lifecycle actors are
seeded and registration defaults to approved, so an approved card does not
prove independent verification or output quality. Session 3 introduces
AGNTCY Directory for discovery.

## 2. Run the data-engineering example

Return to **Studio · all controls** and choose **CV fit**. Drop these files
into the corresponding fields, or paste their contents:

- **CV:** `course/sessions/session-01-cv-fit/cv-examples/jordan-okafor.txt`
- **Job description:** `course/sessions/session-01-cv-fit/jd-examples/senior-data-engineer-fintech.txt`

The job document is titled **Senior Data Engineer — Healthcare Payments**;
the filename is retained for compatibility with the supplied examples.

Enter this **Assessment emphasis**:

> Assess production data pipelines, SQL, reliability and governance.

Predict which evaluator should be selected and why, then choose **Run CV fit**.
Watch **Trace** and **Planner**. The default hybrid planner attempts a model
proposal and records an explicit course fallback if that proposal fails or
does not pass validation. The required responsibilities are already defined
by the course workflow; this is bounded planning, not arbitrary process design.

## 3. Follow the selection and the result

Open **AU selection**, select the assessment task and work through the stages:

1. **Proposed task:** what work was requested, and where did the plan come from?
2. **Eligible AUs:** which cards passed the input, output and approved-lifecycle
   checks? Why were the others excluded?
3. **Choice:** which eligible AU did the decision model return? Inspect the
   provider, model, latency and **Decision evidence and usage**. The extra
   `no_suitable_capability` option permits abstention.
4. **Composition check:** did the whole plan retain the required tasks and
   their upstream evidence? Checking each AU separately would not catch a
   report that bypassed the assessment.
5. **Accepted binding:** which concrete AU was authorised to execute after
   those checks? A returned model choice is not yet an accepted binding.

The choice uses the task purpose and your **Assessment emphasis**. If you leave
that field blank, it uses the first 16,000 characters of the job description,
whether pasted or uploaded. Uploaded job text is prepared by the existing
document reader before planning. The allocator does not read the CV; the chosen
evaluator receives the parsed CV and job description when it executes. A single
eligible AU is bound without a decision-model call.

Open **Run review** and select each AU output. Compare **Complete output JSON**,
the recorded invocation inputs and observed signals. For the assessment,
check that its scores, gaps and verdict have support in the supplied CV and
job description. A declaration of specialisation is not a measured quality
score, and valid JSON is not proof of a sound assessment.

Return to **Studio · all controls** to inspect the trace boundaries:

- `parser-cv` calls the declared `tool-document-text` tool.
- AUs are invoked over A2A; the tool call is a separate traced boundary.
- The same `trace_id` connects planning, selection, invocation and responses.
- Signals report specific observations, such as output shape and latency.
  They do not measure every aspect of quality.

If selection is held, inspect its recorded reason in **AU selection**. No
application AU should have run. Resolve provider errors through the setup
guide; inspect a low probability or no-fit result as a decision to review.

## 4. Change the assessment

Run the matching frontend pair:

- `cv-examples/sam-everett.txt`
- `jd-examples/frontend-engineer-design-systems.txt`

Both paths are within this session's directory. Set **Assessment emphasis** to:

> Assess accessibility, design systems, UI testing and browser performance.

Compare the selected AU, decision evidence, latency and resulting assessment
with the first run. Keep the generation model fixed. Then try a mismatched
pair, such as Jordan's data CV against the frontend job. The [example table](README.md#example-pairs)
gives discussion expectations, not guaranteed verdicts.

Try an emphasis outside the evaluators' declared scope. Does the model choose
`no_suitable_capability`, or does it confidently select something unsuitable?
Record what actually happens. The hosted probability threshold is a classroom
policy, not calibrated accuracy. The local Ollama decision baseline reports
no probability; allowing unscored choices is an explicit configuration choice.

## 5. Change the AU that actually ran

First inspect the **Accepted binding** from your last successful run. Edit
that AU's instructions, using the matching row below. Keep a copy of your
input, output and original instruction before changing it.

| Accepted capability | File to edit from the repository root |
|---|---|
| `evaluator-cv` | `system/agents/evaluator/capabilities/cv/instructions.md` |
| `evaluator-cv-data` | `system/agents/evaluator/capabilities/cv-data/instructions.md` |
| `evaluator-cv-frontend` | `system/agents/evaluator/capabilities/cv-frontend/instructions.md` |

1. In **Capability cards**, note its current `provenance.skills_hash` and
   Agent ID. The short hash also appears beside its registry entry.
2. Change one instruction, for example requiring named evidence for every gap
   or making the seniority rubric stricter. Save the file.
3. Watch that card update without a container restart. The watcher rereads the
   instructions, computes a new hash and registers the changed card. Agent ID
   stays fixed.
4. Rerun exactly the same inputs and emphasis. Check the accepted binding
   again before comparing outputs. If another AU was selected, you have changed
   more than one variable.
5. Inspect the result and signals. Behaviour may change; a hash change alone
   neither guarantees different output nor proves an improvement.

You can also edit the `capability-card.yaml` beside the selected instructions,
for example adding a constraint. The card re-registers too. A declared
constraint is inspectable; its presence does not by itself implement a control.
Restore your experimental edits when finished so later sessions share the
supplied baseline.

## 6. Optional: compare providers or the probability policy

Use the [setup guide](../../pre-work/SETUP.md) to change the existing `.env`;
do not create another environment file. Keep the decision provider fixed when
comparing generation models, and keep the generation model fixed when comparing
decision providers.

Stop and restart after changing configuration:

| Platform | Stop | Restart Session 1 |
|---|---|---|
| macOS/Linux | `./scripts/down.sh` | `./scripts/session1-up.sh` |
| Windows Command Prompt | `scripts\down.bat` | `scripts\session1-up.bat` |

After a generation-model change, inspect the selected card's
`provenance.model`; its Agent ID and public contract remain. For a decision
provider change, inspect the **Choice** evidence. Compare results on the same
examples, including failures and latency, before concluding that a replacement
is better.

On the hosted route you can also raise `DECISION_MIN_PROBABILITY`, restart and
rerun the same example to see whether selection is held. This demonstrates a
policy gate, not calibration. Restore the original setting afterwards. The
local unscored baseline cannot demonstrate this probability gate.

## Review and finish

- All three evaluators accept the same inputs. What establishes eligibility,
  and what remains a judgement?
- A selected AU returns the right JSON shape but a poor assessment. Which
  observations should affect future selection?
- Why must the composition check preserve the report's dependency on the
  evaluation as well as check each AU contract?
- If human review is the bottleneck, what would faster inference change about
  overall throughput?
- The registry accepted your instruction or card edit immediately. What
  approval and evaluation would you require in an enterprise?

The card is the public promise; instructions supply behaviour; tools are
declared dependencies; the model sits behind that boundary. This exercise
makes changes inspectable and gives you outputs to assess. It does not
automatically learn which AU is best.

Stop with `./scripts/down.sh` or `scripts\down.bat`. This retains course data.
Continue with the [Session 2 walkthrough](../session-02-wiki/WALKTHROUGH.md).
The [decision reference](DECISIONS.md) is optional background, not another
required lab.
