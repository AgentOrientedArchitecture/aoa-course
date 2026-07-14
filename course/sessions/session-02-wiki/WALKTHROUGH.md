# Session 2 walkthrough — the same shape becomes a knowledge system

No new architecture: the ingest and query workflows reuse the pattern from
Session 1 (parse → judge → report), and the `wiki-parser` runtime runs the
**same parser code** as `cv-parser` — different capability card, different
`instructions.md`, different Agent ID. That move is the session. ~20 minutes.

## 1. Start the stack

```bash
./scripts/session2-up.sh
```

Open [http://localhost:8080](http://localhost:8080). The Registry pane now
shows both parser runtimes. Compare `parser-cv` and `parser-notes`: same
codebase underneath, two governed agents with different public promises.

## 2. Ingest — promotion is judgement

In the **Ingest** tab, submit
`course/sessions/session-02-wiki/quickstart-note/agent-registry-lessons.txt`.

Watch the trace: `parser-notes` extracts structured passages,
`evaluator-promote` decides what deserves promotion (a judgement, not a copy),
and `reporter-ingest-summary` writes the accepted material to the wiki store
through `tool-wiki-store`.

Now submit `quickstart-note/not-for-wiki-fairytale.txt`. The evaluator
**rejects** it (`promote=false`) — the pipeline exercises judgement at a
declared boundary rather than swallowing everything. Rejection is a feature.

Then ingest a few files from `wiki-seed/` to give the wiki some depth.

## 3. Graph — what the system now knows

Switch to the **Graph** tab. The nodes and edges are a projection of
`system/wiki/index.json`: documents, concepts, passages, open questions, and
typed relationships. Nothing is hidden in an embedding — you can read every
edge back to a stored passage.

## 4. Ask — grounded answering with citations

In the **Ask** tab, ask something the wiki covers, e.g.:

> What did the registry lessons note say about observed quality?

The trace shows `parser-query` compacting the question, `evaluator-wiki-query`
searching the store and ranking passages deterministically, and
`reporter-answer` writing an answer **only from retrieved passages**, with
passage-id citations and declared gaps. Ask something the wiki does not cover
and watch it say so instead of inventing an answer — grounding means the
system knows what it doesn't know.

## What to take away

- Same architectural shape, different domain: describe → discover → compose →
  execute → observe held without modification.
- One codebase became a second governed agent through configuration: card +
  instructions + Agent ID. Replacement is registration, at the agent layer.
- Promotion-as-judgement and cited answering are the governance story for
  knowledge: what enters the store is decided, and what leaves it is traceable.
- Session 4 reuses this exact pipeline to hold a **regulations corpus** — the
  wiki you just built is how the governance checks' citations stay current.
