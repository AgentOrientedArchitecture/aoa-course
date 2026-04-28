# Course data

Synthetic CVs, job descriptions, and starter knowledge notes used in the
course walkthroughs. None of the people or companies in the CV/JD examples are
real. The wiki seed notes are curated course copies distilled from the main
`aoa-knowledge` raw archive.

## Pairings

The walkthrough uses two contrasting pairs so you can see the evaluator and
reporter behave differently when fit is strong vs weak.

| CV | JD | Expected verdict |
| --- | --- | --- |
| `cv-examples/jordan-okafor.txt`  | `jd-examples/senior-data-engineer-fintech.txt`     | strong / fit |
| `cv-examples/sam-everett.txt`    | `jd-examples/frontend-engineer-design-systems.txt` | fit          |
| `cv-examples/jordan-okafor.txt`  | `jd-examples/frontend-engineer-design-systems.txt` | weak / no    |
| `cv-examples/sam-everett.txt`    | `jd-examples/senior-data-engineer-fintech.txt`     | weak / no    |

## How to use

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

## Session 4 wiki ingest and query

Use the Studio in two passes:

1. `Ingest`: paste or drop one of the seed wiki notes.
2. `Ask`: ask a question against the wiki that has now been built.

The starter pack is in `wiki-seed/`:

| File | Purpose |
| --- | --- |
| `wiki-seed/01-potted-history-soa-to-agents.md` | A short lineage from SOA and microservices to AOA. |
| `wiki-seed/02-aoa-principles.md` | Four working principles: decompose, compose, substitute, trust. |
| `wiki-seed/03-registries-and-observed-quality.md` | Registry shapes and the observed-over-claimed argument. |
| `wiki-seed/04-protocol-planes.md` | Where A2A, MCP, REST, workflow specs, and observability standards fit. |
| `wiki-seed/05-real-world-implementations.md` | Vendor/platform anchors for Session 3 and Session 4. |
| `wiki-seed/06-scale-and-operations.md` | Failure modes, runtime controls, and platform-team responsibilities. |
| `wiki-seed/07-standards-and-governance.md` | Standards, governance, identity, audit, and compliance framing. |

Example:

| Ingest note | Ask after ingest |
| --- | --- |
| `wiki-seed/03-registries-and-observed-quality.md` | Why is observed behaviour more important than self-reported metadata? |
| `wiki-seed/04-protocol-planes.md` | Where do A2A and MCP sit in AOA? |
| `wiki-seed/05-real-world-implementations.md` | Which real-world platforms look closest to AOA? |

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
