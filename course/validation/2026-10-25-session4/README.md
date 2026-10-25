# Session 4 rehearsal — 25 October 2026

The simplified governance exercise completed on the Mac using the real
AGNTCY Directory, wiki store and Cerebras `gpt-oss-120b`. Session 4 exposes one
CV evaluator, so its allocation used contract checks without a decision-model
call. TypeSafe settings remain available for the earlier sessions.

## What was exercised

| Check | Observed outcome |
|---|---|
| Start and seed | Fourteen isolated services started. Twelve AU records were published and verified in Directory. Ten regulation notes were loaded; both required governance queries returned passage IDs and sources. |
| Missing declaration | Agent card check reported `evaluator-cv` red for Article 14. CV governance retrieved wiki evidence, rejected the plan and invoked no application AU. |
| One card edit and sync | The saved review declaration appeared in the local card, then Directory sync published it. Card check turned green; CV execution produced a held draft. |
| Planner restart | The held snapshot, plan/result digests and events were unchanged after restart. No application AU ran again. |
| Approval | Released output equalled the frozen draft. Missing notes and a wrong digest were rejected. An identical review retry produced no extra review/release; a conflicting decision failed. |
| Rejection | A separate draft was quarantined with no result-release event. |
| Missing wiki evidence | Temporarily withholding the isolated wiki index blocked execution despite the eligible card. The index was restored exactly afterwards. No wiki source was removed. |
| Actual Studio upload | Uploaded CV/JD files reached the shared inbox unchanged. The extracted JD became selection context; the generated result was held for review. |
| Browser review | The draft was rejected with notes identifying unsupported claims. Studio displayed quarantine; the subsequent Flow audit recorded the controlled outcome with a full wiki citation. A saved released case also reopened with its original digest and notes. |
| Focused card display | The recorded CV declaration and complete source quote appeared first. The original estate report remained available in a collapsed disclosure. |

The staged integration helper passed **110 checks**. Separately, **106 Python
tests**, **15 Studio JavaScript tests**, and all **eight hosted/local Compose
scenarios** passed. The launcher suite covers shell/batch command construction;
this was a real Mac Docker rehearsal, not a full Windows Docker rehearsal.

## Assessment quality remains a separate concern

Three runs of the same synthetic CV/JD produced different assessments. Review
found omitted on-call evidence, confusion between essential and desirable
requirements, uncertain leadership evidence, and unsupported claims about the
duration or absence of regulated experience. The browser-reviewed third draft
was quarantined for those reasons. Automated approval in the protocol checks
is explicitly labelled as a control test, not approval of assessment quality.

The walkthrough now gives learners three specific evidence checks for this
example. No model prompt was changed merely to make the rehearsal pass. The
control findings do not establish reliable hiring judgement or legal compliance.

[Evidence archive](evidence.zip) contains synthetic inputs, requests, responses,
traces, the independent content review, source hashes and experimental test
helpers. Private settings and credentials are excluded. The harness is a dated
rehearsal snapshot, not another learner setup path. The source baseline was
`9248f95`; the archived patch and hashes identify the changes rehearsed.

![Quarantined draft with substantive review notes](quarantined-review.png)
