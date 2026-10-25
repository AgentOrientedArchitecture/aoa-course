# Course content review

Reviewed on 25 October 2026 for a fresh checkout of `main`. The review covered
setup, all four session walkthroughs and their supporting exercises, architecture
and service/tool references, Studio navigation and instructions, fixtures, seed
corpora and the relevant launcher/runtime behaviour. Private keys and learner
runtime data were not used as review material.

## Learner route

Start with [setup](pre-work/SETUP.md), then use one `WALKTHROUGH.md` per session:

| Session | Complete path |
|---|---|
| [1 · CV](sessions/session-01-cv-fit/WALKTHROUGH.md) | Run → inspect task proposal and AU selection → compare evaluators → edit the selected AU → review |
| [2 · Wiki](sessions/session-02-wiki/WALKTHROUGH.md) | Ingest → inspect promotion/rejection/review → inspect graph → ask with retrieved evidence → review |
| [3 · EVE and AGNTCY](sessions/session-03-eve/WALKTHROUGH.md) | Author → accept natively → adopt → inspect OASF discovery → compose CV/interview → stop Directory and test failure → recover → review |
| [4 · Compliance](sessions/session-04-compliance/WALKTHROUGH.md) | Check card evidence → add declaration to the selected evaluator → hold result → restart → review exact result → audit |

`DECISIONS.md`, `ADOPTION.md`, `DIRECTORY.md` and `DURABLE-CASES.md` are optional
explanations or deeper exercises. None is a second required walkthrough.
The setup, overview, instructor runbook and validation record now have neutral
filenames. The unused root provider preset is archived, leaving one current
`.env.example`. Edition labels were removed from the current learner route, diagrams
and visible Studio instructions. Earlier Studio bookmarks redirect to the current
pages. Repository source and fixture links open GitHub when read in Studio;
the documentation server still exposes only course Markdown and scoped diagrams.

## Accuracy and usability corrections

- The CV workflow has three responsibilities and five available AUs. Selection
  uses task purpose and assessment emphasis; the selected evaluator subsequently
  reads the documents. A model choice becomes an accepted binding only after
  composition validation.
- Hot-reload and governance exercises follow the evaluator that actually ran,
  including specialist runtimes. The healthcare-payments job's historical
  `fintech` filename is explained without changing the source fixture.
- Wiki `review` and `reject` both prevent publication. There is no editorial
  approval queue. Preserving the parser's quotes is not proof that the parser
  copied the source accurately.
- Session 3 includes AGNTCY inspection and the outage check before finishing.
  EVE's terminal UI, host/container file paths, initial scaffold model error,
  required copy-and-paste files and adoption steps are described in order.
- The Mac/Linux native launcher now prints the machine and full workshop path,
  as Windows already did, so a remote shell is distinguishable from a local one.
- Sessions 3–4 require AGNTCY AU discovery. Local adoption, lifecycle and tool
  lookup remain in the registry. No silent local-discovery fallback is taught.
- Persistence descriptions match the SQLite case store. A held result survives
  restart; interrupted invocation is not blindly replayed. Review binds to the
  same digest, and an identical retry does not release twice.
- Troubleshooting uses current launchers and preserves data. The retained legacy
  reset script is explicitly unsuitable for resetting current durable cases.
- Studio distinguishes zero eligible AUs from a single directly bound AU; both
  can legitimately involve no decision-model call.

Original documents are preserved byte-for-byte under
[`archive/course-content-before-review/`](../archive/course-content-before-review/INDEX.md).
Examples, learner exercises, optional host-installed Directory instructions and
existing runtime functionality remain available. No learner checkout, workshop,
keys or saved cases were removed.

## Validation

- **64 Python tests pass**, including document redirects, navigation, filesystem
  boundaries, persistence, allocation, discovery and 16 actual launcher tests.
- **12 Node inspection tests pass**.
- All current local Markdown links and heading targets resolve; shell and
  JavaScript syntax checks pass; `git diff --check` passes.
- The real EVE container starts as a non-root learner using the exact TypeScript
  example from the Session 3 walkthrough. The isolated check uses offline
  dependencies and no provider calls. Package cache and mounted workshop state
  are writable; no learner files are replaced.

The [validation record](VALIDATION.md) preserves earlier provider-backed integration
observations and explains how to repeat the automated checks.

## Remaining teaching checks

A complete learner-led Mac and Windows rehearsal is still required. Automated
checks cannot establish that the instructions are clear in use, that local
hardware is fast enough, or that a particular model response is good.

The wiki seeds are selected April research snapshots. They do not contain every
later course topic, and their gaps should remain visible when querying them.
The regulation corpus is also dated teaching evidence. A timetable spot-check
matched [European Commission guidance](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai); this was not a full legal review.
No source seed was silently updated to make the demo appear more current.

Question quality, semantic decision calibration, externally owned agent adoption,
production durability and a full enterprise AGNTCY deployment remain beyond the
claims demonstrated by this local course. Presentation demo alignment and final
review-question pacing can follow the practical walkthrough.
