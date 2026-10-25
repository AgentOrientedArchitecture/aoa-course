# Session 2: wiki examples

Starter material for the AOA knowledge-management workflow. Follow the
[Session 2 walkthrough](WALKTHROUGH.md) for one sequence covering startup,
promotion decisions, graph inspection and cited answers. This page lists
inputs and optional API examples; [DECISIONS.md](DECISIONS.md) is optional
background.

- `wiki-seed/` contains the curated Markdown seed pack for building the wiki.
- `quickstart-note/` contains a short relevant note for a faster first ingest,
  plus `not-for-wiki-fairytale.txt` for demonstrating evaluator rejection.

In Studio, ingest files one at a time and check whether each was promoted,
rejected or held for review. Then ask questions against the stored passages.
The wiki persists between restarts; rejected and review outcomes do not add
content to it.

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

## Optional: call the planner directly

With Session 2 running, copy the input note into `system/inbox/` in this
checkout. Docker mounts that folder as `/data/inbox/` for the services. These
are Bash examples; Studio supplies the same workflow inputs through its forms.

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

Check the ingest result before querying: a withheld note is not queryable wiki
content. A file path must name a document visible inside the container; an
arbitrary laptop path is not accessible to the AU.
