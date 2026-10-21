# Compliance: a case that survives restart

Start `./scripts/revised-up.sh 4`, then run the existing `./scripts/session4-seed.sh`. Follow the [original three-stage walkthrough](WALKTHROUGH.md): card check, CV fit with exact-result review, then flow audit. Its final paragraph about in-memory drafts applies to the original profile. In this revised profile, the saved case and its event log are durable.

The specialist evaluators also start without the required review-before-use declaration. Inspect which evaluator the planner selected. Add the existing declaration to that evaluator's capability card before expecting the employment policy to proceed. A declaration is still only evidence of the declared constraint.

## Stop between execution and approval

1. Run the card check and observe the original red result. Submit CV fit and confirm rejection before application execution.
2. Add the declaration from the original walkthrough to the selected evaluator's card. Wait for its hot reload. Rerun CV fit and inspect the held draft, plan digest and result digest.
3. Record the trace ID and result digest. Restart only the planner with `docker restart aoa-planner`.
4. Refresh Studio and select **Open a saved case**. Reopen that trace. Compare the digest and exact draft; no CV processing should run again.
5. Add notes and approve or reject. Approval releases the same draft; rejection quarantines it.
6. Repeat the identical review request. It must return the recorded result without adding another release. A changed digest or conflicting review must fail.
7. Run **Flow audit** and inspect event order, payload equality and the cited governance evidence.

The saved object contains the intent, frozen plan and cards, governance result, held output, digest, review and final state. SQLite commits draft+hold together, and review+release/quarantine+finish together. JSONL is a regenerable projection for the original flow-audit tools.

If the process stops during an external invocation, the case is marked interrupted. It is not automatically rerun: the outside effect may already have happened. This course does not add retry machinery for arbitrary effects or claim exactly-once delivery.

## Review questions

- Why is remembering the conversation insufficient to recover this business case?
- What must approval refer to if a model can generate a different answer on another run?
- What happens if the client retries approval after losing the response?
- If an AU sends an email before the hold, can result quarantine undo it?
- Which parts of this local design would a production durable-object or workflow platform have to supply?

This is a local case-state demonstration, not a deployment of Cloudflare Durable Objects or a replacement for the existing compliance policy. The existing regulation corpus is retained; legal currency and effective oversight require their own review before production use.
