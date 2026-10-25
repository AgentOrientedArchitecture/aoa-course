# Preserved course content

These are exact copies of the course documents before the content review on
25 October 2026, from commit `eeeb33e307594ecf99093b01e68cd567cad3dd0a`.
Their original relative paths are retained. The unused `env.ollama-cloud` preset
is also preserved here; fresh setups use the single root `.env.example`. They preserve the earlier explanations,
exercises and validation history; they are not a second course to follow.

For the current learner route, use [the course overview](../../course/COURSE.md),
[setup](../../course/pre-work/SETUP.md) and each session's `WALKTHROUGH.md`.
Architecture and manual-command documents remain available as optional references.

## Updating an older installation

Fresh checkouts use only `.env`. For compatibility, the launchers still read an
existing private `.env.revised` after `.env`; its values override `.env`.
Exported terminal variables override both. If an older installation behaves
unexpectedly, inspect these sources privately. Consolidate the intended settings
into `.env` and keep any old file outside the checkout as a backup before removing
that overlay. Never paste keys into chat or commit either private file.

Earlier configuration files and launchers are preserved separately in
[configuration-before-consolidation](../configuration-before-consolidation/README.md).
The optional legacy reset script clears only JSONL projections, not the authoritative
SQLite case store, and does not produce a clean current-course baseline. Use the
normal stop command and a separate fresh checkout when you need an isolated rehearsal.
