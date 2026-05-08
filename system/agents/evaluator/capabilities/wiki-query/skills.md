# Skills: evaluator-wiki-query

This capability evaluates retrieved wiki passages against a user question.

In the reference implementation the ranking is deterministic, not model
written: `agent.py` asks `tool-wiki-store` for passages, keeps the returned
passage ids, converts retrieval scores into 1-5 relevance values, and records
whether there is enough evidence for a direct answer. This keeps Session 4
focused on grounded retrieval rather than model prior knowledge.

You receive:

- the original question
- the parsed retrieval query
- candidate passages returned by the wiki store

The returned JSON object has this shape:

```json
{
  "ranked_passages": [
    {
      "passage_id": "id from retrieved passage",
      "relevance": 1,
      "reason": "why this passage helps or does not help"
    }
  ],
  "direct_answer_possible": true,
  "gaps": ["what the wiki does not yet contain"],
  "rationale": "short explanation of evidence quality"
}
```

Relevance is 1 to 5. The capability uses only passage ids returned by the wiki
store. If the wiki store has no useful passages, `direct_answer_possible` is
false and the gap is named.
