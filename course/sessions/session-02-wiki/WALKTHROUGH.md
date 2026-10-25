# Session 2: curate and query a wiki

Use the same parse → judge → report pattern to curate knowledge. This session
adds a second use of a decision model: the judgement is now the main output of
an AU. You will compare accepted, rejected and uncertain material, inspect what
was stored, then ask questions against the retained passages. Allow about
30 minutes, depending on model speed and how many seed files you ingest.

This page contains the whole session. The input files and optional API examples
are listed in [README.md](README.md).

![Note extraction, bounded promotion decision and conditional publication](../../diagrams/wiki-decision.svg)

## 1. Start and compare the agents

Use the `.env` created during [course setup](../../pre-work/SETUP.md). Run from
the repository root:

| Platform | Start Session 2 |
|---|---|
| macOS/Linux | `./scripts/session2-up.sh` |
| Windows Command Prompt | `scripts\session2-up.bat` |

Open [Studio](http://localhost:8080), then **Capability cards**. Compare
`parser-cv` and `parser-notes` in **Readable** and **Complete JSON**. Their
`cv-parser` and `wiki-parser` runtimes share the same parser code, but have
different capability cards, instructions and Agent IDs. One codebase supports
two governed agents with different public promises.

Session 2 continues to use the local registry. In addition to the CV workflow,
it provides these two paths:

```text
Ingest: parser-notes → evaluator-promote → reporter-ingest-summary
Ask:    parser-query → evaluator-wiki-query → reporter-answer
```

Ingest uses the generation model to extract a note, then the decision service
to choose `promote`, `reject` or `review`. Code assembles the promotion output
from parsed fields. The reporter calls `tool-wiki-store` only when promotion
is true. This is distinct from Session 1's choice of which AU should run.

## 2. Ingest a relevant note

Return to **Studio · all controls** and choose **Ingest**. Drop this file into
**Source material**, or paste its contents:

`course/sessions/session-02-wiki/quickstart-note/agent-registry-lessons.txt`

Predict whether the note supplies useful AOA material, then choose
**Run ingest**. Follow the trace through parsing, promotion and
reporting. Open **Run review** and select each output:

1. **Parser:** inspect its summary, concepts and extracted passage quotes.
   Compare at least one quote against the original note.
2. **Promotion evaluator:** open **Complete output JSON** and inspect
   `promotion.decision_outcome`, `promotion.promote`, retained passages and
   `promotion.decision_evidence`.
3. **Reporter:** inspect `stored`, the passage count and the ingest summary.
   A successful promotion should show a stored document; a withheld decision
   should show `stored.skipped=true`.

For a more compact decision view, return to **Studio · all controls**, find
**Plan and decisions**, and expand **Full allocation and promotion evidence**.
The **Wiki promotion** entry shows the returned decision and available
provider, model, latency, usage and probability evidence.

A `promote` decision is an observation to inspect, not proof that the source
is true. The code preserves quotes received from the parser; it does not prove
that the parser copied the original accurately. If the first note is withheld,
inspect the decision evidence and any provider error before continuing.

## 3. Compare rejection and uncertainty

Run two more inputs through **Ingest**:

| Input | Prediction to test |
|---|---|
| `quickstart-note/not-for-wiki-fairytale.txt` | Fiction unrelated to the wiki should be rejected. |
| The short claim below | Insufficient evidence should lead to review or rejection. |

The file path is within this session's directory. Paste this for the third run:

> Someone said the new agent system cut costs dramatically. No figures, method, dates or source were supplied.

Record the actual outcome for each. These are discussion expectations, not
fixed model answers. If irrelevant or unsupported content is promoted, inspect
that as a failure rather than treating a typed response as proof of correctness.

For a `reject` or `review` outcome, verify `promotion.promote=false` and the
reporter's `stored.skipped=true`. No `write_ingest` call should have been made
for that run. If you later inspect the graph, distinguish existing nodes from
new content; earlier ingests remain on disk.

The caller changes a low-probability choice to `review`. A `promote` choice
without usable passages also becomes `review`. The configured probability
threshold is an illustrative policy, not calibrated accuracy. The local
Ollama baseline supplies no probability and runs only when the configuration
explicitly permits unscored choices.

Review material stays in the recorded run and is withheld from publication.
There is no separate editorial approval queue in this exercise. You can edit
an input and submit a new ingest; that is a new run, not approval of the old one.

## 4. Add depth and inspect the graph

Ingest a few files from `course/sessions/session-02-wiki/wiki-seed/`, one at a
time. Start with:

- `03-registries-and-observed-quality.md`
- `04-protocol-planes.md`
- `02-aoa-principles.md`

Inspect each promotion result before assuming that its content is available.
The [seed-pack table](README.md#seed-pack) describes the remaining examples,
including implementation, operations and adoption material. These are selected
April research snapshots, not a complete account of the current course. They
do not contain the TypeSafe or persistent-case lessons. A question on those
topics should expose a corpus gap, not draw an answer from the model’s memory.
The protocol note describes model-driven AUs; this course also includes a
deterministic governance AU. AU responsibility and contract define the boundary,
not a requirement that every implementation call a model.

Choose **Graph**. The nodes and edges project the stored
`system/wiki/index.json`: documents, concepts, passages, open questions and
typed relationships. This is inspectable stored structure, not an embedding
visualisation. Compare a passage with its source document and read the
associated relationships. Visibility makes the structure reviewable; it does
not establish that every extracted relationship is correct.

The wiki persists when you stop or restart the course. **Reset wiki** removes
stored content and is not required for this session. Keep your earlier ingests
unless you deliberately want a new wiki.

## 5. Ask using retrieved evidence

Choose **Ask** and enter:

> What did the registry lessons note say about observed quality?

Choose **Ask wiki**. In the trace and **Run review**, inspect:

1. `parser-query`: the structured query derived from your question.
2. `evaluator-wiki-query`: the `tool-wiki-store` search and ranked passages.
3. `reporter-answer`: the answer, passage-ID citations and declared gaps.

The final answer is assembled deterministically from retrieved passages; it
is not a fresh model-written answer from general knowledge. Compare each
citation with the retrieved passage and the source note. Retrieval relevance
and source fidelity still need checking.

Try another question from the [ingest/ask pairs](README.md#example-ingestask-pairs),
then ask something your wiki does not cover. With no usable retrieved evidence,
the reporter returns an explicit insufficient-evidence answer. If it retrieves
tangential passages instead, inspect their relevance and any declared gaps;
citations alone do not make an answer sufficient.

## Review and finish

- Which parts of the ingest still need generation, and which have a bounded
  decision as their main output?
- What is the cost of a false promotion compared with an unnecessary review?
- Does probability over three choices tell you whether the source is true?
- Which boundary prevents `review` and `reject` from becoming published wiki
  content?
- What would you measure before using this policy on a production knowledge
  pipeline: source fidelity, promotion errors, retrieval quality or something
  else?
- What changed between the CV parser and the note parser, and what was reused?

The architecture remains recognisable: describe capabilities, discover AUs,
compose the work, execute and observe. Knowledge curation adds a decision about
what enters the store and a traceable evidence path for what leaves it. Session
4 uses the same wiki mechanisms for a supplied regulations corpus.

Stop with `./scripts/down.sh` or `scripts\down.bat`, retaining your wiki and
recorded runs. Continue with the [Session 3 walkthrough](../session-03-eve/WALKTHROUGH.md).
The [promotion reference](DECISIONS.md) is optional background.
