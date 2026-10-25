# Native Directory alternative

This preserves the original host-installed route. The standard course now uses [Directory in Docker](DIRECTORY.md) on macOS, Linux and Windows. Use only one Directory daemon against a data directory at a time; stop the host daemon before starting the container. Existing records remain under `.course-data/directory`.

Read [Adopting EVE with AGNTCY Directory](ADOPTION.md) first. It explains why these are separate boundaries, what the course bridge implements, and what this integration does and does not establish.

Keep the existing [EVE walkthrough](WALKTHROUGH.md), including native `eve init`, the authored instructions, native testing and the AOA boundary. Use these revised launchers so the selected model configuration is retained:

```bash
./scripts/session3-up.sh
# Complete the original native authoring and acceptance checkpoints, then exit.
./scripts/session3-adopt.sh
```

In Windows Command Prompt, use `scripts\session3-up.bat`, then `scripts\session3-adopt.bat`. These are the standard course launchers; they use `.env`. See the [launcher table](../../pre-work/01-revised-model-access.md#start-and-stop).

The pinned `eve init` may try to start its default agent before the provider-neutral configuration is added. If it reports a default-model metadata error, continue to the original walkthrough’s `agent.ts` configuration checkpoint, then run `eve dev` again. The revised launcher runs native authoring as the host user so Linux workshop files remain editable.

The adopted EVE agent joins the existing CV/interview composition. It remains learner-authored; neither the adapter nor the Directory rewrites its behaviour.

## Publish to a real local Directory

This part uses macOS/Linux shell commands. On Windows, run the whole Session 3 Directory exercise from a WSL2 checkout with Docker integration; the installer does not provide a native Windows binary. This keeps the workshop, registry connection and Directory files in one environment. The native Windows EVE-only route remains available.

```bash
./scripts/directory-install.sh
python3 scripts/directory-lab.py start
```

Leave that terminal open, or run the service under a persistent remote terminal on Spark. It listens on loopback port 8890 and keeps its state under `.course-data/directory`. This is AGNTCY Directory v1.8.0, not an imitation registry. Stop it with Ctrl+C in that terminal; the course's `down` script stops Compose services and does not stop this separate host process.

The helper uses an insecure local connection. The installer records the downloaded binary's hash; it does not verify a publisher signature. Neither is a production trust configuration.

In a second terminal:

```bash
python3 scripts/directory-lab.py export interviewer-questions > .course-data/interviewer.oasf.json
python3 scripts/directory-lab.py push .course-data/interviewer.oasf.json > .course-data/interviewer.cid
python3 scripts/directory-lab.py search "aoa-course/*"
python3 scripts/directory-lab.py pull "$(cat .course-data/interviewer.cid)" > .course-data/discovered.json
python3 scripts/directory-lab.py check .course-data/discovered.json
```

Allow a few seconds for indexing before searching. Inspect the actual record, its content-addressed identifier and the matching contract digest. The interviewer maps to OASF question generation (10205); parser exports map to fact extraction (10301), verified against the pinned v1.0.0 taxonomy. Mapping another capability requires reviewing a suitable taxonomy item. A declared skill does not establish measured ability.

The final command reports `matching_local_contract`, `local_lifecycle_approved`, `locally_eligible`, `execution_authorised` and `identity_verified_by_directory_record`. In the matching adopted case, the first three should be true and the last two false. Read the fields: this comparison command is informational and can exit successfully while reporting a mismatch. It is not an automated admission controller.

To expose discovery **before** local adoption, export the checked-in template directly:

```bash
.venv-course/bin/python scripts/directory-lab.py export interviewer-questions --card system/agents-eve/runtime/templates/interviewer-questions.yaml > .course-data/interviewer-before-adoption.oasf.json
```

This optional path needs PyYAML from the [test environment](../../REVISED-VALIDATION.md#run-the-checks). Push and pull that record as above. Native EVE authoring stops the AOA services, so a comparison at this point may report a connection failure because the registry is not running. To inspect absence in a live registry, start only that service with `docker compose -f system/docker-compose.yml --profile session3 up --build -d registry`, then run `check`. A previous session may already have persisted the capability: inspect and explain that history rather than deleting it. Adoption then makes the runtime available; repeat the comparison and the full CV/interview run.

## Three distinct boundaries

- **Directory** stores and discovers a portable declaration. A name or annotation is not verified identity.
- **Local registry** holds the adopted AU's contract and lifecycle. `check` compares the declaration with the current local contract; it never imports or approves an external agent.
- **Planner and governance** decide whether this AU is eligible for this task and whether the complete plan may run in this use context.

Change a copy of the discovered declaration's contract digest and rerun `check`. Discovery still succeeded; local eligibility must fail. No result from the Directory is automatically executable.

Finish the demonstration in **CV fit + interview**. The planner should call the locally adopted EVE capability and return five questions grounded in the selected evaluator's output. Directory publication alone is not the final success condition. Inspect the [invocation boundary](ADOPTION.md#follow-one-invocation) and keep the record, accepted card and run evidence together.

## Troubleshooting the boundary

| Observation | Check |
|---|---|
| Connection refused on port 8890 | Keep the Directory daemon running in its own terminal; use the same machine/environment as the helper |
| Search returns nothing immediately after push | Wait briefly for indexing; pull using the actual content ID returned by push |
| Registry connection fails during comparison | Native EVE mode stops AOA; adopt or start the registry before comparing |
| Contract mismatch | Inspect the specific contract fields and whether the exported record predates a card edit; publish a newly reviewed record rather than changing a hash to hide the difference |
| Matching record but no working result | Check runtime health, model access, local selection and the actual EVE reply; metadata comparison does not test execution |
| EVE's initial scaffold reports unknown model metadata | Complete the provider-neutral `agent.ts` checkpoint in the native walkthrough, then rerun `eve dev` |

## Review questions

- What did EVE provide, what did the adapter add, and what did Directory add?
- Which checks would be needed before adopting an agent published by another organisation?
- Does a matching contract hash prove the runtime behaves as declared?

This lab covers local publish/discover and local acceptance checks. Federation, identity verification, SLIM transport and AGNTCY observability are later course extensions. Primary references: [Directory local deployment](https://dir.agntcy.org/latest/dir/dir-deployment-local/) and [Directory usage scenarios](https://dir.agntcy.org/latest/dir/dir-features-scenarios/).
