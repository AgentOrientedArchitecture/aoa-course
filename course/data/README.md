# Course data

Synthetic CVs, job descriptions, and starter knowledge notes used in the
course walkthroughs. None of the people or companies in the CV/JD examples are
real. The wiki seed notes are curated course copies distilled from the main
`aoa-knowledge` raw archive.

## Layout

| Folder | Used by | Contents |
| --- | --- | --- |
| `session-02-cv-fit/` | Session 2 | Synthetic CVs and job descriptions. |
| `session-04-wiki/` | Session 4 | AOA wiki seed notes and quickstart note for ingest/query. |

## Session 2 CV Fit

The walkthrough uses two contrasting pairs so you can see the evaluator and
reporter behave differently when fit is strong vs weak.

| CV | JD | Expected verdict |
| --- | --- | --- |
| `session-02-cv-fit/cv-examples/jordan-okafor.txt` | `session-02-cv-fit/jd-examples/senior-data-engineer-fintech.txt` | strong / fit |
| `session-02-cv-fit/cv-examples/sam-everett.txt` | `session-02-cv-fit/jd-examples/frontend-engineer-design-systems.txt` | fit |
| `session-02-cv-fit/cv-examples/jordan-okafor.txt` | `session-02-cv-fit/jd-examples/frontend-engineer-design-systems.txt` | weak / no |
| `session-02-cv-fit/cv-examples/sam-everett.txt` | `session-02-cv-fit/jd-examples/senior-data-engineer-fintech.txt` | weak / no |

### How to use

In the studio, drop a CV into the CV slot and a JD into the JD slot, then
hit submit. The studio writes both to the shared inbox volume and submits
their paths to the planner.

Or, if you'd rather drive the planner directly:

```bash
curl -s http://localhost:7200/intent \
  -H 'content-type: application/json' \
  -d '{
    "kind": "cv-fit",
    "inputs": {
      "cv_path": "/data/inbox/jordan-okafor.txt",
      "jd_path": "/data/inbox/senior-data-engineer-fintech.txt"
    }
  }'
```

(With files of those names placed in the `inbox` volume by hand.)

## Session 4 Wiki Ingest and Query

Use the Studio in two passes:

1. `Ingest`: paste or drop one of the seed wiki notes.
2. `Ask`: ask a question against the wiki that has now been built.

The starter pack is in `session-04-wiki/wiki-seed/`:

| File | Purpose |
| --- | --- |
| `session-04-wiki/wiki-seed/01-potted-history-soa-to-agents.md` | A short lineage from SOA and microservices to AOA. |
| `session-04-wiki/wiki-seed/02-aoa-principles.md` | Four working principles: decompose, compose, substitute, trust. |
| `session-04-wiki/wiki-seed/03-registries-and-observed-quality.md` | Registry shapes and the observed-over-claimed argument. |
| `session-04-wiki/wiki-seed/04-protocol-planes.md` | Where A2A, MCP, REST, workflow specs, and observability standards fit. |
| `session-04-wiki/wiki-seed/05-real-world-implementations.md` | Vendor/platform anchors for Session 3 and Session 4. |
| `session-04-wiki/wiki-seed/06-scale-and-operations.md` | Failure modes, runtime controls, and platform-team responsibilities. |
| `session-04-wiki/wiki-seed/07-standards-and-governance.md` | Standards, governance, identity, audit, and compliance framing. |

For a very short first run, use
`session-04-wiki/quickstart-note/agent-registry-lessons.txt`.

Example:

| Ingest note | Ask after ingest |
| --- | --- |
| `session-04-wiki/wiki-seed/03-registries-and-observed-quality.md` | Why is observed behaviour more important than self-reported metadata? |
| `session-04-wiki/wiki-seed/04-protocol-planes.md` | Where do A2A and MCP sit in AOA? |
| `session-04-wiki/wiki-seed/05-real-world-implementations.md` | Which real-world platforms look closest to AOA? |

Direct planner invocation for ingest:

```bash
curl -s http://localhost:7200/intent \
  -H 'content-type: application/json' \
  -d '{
    "kind": "knowledge-ingest",
    "inputs": {
      "note_path": "/data/inbox/03-registries-and-observed-quality.md"
    }
  }'
```

Direct planner invocation for query:

```bash
curl -s http://localhost:7200/intent \
  -H 'content-type: application/json' \
  -d '{
    "kind": "knowledge-query",
    "inputs": {
      "question": "Why is observed behaviour more important than self-reported metadata?"
    }
  }'
```

(With files placed in the `inbox` volume by hand, or written there by the
Studio after paste/drop.)
