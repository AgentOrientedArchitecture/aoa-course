# EVE: build, discover and adopt

Keep the existing [EVE walkthrough](WALKTHROUGH.md), including native `eve init`, the authored instructions, native testing and the AOA boundary. Use these revised launchers so the selected model configuration is retained:

```bash
./scripts/revised-eve.sh native
# Complete the original native authoring and acceptance checkpoints, then exit.
./scripts/revised-eve.sh adopt
```

In Windows Command Prompt, use `scripts\revised-eve.bat native`, then `scripts\revised-eve.bat adopt`. The standard `session3-up` and `session3-adopt` launchers also select this revised path when `.env.revised` is present. See the [launcher table](../../pre-work/01-revised-model-access.md#start-and-stop).

The pinned `eve init` may try to start its default agent before the provider-neutral configuration is added. If it reports a default-model metadata error, continue to the original walkthrough’s `agent.ts` configuration checkpoint, then run `eve dev` again. The revised launcher runs native authoring as the host user so Linux workshop files remain editable.

The adopted EVE agent joins the existing CV/interview composition. It remains learner-authored; neither the adapter nor the Directory rewrites its behaviour.

## Publish to a real local Directory

This part uses macOS/Linux shell commands. On Windows, run the Directory lab in WSL2; the installer does not provide a native Windows binary.

```bash
./scripts/directory-install.sh
python3 scripts/directory-lab.py start
```

Leave that terminal open, or run the service under a persistent remote terminal on Spark. It listens on loopback port 8890 and keeps its state under `.course-data/directory`. This is AGNTCY Directory v1.8.0, not an imitation registry. Stop it with Ctrl+C in that terminal; the course's `down` script stops Compose services and does not stop this separate host process.

In a second terminal:

```bash
python3 scripts/directory-lab.py export interviewer-questions > .course-data/interviewer.oasf.json
python3 scripts/directory-lab.py push .course-data/interviewer.oasf.json > .course-data/interviewer.cid
python3 scripts/directory-lab.py search "aoa-course/*"
python3 scripts/directory-lab.py pull "$(cat .course-data/interviewer.cid)" > .course-data/discovered.json
python3 scripts/directory-lab.py check .course-data/discovered.json
```

Allow a few seconds for indexing before searching. Inspect the actual record, its content-addressed identifier and the matching contract digest. The interviewer maps to OASF question generation (10205); parser exports map to fact extraction (10301), verified against the pinned v1.0.0 taxonomy. Mapping another capability requires reviewing a suitable taxonomy item. A declared skill does not establish measured ability.

To expose discovery **before** local adoption, copy the existing interviewer template into the workshop only if no card exists, then export using `--card system/agents-eve/workshop/capability-card.yaml`. This option uses PyYAML (`.venv-course/bin/python` after the test setup). Push and pull the record; `check` should report the missing local capability. Then adopt and repeat. A previous session may already have persisted that capability: inspect the local registry and state this openly rather than deleting it for a cleaner demonstration.

## Three distinct boundaries

- **Directory** stores and discovers a portable declaration. A name or annotation is not verified identity.
- **Local registry** holds the adopted AU's contract and lifecycle. `check` compares the declaration with the current local contract; it never imports or approves an external agent.
- **Planner and governance** decide whether this AU is eligible for this task and whether the complete plan may run in this use context.

Change a copy of the discovered declaration's contract digest and rerun `check`. Discovery still succeeded; local eligibility must fail. No result from the Directory is automatically executable.

## Review questions

- What did EVE provide, what did the adapter add, and what did Directory add?
- Which checks would be needed before adopting an agent published by another organisation?
- Does a matching contract hash prove the runtime behaves as declared?

This lab covers local publish/discover and local acceptance checks. Federation, identity verification, SLIM transport and AGNTCY observability are later course extensions. Primary references: [Directory local deployment](https://dir.agntcy.org/latest/dir/dir-deployment-local/) and [Directory usage scenarios](https://dir.agntcy.org/latest/dir/dir-features-scenarios/).
