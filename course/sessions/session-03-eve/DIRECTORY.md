# EVE: build, discover and adopt

Read [Adopting EVE with AGNTCY Directory](ADOPTION.md) first. EVE runs the interviewer, AGNTCY Directory publishes a portable description, and the local AOA registry and planner handle adoption and composition.

## Prepare the EVE capability

Keep the [EVE walkthrough](WALKTHROUGH.md): native `eve init`, authored instructions, native acceptance and then AOA adoption. With `.env.revised` configured, use `session3-up.sh/.bat`, complete the native exercise and exit its shell, then run `session3-adopt.sh/.bat`. The [launcher table](../../pre-work/01-revised-model-access.md#start-and-stop) covers both platforms. A healthy adopted `interviewer-questions` card must be in the local registry for the main export/comparison sequence below.

The pinned `eve init` may report a default-model metadata error before the provider-neutral `agent.ts` is added. Complete that configuration checkpoint in the native walkthrough and run `eve dev` again. The agent remains learner-authored; neither the adapter nor Directory rewrites its behaviour.

## Start Directory in Docker

Use the same checkout on `main` as the EVE lab. Docker runs the real AGNTCY **v1.8.0** daemon, its CLI and the course's Python helper. No host `dirctl`, Python installation or separate WSL checkout is needed. On Windows, use Docker Desktop with Linux containers, as for EVE.

From the repository root:

| Action | macOS/Linux | Windows Command Prompt |
|---|---|---|
| Build and start; wait for readiness | `./scripts/directory.sh up` | `scripts\directory.bat up` |
| Inspect the installed version | `./scripts/directory.sh cli version` | `scripts\directory.bat cli version` |
| Follow Directory logs | `./scripts/directory.sh logs` | `scripts\directory.bat logs` |
| Stop Directory, keeping records | `./scripts/directory.sh stop` | `scripts\directory.bat stop` |

The container uses the official `dir-ctl` image's binary, pinned by version and multi-platform digest, with the course helper and PyYAML alongside it. It runs in the background and publishes host loopback ports 8890 (CLI) and 8891 (upstream browser catalogue). Its helper reaches the local AOA registry through `registry:7100` on the course Docker network. Start Directory and AOA from the same checkout and Compose project.

Directory's database and record store persist in **`.course-data/directory`**. Exports and retrieved JSON files are also written under `.course-data`, where you can open them in your editor. Neither `directory stop` nor the normal course `down.sh/.bat` removes that data. The course `logs` and `down` commands include Directory.

The CLI connection is insecure within this local teaching setup; container packaging does not add publisher verification or enterprise approval. The [original host-installed route](NATIVE-DIRECTORY.md) is retained. If you used it previously, stop its daemon with Ctrl+C before using the container: never run two daemons against the same data directory.

## Publish, find and retrieve

On **macOS/Linux**:

```bash
./scripts/directory.sh export interviewer-questions --out interviewer.oasf.json
./scripts/directory.sh push interviewer.oasf.json --out interviewer.cid
./scripts/directory.sh search "aoa-course/*"
./scripts/directory.sh pull --cid-file interviewer.cid --out discovered.json
./scripts/directory.sh check discovered.json
```

On **Windows Command Prompt**:

```bat
scripts\directory.bat export interviewer-questions --out interviewer.oasf.json
scripts\directory.bat push interviewer.oasf.json --out interviewer.cid
scripts\directory.bat search "aoa-course/*"
scripts\directory.bat pull --cid-file interviewer.cid --out discovered.json
scripts\directory.bat check discovered.json
```

The helper writes UTF-8 files inside the mounted `.course-data` folder. `--cid-file` reads the returned identifier directly, so no shell substitution or redirection is needed. The original helper's stdout/redirection interface remains supported for native users.

Allow a few seconds for indexing before searching. Inspect `.course-data/interviewer.oasf.json`, the actual content ID in `interviewer.cid`, and the retrieved record in `discovered.json`. The interviewer maps to OASF question generation (10205); parser exports map to fact extraction (10301), checked against the pinned v1.0.0 taxonomy. Mapping another capability requires reviewing a suitable taxonomy entry. A declared skill does not establish measured ability.

The final command reports:

| Field | Expected for the matching adopted card | Meaning |
|---|---|---|
| `matching_local_contract` | `true` | The selected contract fields match the record's digest |
| `local_lifecycle_approved` | `true` | The local card's lifecycle is approved |
| `locally_eligible` | `true` | Both comparison conditions hold; task eligibility still follows |
| `execution_authorised` | `false` | Discovery/comparison does not grant execution permission |
| `identity_verified_by_directory_record` | `false` | These annotations do not verify the publisher |

Read the fields: `check` is informational and can exit successfully while reporting a mismatch. It is not an automated admission controller. The [adoption guide](ADOPTION.md#three-descriptions-of-the-same-capability) lists the exact hash scope and distinguishes the OASF record, AOA card and A2A Agent Card.

## View the OASF descriptions

Open **`.course-data/interviewer.oasf.json`** in Zed or another text editor to read the exported description. Open **`.course-data/discovered.json`** to inspect the record actually retrieved from Directory. These files show the name, version, description, declared skills and domains, modules, and the course's contract annotations. This is the full OASF record; Studio's capability-card view shows the separate local AOA contract.

The upstream **AI Catalog** is also available at [http://localhost:8891](http://localhost:8891) after `directory.sh up` or `directory.bat up`. Select a listed card for its summary, tags and **Catalog Entry JSON**. This is AGNTCY's built-in interface, not a course viewer.

**The v1.8.0 catalogue does not list every OASF record.** It projects records containing an A2A, MCP or Agent Skills module. The course's current export has `modules: []`, so it remains searchable and retrievable through the CLI but does not appear as a card in this browser catalogue. An apparently empty course search in the browser does not mean publication failed. The daemon's self-description may be the only visible card. Catalogue JSON is a projection, not the original OASF JSON. This behaviour is explicit in the [pinned upstream catalogue implementation](https://github.com/agntcy/dir/blob/v1.8.0/api/catalog/v1/catalog.go).

Use the editor files for this lab. A future catalogue-visible export needs a reviewed, accurate integration module; do not invent an endpoint or claim A2A compatibility simply to make a card appear. The browser's generic wording about verified records also does not establish that our local records are signed, trusted or approved for execution.

## Discover before adoption

The container also mounts the checked-in contract template read-only. You can publish its description before an interviewer has been adopted:

```bash
./scripts/directory.sh export interviewer-questions --card /course-templates/interviewer-questions.yaml --out interviewer-before-adoption.oasf.json
```

On Windows, use `scripts\directory.bat` with the same arguments. Push and retrieve this record as above. A learner-authored card is also accessible at `/workshop/capability-card.yaml` after it exists.

Native EVE authoring stops AOA services. A comparison then needs the registry running; to inspect an unadopted record, start just the registry with `docker compose -f system/docker-compose.yml --profile session3 up --build -d registry`. A previous session may already have persisted the card: inspect that history rather than deleting it. Complete adoption, then repeat the comparison and CV/interview run.

## Three distinct boundaries

- **Directory** stores and discovers a portable declaration. A name or annotation is not verified identity.
- **Local registry** holds the adopted AU's contract and lifecycle. `check` compares declarations; it never imports or approves an external agent.
- **Planner and governance** decide whether the adopted AU fits this task and whether the complete plan may run in this use context.

Save a copy of `.course-data/discovered.json` as `.course-data/mismatch.json`, change its contract digest in your editor and run `directory.sh check mismatch.json` or `directory.bat check mismatch.json`. Discovery still succeeded; local eligibility must be false. No Directory result is automatically executable.

Finish in Studio's **CV fit + interview** workflow. Inspect the accepted EVE capability, its invocation and five questions grounded in the selected evaluator's output. Directory publication alone is not the final success condition. Keep the portable record, accepted local card and run evidence together.

## Troubleshooting

| Observation | Check |
|---|---|
| Docker cannot start | Start Docker Desktop/Engine; on Windows select Linux containers |
| `agntcy-directory` is not running | Run `directory.sh up` or `directory.bat up`; inspect `logs` if readiness fails |
| Host port 8890 is already in use | Stop the old host Directory daemon or identify the existing container; do not run two daemons on the same data |
| Browser port 8891 is already in use | Set `COURSE_DIRECTORY_UI_PORT` to a free host port before `directory.sh up` or `directory.bat up`, then browse that port |
| CLI finds the record but the catalogue does not | Plain OASF records without a recognised integration module are not projected into the v1.8.0 catalogue; inspect the pulled JSON |
| Search is initially empty | Allow indexing to finish; retrieve using the returned content ID |
| Registry connection fails | Run the adopted AOA session or the registry-only command above, in the same checkout/project |
| A file cannot be found | Helper paths are relative to `.course-data`; use the filename, not a Windows host path |
| A contract comparison fails | Inspect the fields and whether the record predates a card edit; publish a newly reviewed record rather than changing the digest to hide the difference |
| Matching record but no working result | Check runtime health, model access, local selection and the actual EVE reply |

The raw CLI remains available through `directory.sh cli ...` and `directory.bat cli ...`. Keep record paths relative to `.course-data`. The helper maps only parser and interviewer capabilities; it does not expose every AGNTCY feature.

## Review questions

- What did EVE provide, what did the adapter add, and what did Directory add?
- Which checks would be needed before adopting an agent published by another organisation?
- Does a matching contract hash prove the runtime behaves as declared?

This lab covers a real local publish/discover round trip and local comparison. Federation, verified identity, SLIM and AGNTCY observability remain later course extensions. Primary references: [Directory local deployment](https://dir.agntcy.org/latest/dir/dir-deployment-local/) and [container CLI quickstart](https://dir.agntcy.org/latest/dir/dir-quickstart/).
