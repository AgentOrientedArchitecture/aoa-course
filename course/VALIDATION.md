# Course validation

Use `main` and the [setup guide](pre-work/SETUP.md). This record separates observed
integration behaviour, automated checks and the learner walkthroughs still needed.
The [content review](DOCUMENTATION-REVIEW.md) describes the current documentation pass.

## Observed integration behaviour

| Area | Observation and scope |
|---|---|
| Hosted models | Spark rehearsals on 21 and 25 October 2026 used Cerebras `gpt-oss-120b` and TypeSafe `jev-1.13.0`. CV allocation selected data/frontend evaluators; wiki fixtures exercised promotion and rejection. These are functional observations, not calibrated quality or cost benchmarks |
| EVE | Real EVE 0.17.1 scaffolded, started and ran the authored interviewer. A composed CV/interview run returned five questions meeting the documented field limits |
| AGNTCY | Real Directory v1.8.0 published and discovered OASF 1.0.0 records. The live Session 3 run discovered six active AUs; the accepted EVE binding and invocation carried the Directory content ID |
| Discovery failure | Stopping the rehearsal Directory caused a new intent to fail with 503 and zero AU invocations. The local registry list was not substituted |
| Exact-result review | A held case survived planner restart with the same result digest. Approval released the identical payload; an identical retry added no second release |
| Local model route | Ollama `gpt-oss:20b` completed generation and constrained choice on Spark, without invented probabilities. Observed requests took roughly 111–168 seconds; this route needs a hardware-specific timing check before class |
| Mac generation access | The consolidated provider smoke test completed a real Cerebras request on 25 October. It does not test TypeSafe |

[Structured AGNTCY rehearsal evidence](validation/2026-10-25-agntcy/live-evidence.json)
records exact models, bindings, content IDs and outage behaviour. The
[dated validation history](../archive/course-content-before-review/course/REVISED-VALIDATION.md)
preserves the environments, commits and earlier observations; it is historical
evidence, not setup instructions.

## Run the checks

Create an isolated Python environment and install `tests/requirements.txt`:

```bash
python3 -m venv .venv-course
.venv-course/bin/python -m pip install -r tests/requirements.txt
.venv-course/bin/python -m pytest -q tests
```

Windows Command Prompt:

```bat
py -m venv .venv-course
.venv-course\Scripts\python -m pip install -r tests\requirements.txt
.venv-course\Scripts\python -m pytest -q tests
```

The suite checks response validation, eligibility/composition, wiki gating,
persistence/review, document navigation and actual shell/batch launchers with
harmless command stand-ins. It does not make provider calls.

Docker integration checks run separately on macOS/Linux:

```bash
.venv-course/bin/python tests/check_course_configuration.py
.venv-course/bin/python tests/check_directory_container.py
.venv-course/bin/python tests/check_eve_workshop.py
```

The native EVE check uses POSIX user IDs; run it on macOS/Linux or use its Linux
CI result. The configuration check parses the effective Compose setup for all four sessions and hosted/local
routes. The Directory check uses an isolated registry and records for all 18 AU
contracts, checks catalogue visibility, mismatch/outage behaviour and recovery.
The EVE check boots the real framework as a non-root learner with the exact
TypeScript block from the walkthrough, offline dependencies and networking disabled.
These checks use temporary state and do not replace authored workshop files.

The repository's [Course launchers CI](https://github.com/AgentOrientedArchitecture/aoa-course/actions/workflows/launcher-checks.yml)
runs native shell/batch checks on Linux, macOS and Windows, plus real container
checks on Linux. Windows launcher checks use a Docker stand-in; they are not a
full Docker Desktop class rehearsal.

## Checks still needed in the learner environment

- Complete fresh Mac and Windows walkthroughs, including Docker mounts, native EVE
  acceptance, provider access, AGNTCY discovery and the Session 4 restart/review.
- Time the examples and evaluate actual CV assessments, interview questions and
  promotion decisions against explicit task criteria. A valid schema or model
  probability is not semantic correctness; the 0.65 gate is a teaching setting.
- Review the dated regulation corpus before any real compliance use. The exercise
  demonstrates evidence and controls, not legal certification.
- For an externally owned agent, establish identity, access, evaluation and operating
  responsibilities. This local lab does not deploy federation, verified identity,
  SLIM or an enterprise trust service.

SQLite supports the single-process classroom case lifecycle. Interrupted external
invocation is marked for inspection, not replayed automatically. It does not claim
exactly-once external effects or constitute a Cloudflare Durable Objects deployment.
