# Course sessions

One folder per hands-on session. Each folder follows the same layout:

- **`WALKTHROUGH.md`** — the learner instructions for the session. Start here.
- **`README.md`** — describes the session's example data and how to feed it in.
- Data subfolders (CVs, wiki seed notes, regulations seed, …) used by the
  walkthrough.

All CV/JD examples are synthetic; none of the people or companies are real.
The wiki seed notes are curated course copies distilled from the main
`aoa-knowledge` raw archive.

| Session | Folder | What you do |
| --- | --- | --- |
| 1 — CV fit | [`session-01-cv-fit/`](session-01-cv-fit/WALKTHROUGH.md) | Build and inspect the three-AU CV-fit workflow, then modify a live agent and watch it re-register. |
| 2 — Wiki | [`session-02-wiki/`](session-02-wiki/WALKTHROUGH.md) | The same shape becomes a knowledge-management workflow: ingest, promote, graph, ask. |
| 3 — EVE | [`session-03-eve/`](session-03-eve/WALKTHROUGH.md) | Author an agent natively in EVE, accept it, then adopt it into the AOA registry, planner, and Studio. |
| 4 — Compliance | [`session-04-compliance/`](session-04-compliance/WALKTHROUGH.md) | Agent card check, CV fit to a held result with human review, and flow audit against the EU AI Act corpus. |

Start each session with its start script from the repo root
(`./scripts/session1-up.sh` … `./scripts/session4-up.sh`, with `.bat`
equivalents for Windows); the walkthroughs give the exact sequence.
