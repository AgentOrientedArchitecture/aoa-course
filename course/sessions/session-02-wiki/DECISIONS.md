# Wiki promotion reference

Optional background for [Session 2](WALKTHROUGH.md). The walkthrough contains
the ingest comparisons, graph inspection, grounded queries and review questions.

## A decision as the AU's main output

Session 1 used a decision model to allocate a task to an eligible AU. Here
`evaluator-promote` uses the decision model to fulfil its own responsibility:
should this note enter the wiki? Its bounded output is `promote`, `reject` or
`review`.

![Extraction, decision and conditional publication](../../diagrams/wiki-decision.svg)

The parser still needs generation to extract the note's fields. The promotion
code sends those fields, the source path and the promotion rubric to the
decision service. It then constructs the existing promotion contract from
the parsed content, without asking the model for another paraphrase.

## Decisions and publication

| Returned evidence | Effective outcome | Store behaviour |
|---|---|---|
| Accepted `promote` with usable passages | `promote` | Reporter calls `write_ingest`. |
| Accepted `reject` | `reject` | Reporter records `stored.skipped=true`; no store write. |
| `review` | `review` | Same withholding behaviour; no editorial approval queue. |
| Probability below the configured threshold | `review` | Withheld, even if the returned choice was `promote`. |
| `promote` without usable passages | `review` | Withheld. |
| No probability and unscored decisions disallowed | `review` | Withheld. |

A provider error or unknown choice fails the AU invocation. It is not a
successful `review` decision. Inspect the trace rather than interpreting all
missing wiki content as model rejection.

`promotion.decision_evidence` retains the service response, including provider,
model, latency and available usage/probability evidence. `decision_outcome`
records the effective outcome after the caller's checks. Compare both when
explaining why a note was withheld.

## What still needs evaluation

The probability threshold is a teaching policy, not a calibrated quality
claim. The local Ollama route has no probability estimate; its explicitly
unscored policy differs from the hosted TypeSafe route. In either case,
structured output can still be wrong.

Retained quotes match the parser's output. That is useful provenance but does
not prove the parser copied the source correctly. Compare the quote with the
original note, then separately assess relevance, source reliability and the
cost of false promotion or unnecessary review.

The reporter's query answers use retrieved passages deterministically. That
limits unsupported generation at the final step, but does not repair a bad
source, extraction error or irrelevant retrieval. Trace citations back to
source text before treating an answer as supported.

The [course architecture guide](../../ARCHITECTURE.md#session-2-the-decision-is-the-aus-main-model-output)
shows the boundaries between parser, decision service, promotion AU, reporter
and wiki tool.
