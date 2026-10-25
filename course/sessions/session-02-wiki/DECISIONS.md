# Wiki: a decision inside the AU

Start `./scripts/session2-up.sh`, or `scripts\session2-up.bat`, with `.env` configured. Retain the original [wiki walkthrough](WALKTHROUGH.md), including ingest, graph, retrieval and citations. The [wiki architecture diagram](../../ARCHITECTURE.md#session-2-the-decision-is-the-aus-main-model-output) shows which component supplies the judgement and which one writes the result.

The parser still uses the generation model to extract the note. The promotion AU now asks a bounded question: **promote, reject, or review**. The decision model supplies the judgement; code assembles the existing promotion contract from parsed fields and preserves each retained quote. The reporter writes to the wiki only when `promote` is true.

## Compare three inputs

1. Use `quickstart-note/agent-registry-lessons.txt`. Predict whether its architecture content warrants promotion. Inspect the returned decision and retained passages.
2. Use `quickstart-note/not-for-wiki-fairytale.txt`. Verify that an irrelevant source does not create wiki content.
3. Enter: “Someone said the new agent system cut costs dramatically. No figures, method, dates or source were supplied.” Predict whether the result should be review or reject. Inspect what actually happens; the expected label is a discussion rubric, not a guaranteed model answer.

The Studio exposes decision provenance, latency, usage and probability when the provider supplies it. Low probability becomes review; a promote decision without usable passages also becomes review. Review items are withheld in the trace, not automatically published. A full editorial approval queue is outside this exercise.

A preserved parser quote is not proof that the parser copied it correctly from the original. Compare the displayed quote with the raw note. The lesson includes source fidelity and evaluation, rather than claiming the decision model solves extraction errors.

## Review questions

- Which parts of this AU still need generation, and which now have a bounded output?
- What is the cost of a false promotion compared with an unnecessary review?
- Does confidence over three choices tell us whether the source itself is true?
- What would you measure before moving this policy into a production knowledge pipeline?
