---
title: AOA wiki seed pack
source_type: course-curation
curated_from: aoa-knowledge/raw
---

# AOA Wiki Seed Pack

This folder is a small starter set for the Session 4 knowledge-management
demo. It deliberately uses Markdown only, even though the real knowledge base
contains a wider mix of source types. Markdown keeps the first ingest workflow
simple: participants can paste, drop, inspect, and re-run the same material
without format-specific parsing getting in the way.

The files are not the full `aoa-knowledge` raw archive. They are compact,
course-safe seed notes distilled from a small number of raw research files.
Each note includes provenance back to the source files in the main knowledge
repo so the course copy can be replaced or expanded later.

## Suggested ingest order

1. `01-potted-history-soa-to-agents.md`
2. `02-aoa-principles.md`
3. `03-registries-and-observed-quality.md`
4. `04-protocol-planes.md`
5. `05-real-world-implementations.md`
6. `06-scale-and-operations.md`
7. `07-standards-and-governance.md`
8. `08-adoption-action-plan.md`
9. `09-context-aware-principles.md`
10. `10-post-course-questions.md`

After ingesting these, try questions such as:

- What does AOA inherit from SOA and microservices?
- Why is the registry more than a catalogue?
- Where do A2A and MCP sit in the architecture?
- Which real-world platforms look closest to AOA?
- What failure modes does AOA inherit from microservices?
- How do we get started with AOA?
- How do we create context-aware principles for our organisation?
- When should we build a registry?
- What should we do in the first week after the course?

## Why Markdown only for now

Markdown is enough to demonstrate the important AOA behaviour:

- raw source arrives as a file
- a parser extracts structured passages
- an evaluator promotes concepts and gaps
- the wiki store persists raw, promoted, and indexed layers
- query uses the stored wiki rather than a one-off pasted note
- the graph view shows documents, concepts, passages, and open questions

Later course iterations can add PDF, HTML, transcript, and repo-snapshot
examples once the core ingest/access story is stable.
