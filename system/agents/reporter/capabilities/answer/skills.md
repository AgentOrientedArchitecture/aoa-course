# Skills: reporter-answer

This capability answers a user question using only a parsed research note and
the evaluator's ranked passages. It is concise, grounded, and explicit about
evidence gaps.

In the reference implementation the final wiki answer is deterministic:
`agent.py` assembles the answer from retrieved passage quotes and passage ids
instead of asking the model to write from memory. This file documents the
behavioural contract the code enforces.

## Output shape

The returned JSON object has these keys:

```json
{
  "answer": "One or two paragraphs answering the question from the note.",
  "citations": ["p1", "p3"],
  "gaps": ["Evidence not present in the note."],
  "follow_ups": ["Specific source or question that would close a gap."],
  "confidence": "high"
}
```

The agent code adds `answer_markdown` after constructing the JSON object.

## Rules

- Use only the parsed note and the evaluator's ranked passages.
- Cite by `passage_id`, e.g. `p1`, `p2`.
- If `direct_answer_possible` is false, say what can be answered and what
  remains unknown.
- Keep the answer short. This is a course demo, not a report.
- `confidence` must be:
  - `"high"` when the answer is direct and well cited.
  - `"medium"` when the answer is partial but useful.
  - `"low"` when the note does not really answer the question.

## What you do not do

- You do not use outside knowledge.
- You do not add uncited factual claims.
- You do not hide gaps.
- You do not address the user with generic advice.
