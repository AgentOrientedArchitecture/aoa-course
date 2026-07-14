# Session 2 Wiki Data

Starter material for the AOA knowledge-management workflow.
The learner instructions are in [`WALKTHROUGH.md`](WALKTHROUGH.md).

- `wiki-seed/` contains the curated Markdown seed pack for building the wiki.
- `quickstart-note/` contains a short relevant note for a faster first ingest,
  plus `not-for-wiki-fairytale.txt` for demonstrating evaluator rejection.

In the Studio, ingest one or more files first, then ask questions against the
built wiki.

The seed pack includes both AOA background material and a small post-course
action kit: an adoption plan, a context-aware principles workshop, and a
short FAQ for common "how do we start?" questions.

## Seed pack

| File | Purpose |
| --- | --- |
| `wiki-seed/01-potted-history-soa-to-agents.md` | A short lineage from SOA and microservices to AOA. |
| `wiki-seed/02-aoa-principles.md` | Four working principles: decompose, compose, substitute, trust. |
| `wiki-seed/03-registries-and-observed-quality.md` | Registry shapes and the observed-over-claimed argument. |
| `wiki-seed/04-protocol-planes.md` | Where A2A, MCP, REST, workflow specs, and observability standards fit. |
| `wiki-seed/05-real-world-implementations.md` | Vendor/platform anchors for Session 2 and Session 3. |
| `wiki-seed/06-scale-and-operations.md` | Failure modes, runtime controls, and platform-team responsibilities. |
| `wiki-seed/07-standards-and-governance.md` | Standards, governance, identity, audit, and compliance framing. |
| `wiki-seed/08-adoption-action-plan.md` | Post-course adoption plan. |
| `wiki-seed/09-context-aware-principles.md` | Context-aware principles workshop. |
| `wiki-seed/10-post-course-questions.md` | FAQ for common "how do we start?" questions. |

For a very short first run, use `quickstart-note/agent-registry-lessons.txt`.

## Example ingest/ask pairs

| Ingest note | Ask after ingest |
| --- | --- |
| `wiki-seed/03-registries-and-observed-quality.md` | Why is observed behaviour more important than self-reported metadata? |
| `wiki-seed/04-protocol-planes.md` | Where do A2A and MCP sit in AOA? |
| `wiki-seed/05-real-world-implementations.md` | Which real-world platforms look closest to AOA? |

## Direct planner invocation

Ingest:

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

Query:

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
