# Revised course validation

Use `main` for current course setup and delivery. The dated records below retain the revisions and environments actually checked; they are not instructions to use a development branch.

## Spark integration, 21 October 2026

Checked in `/home/lewis/work/AOA/aoa-course` on the then-development branch `codex/october-course-rebuild`, based on main `13ed2a3`.

## Verified

| Check | Observed result |
|---|---|
| Automated regressions | 21 pass: response validation, explicit choice under rounded ties, eligibility, final composition, no execution of an incomplete plan, wiki gating, source quote retention, saved-result integrity, transactional rollback and concurrent duplicate review |
| Hosted generation | Cerebras `gpt-oss-120b` completed the CV and wiki workflows; the CV planner trace records an LLM proposal with no fallback |
| Hosted allocation | TypeSafe `jev-1.13.0` chose `evaluator-cv-data` for the data emphasis and `evaluator-cv-frontend` for the frontend emphasis; both complete compositions passed validation |
| Decision-powered wiki AU | Architecture fixture promoted (`376f437a15b3`); fairy-tale fixture rejected (`a6e403345b76`) through the typed decision service |
| Native EVE | Pinned 0.17.1 scaffolded and installed dependencies offline in separate fixtures; host-user scaffolding succeeded; provider-neutral configuration from the original walkthrough started successfully |
| EVE adoption | The original AOA adapter registered the unchanged authored agent; a direct call returned five questions; complete CV → frontend evaluator → EVE composition returned five questions (`2e92f0a3b700`) |
| Real AGNTCY Directory | v1.8.0 local daemon validated, stored, indexed, searched and returned OASF 1.0.0 parser and interviewer records; local contract check passed and explicitly did not authorise execution |
| Compliance before execution | Undeclared selected evaluator was rejected with no application invocation (`635d43f6de9d`) |
| Durable exact-result review | Held case `5d6c2764435d` survived an actual planner restart with the same result digest; approval released the identical draft; an identical retry added zero events and there was exactly one release |
| Existing flow audit | The rejected and released cases both had the expected evidence; the original audit reported two green flows and retained its explicit limits on what green establishes |
| Browser inspection | Saved-case replay displays the actual plan, eligible alternatives, returned decision and accepted binding; the course guide is served directly from Spark |
| Preservation | Original walkthrough text, fixtures, launchers and learner EVE workshop retained; `feat/decision-allocator`, course-v2 and local training artefacts retained |

The hosted data-emphasis CV check took about 3.7 seconds end to end, including a roughly 0.29-second decision call. These are single functional checks, not quality, latency or cost benchmarks. All candidate data used in verification was synthetic. The two wiki fixtures were inspected before hosted submission and contain teaching prose and fiction.

## Local route

The Ollama `gpt-oss:20b` decision adapter returned the expected frontend choice with no invented probability. Its first cold request took about 168 seconds on this Spark setup. The adapter now requests an 8k context by default rather than the server's much larger model default. A subsequent decision check took about 111 seconds; a local generation check returned valid JSON in about 116 seconds. An initial generation smoke check with a 40-token budget returned no completed JSON; the repeat with 512 tokens completed. The course retains its larger generation budget. Time local models before class; these runs were much slower than the hosted route and should not be presented as equivalent classroom latency.

## Delivery limits

- The smoke checks establish working integration, not calibrated decision accuracy. The 0.65 probability threshold remains an illustrative policy setting.
- EVE's initial scaffold tries to launch its default model before the walkthrough's provider-neutral configuration is added. The pinned version reports a default-model metadata error at that point; the configured course agent starts and runs. The revised walkthrough makes this checkpoint explicit.
- The durable case implementation runs in a single planner process on SQLite. Restart during an external invocation is marked interrupted and is not automatically replayed. No exactly-once external-effect guarantee is made.
- AGNTCY testing covers a real **local** Directory, portable records and contract comparison. Federation, verified identity, messaging and observability deployment remain outside this lab.
- The existing compliance corpus and interpretation are retained. No claim of current legal certification is introduced.
- Browser inspection and these checks do not replace Lewis's teaching review or a full timed class rehearsal.

## Run the checks

```bash
uv venv .venv-course
uv pip install --python .venv-course/bin/python -r tests/requirements.txt
.venv-course/bin/python -m pytest -q tests
```

Live run evidence remains in the planner's persisted traces and the ignored `.course-data/` fixture directory on Spark. The local EVE validation fixture is separate from `system/agents-eve/workshop`, which remains ready for learner authoring. Continue course work on `main`; temporary test fixtures are not course source.

The 21 October Spark preview used Session 3 with the isolated EVE validation fixture; this is not a claim about which services are running now. Use the launchers in the guide to switch sessions; original source material and all saved cases remain available.

## Launcher checks, 24 October 2026

The standard session, EVE build/adoption and provider-check launchers now select the revised configuration when `.env.revised` is present, on both shell and Windows batch paths. Explicit original-course selection remains available. Stop/log commands include every original and revised Compose service; stopping retains saved data and volumes by default.

- Eleven launcher tests pass on macOS using harmless Docker/curl stand-ins. They execute the actual scripts from a path containing spaces and check session selection, original-course access, local Ollama selection, configuration precedence, argument/error propagation, EVE build/adoption ordering, learner-file preservation and shutdown coverage.
- Every shell script passes `bash -n`.
- Real Docker Compose configuration validation passes for all four revised sessions with both example model routes, and for the combined stop/log service configuration. These checks do not start or stop containers.
- The `Course launchers` GitHub Actions workflow passed all 11 tests on Linux, macOS and native Windows at commit `a029f79`: [cross-platform results](https://github.com/AgentOrientedArchitecture/aoa-course/actions/runs/40096715858). The first Windows run caught an EVE helper-path error after argument processing; the corrected scripts passed the complete rerun.

These checks validate launcher behaviour. They do not replace the fresh Mac/Windows walkthroughs with Docker and live providers, which remain pending. AGNTCY Directory is a separate foreground process, and the current Windows Directory instructions use WSL2.

To repeat just the launcher checks without Docker or provider keys:

```bash
python -m unittest discover -s tests -p test_launchers.py -v
```

Use `python3` if that is the Python command on your machine.

## Documentation checks, 25 October 2026

The [documentation review](DOCUMENTATION-REVIEW.md) adds a system map and an EVE/AGNTCY adoption guide grounded in the implementation. All 41 tests pass, including new coverage for document rendering, heading anchors, SVG serving and file access boundaries. All 136 local links in the changed Markdown resolve, and all six diagrams were rendered and visually inspected. A browser check confirmed image loading and section navigation in the existing Studio documentation route. This pass made no live provider calls and did not repeat the 21 October integration rehearsal.
