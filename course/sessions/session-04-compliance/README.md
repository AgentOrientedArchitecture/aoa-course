# Session 4: evidence, review and recovery

Follow [`WALKTHROUGH.md`](WALKTHROUGH.md) from start to finish. It covers three
stages: check the general CV evaluator’s declaration against wiki evidence,
produce and review its held assessment, then audit what actually happened.
There is one CV evaluator and one card to edit in this session. Restart
recovery remains an optional extension in the same walkthrough.

The session uses AGNTCY to discover AUs, the wiki for cited policy evidence and
SQLite to retain the exact result awaiting review. These serve different
purposes: discovery does not approve a plan, a card declaration does not enforce
a control, and a saved review is not legal certification.

[`DURABLE-CASES.md`](DURABLE-CASES.md) is an optional reference for storage,
restart boundaries and testing repeated review requests. It is not another
walkthrough you need to complete.

## Teaching corpus

`regulations-seed/` holds one Markdown note per regulation topic (risk tiers,
Annex III employment, Articles 9–14, 26, and 72) with a matching
`.promotion.json` file per note so the seed script can load the corpus
deterministically, without a model in the loop.

After `session4-up`, `./scripts/session4-seed.sh` (or
`scripts\session4-seed.bat` on Windows) loads and verifies the corpus with
Annex III employment and Article 14 human-oversight queries. Wiki reset is
disabled in Session 4; if evidence is missing, rerun the seed script. The corpus
supports a bounded teaching policy; it is not a complete or continuously updated
legal source.

Session 4 reuses the Session 1 CV and job-description examples in
[`../session-01-cv-fit/`](../session-01-cv-fit/) for the **CV fit** stage.
