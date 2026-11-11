# Local oMLX model checks — 5 November 2026

**API compatibility checked; full course and EVE not rehearsed with this pair.**

The [local example](../../../.env.local.example) uses oMLX 0.7.3 on the Mac,
`Qwen3.8-Flash-Next-oQ3.5e-mtp` for generation and `d1-2B-MLX-8bit` for decisions.
A disposable course container reached both through `host.docker.internal:8000`.
The running course services and active `.env` were not changed.

The real generation adapter returned the required `{"ok":true}` JSON in 1.199
seconds. This small smoke request does not test extraction, planning or EVE.

The [decision evidence](decision-check.json) records six synthetic cases through
the actual allocation, promotion and native decision callers. All six responses
validated; four met the hand-authored choice and caller-outcome expectations.

| Case | Choice and winning probability | Caller outcome |
|---|---|---|
| Data evaluator | `evaluator-cv-data`, 0.5442 | Held below 0.65; no AU accepted |
| Frontend evaluator | `evaluator-cv`, 0.6685 | General evaluator accepted; expected frontend specialist |
| No suitable AU | `no_suitable_capability`, 0.9881 | No AU accepted, as expected |
| Relevant wiki note | `promote`, 0.7144 | Promoted, as expected |
| Fiction | `reject`, 0.9954 | Rejected, as expected |
| Unsupported claim | `reject`, 0.6150 | Held for review, an allowed expected outcome |

Observed decision calls took 30–91 ms, median 60 ms. This was one pass with six
small inputs, not a throughput benchmark or calibration study. The 0.65 gate
and prohibition on unscored acceptance were unchanged. No application AU ran
and no wiki content was published during the decision probe.

The test helper now records an unavailable Git revision when Git is absent in
a course container; its source hashes still identify the implementation tested.
Prior full-course local findings remain in the [25 October record](../2026-10-25-local-course/README.md).
