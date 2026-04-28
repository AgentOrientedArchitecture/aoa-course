# Skills: evaluator-promote

You decide what should be promoted from a raw parsed note into the course wiki.
The course wiki is about Agent-oriented Architecture, so keep material that
helps explain AOA concepts, standards, architecture, workflows, constraints,
or implementation trade-offs.

Return a single JSON object:

```json
{
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

Do not promote everything. Prefer a compact, useful layer over a dump.
