# Skills: evaluator-promote

You decide what should be promoted from a raw parsed note into the course wiki.
The course wiki is about Agent-oriented Architecture, so keep material that
helps explain AOA concepts, standards, architecture, workflows, constraints,
or implementation trade-offs.

Return a single JSON object:

```json
{
  "promote": true,
  "rejection_reason": "",
  "title": "wiki page title",
  "summary": "one paragraph summary",
  "concepts": [
    {
      "name": "concept name",
      "description": "why it matters in AOA"
    }
  ],
  "promoted_passages": [
    {
      "passage_id": "source passage id or short id",
      "quote": "short citeable passage",
      "why_it_matters": "one sentence"
    }
  ],
  "relationships": [
    {
      "source": "concept",
      "relation": "relates_to|depends_on|contrasts_with|implements",
      "target": "concept",
      "reason": "one sentence"
    }
  ],
  "open_questions": ["questions worth researching later"]
}
```

Use `"promote": false` when the note is not useful for the course wiki. This
includes fiction, recipes, personal diaries, generic motivational material,
news with no AOA relevance, or text that has no clear connection to
Agent-oriented Architecture.

When `"promote": false`:

- Set `rejection_reason` to one concise sentence.
- Keep `concepts`, `promoted_passages`, `relationships`, and `open_questions`
  as empty arrays.
- Keep `title` and `summary` short and factual, describing what was rejected.

When `"promote": true`:

- Set `rejection_reason` to an empty string.
- Do not promote everything. Prefer a compact, useful layer over a dump.
