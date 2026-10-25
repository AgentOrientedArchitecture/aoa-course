# Documentation review — 25 October 2026

Reviewed the October course implementation against the current Compose overlays, launchers, registry, planner/allocation, decision adapters, case store, EVE bridge and Directory helper. This was an implementation/documentation review, not a fresh provider-backed rehearsal or a legal review of the curated corpus. Current setup and delivery use `main`.

## Findings addressed

| Gap | Change |
|---|---|
| No clear first explanation of the revised running system | Added `ARCHITECTURE.md` with component responsibilities, session differences, source pointers and six SVG diagrams |
| Older references said held results were lost on restart without identifying the profile | Marked the original in-memory path and explained the revised SQLite path in the planner, system and compliance documentation |
| Registry documentation implied the planner always uses `/discover` | Described the revised `/list` → local eligibility → bounded decision path |
| Planning and orchestration looked like separate deployed components | Explained their separate responsibilities inside the single planner service; fixed plans in Sessions 3–4 do not disable decision allocation |
| CV hot-reload instructions always edited the general evaluator | Added a selected-capability-to-file map and the need to compare the same runtime before/after |
| EVE and AGNTCY could read as vendor mentions rather than a demonstrated integration | Added a substantial adoption guide covering actual EVE calls, the course adapter, local vs portable contracts, responsibility boundaries and inspectable evidence |
| Directory comparison before adoption could fail because native EVE mode stops the registry | Explained the connection failure, optional registry-only start and persisted-card caveat |
| A successful comparison command could be mistaken for execution approval | Documented its informational result, limited hash scope and explicit false authorisation/identity fields |
| Setup links and examples were split between shell-only additions and cross-platform launchers | Linked the shared command table and added Windows commands at revised session entry points |
| Studio could display Markdown but not embedded diagrams or heading anchors | Added scoped SVG serving under the course diagrams folder, responsive images and heading IDs; retained disabled raw HTML and the filesystem boundary |

Existing walkthroughs, examples and launcher functionality are retained. No presentation changes or learner/runtime-data resets were made.

## Validation

- All **41 tests pass**, including the existing revised-course tests and new document-route checks for diagrams, heading links, disabled raw HTML and file access boundaries.
- All **136 local links** in the changed Markdown resolve to existing files.
- The six generated SVGs were rendered and visually checked for readable labels, connections and cropping.
- A temporary local Studio documentation view loaded every image in both new guides without horizontal overflow; the invocation section link scrolled to its heading. The check ran with service subscriptions disabled.
- `git diff --check` passes. No live model calls or course services were needed for this documentation check.

## Still needs the walkthrough

- Fresh Mac and Windows installation, provider access, full EVE native acceptance and Directory round trip in the learner environments.
- A timed teaching pass: inspect whether the diagrams and evidence checkpoints make the distinction between discovery, adoption and execution clear.
- Quality review of actual CV assessments, interview questions and wiki promotion judgements. Shape checks and model probabilities are not quality validation.
- Review questions and demonstration pacing in the presentation after the practical walkthrough, as already agreed.
- If adopting an externally owned agent, complete the identity, contract, access, evaluation and operating decisions listed in `sessions/session-03-eve/ADOPTION.md`; the local lab does not establish those.
