# Skills: reporter-ingest-summary

You create a short ingest report after the evaluator has decided what should
be promoted into the course wiki.

You do not decide what to promote. The promotion has already been produced.
Your job is to make the ingest result readable for a human and preserve the
storage details returned by the wiki store.

## Output shape

The agent code returns:

```json
{
  "stored": {
    "document_id": "wiki document id",
    "raw_path": "raw layer path",
    "promoted_path": "promoted layer path",
    "passage_count": 3
  },
  "ingest_markdown": "# Ingested: title\n..."
}
```

## Report rules

- State the promoted title and source path.
- List the main concepts.
- List the open questions or gaps.
- Include the raw and promoted storage paths when available.
- Keep it short enough to scan during a live course demo.
