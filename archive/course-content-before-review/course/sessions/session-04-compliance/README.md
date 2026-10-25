# Session 4 Compliance Data

Curated EU AI Act corpus for the governance/evidence knowledge plane.
The learner instructions are in [`WALKTHROUGH.md`](WALKTHROUGH.md).

`regulations-seed/` holds one Markdown note per regulation topic (risk tiers,
Annex III employment, Articles 9–14, 26, and 72) with a matching
`.promotion.json` file per note so the seed script can load the corpus
deterministically, without a model in the loop.

The seed is loaded by `./scripts/session4-seed.sh` (or
`scripts\session4-seed.bat` on Windows) after `session4-up`, which then
verifies the wiki with searches for `Annex III employment` and
`Article 14 human oversight`. Wiki reset is disabled in Session 4 to protect
this governance corpus; if evidence is missing, rerun the seed script.

Session 4 reuses the Session 1 CV and job-description examples in
[`../session-01-cv-fit/`](../session-01-cv-fit/) for the **CV fit** stage.
