# Session 4 - Estate check: EU AI Act evidence readiness

The estate scans itself. A three-AU workflow reads the system's own governance
artefacts - registered capability cards, registry lifecycle state, planner
traces - checks them for evidence hooks related to selected EU AI Act
high-risk-system obligations, and writes a findings report in which every
finding cites the regulation verbatim.

**Findings and evidence only.** The scanner never says "compliant". Green
means *evidence present*; Article 10 is capped at amber by construction; when
the regulations corpus has no passage for an article the finding abstains
(severity `unknown`, `corpus_silent: true`) instead of paraphrasing the law
from model memory.

## The workflow

`parser-estate` → `evaluator-compliance` → `reporter-findings`

- **parser-estate** reads `cards.json` and `traces/*.jsonl` through
  `tool-filesystem` (governance as ordinary files) and emits a typed estate
  inventory. Deterministic — a scan is a read, not a judgement.
- **evaluator-compliance** identifies Annex III point 4 markers
  (recruitment / candidate evaluation -> contextual legal assessment), runs seven evidence checks
  (Articles 9, 10, 11, 12, 13, 14, 72), and attaches the top regulation
  passage from the wiki store to every finding.
- **reporter-findings** renders the posture table and per-finding detail, with
  the fixed scope banner and the evidence-by-construction footer. Its
  `no_compliance_verdict` signal machine-checks the language rule.

## Running it

On macOS or Linux:

```bash
./scripts/session4-up.sh       # full estate: cv-fit + wiki + estate-check
./scripts/session4-seed.sh     # load the regulations corpus (10 notes, 38 passages)
```

On Windows Command Prompt:

```bat
scripts\session4-up.bat
scripts\session4-seed.bat
```

Then open `http://localhost:8080`, select **Estate check**, and run the scan.

Estate reports render the complete retrieved regulation passage rather than a
character-truncated excerpt, so each finding has a readable citation paragraph.

The regulations corpus is curated from the verbatim EUR-Lex text of Regulation
(EU) 2024/1689 (`regulations-seed/`), and seeds through the same `write_ingest`
path the Session 2 wiki uses. **Keeping the corpus current IS the wiki demo's
ingest loop**: ingest a new guidance note through the Ingest tab, re-run the
scan, and the citations update. The Ask tab answers "what does Article 14
require?" from the same corpus.

## The demo arc (~12 min)

1. Reset and seed the opening state with
   `./scripts/session4-reset.sh && ./scripts/session4-seed.sh` on macOS/Linux,
   or run `scripts\session4-seed.bat` on Windows after resetting the demo state.
2. Run one CV-fit from the Studio (needs a model provider) — creates trace
   evidence, so Article 12 has something to find.
3. Run the Estate check. The CV-fit trio is flagged **Annex III candidate -
   employment** with the verbatim citation and a legal-assessment caveat;
   `evaluator-cv` shows **Art 14 red** (no
   oversight declaration) and **Art 72 red** (draft, unapproved).
4. **Fix the estate live, two governance surfaces:**
   - Edit `system/agents/evaluator/capabilities/cv/capability-card.yaml` and add
     this item under `constraints` without removing the existing entries:

     ```yaml
     - A human reviewer must approve every verdict before it informs candidate screening, interview, or employment action.
     ```

     The card hot-reloads and re-registers; watch the registry pane. Re-run the
     estate check: `evaluator-cv` Article 14 changes from red to green because the
     declared oversight evidence changed. Green means evidence present, not that
     the protocol is implemented effectively or the obligation is satisfied.
   - `./scripts/session4-approve.sh` — the `card_approved` governance event
     appears in the Studio.
5. Re-run the Estate check: Art 14 and Art 72 flip green. **The evidence hooks
   appeared because the estate changed - no legal obligation was thereby
   satisfied.**

## The deliberate legal tension

The teaching system uses synthetic CVs; it is not a hiring system. If the same
capabilities were used to analyse, filter, or evaluate real candidates, Annex
III point 4 would be engaged unless a contextual assessment established an
Article 6(3) derogation. The original Regulation schedule and current
Commission implementation guidance also differ: following the May 2026 AI
Omnibus political agreement, the Commission says employment-area high-risk
rules apply from **2 December 2027**, not August 2026. Check the enacted text
and current guidance before deployment.

That is the story, not an awkward disclaimer: we can build a technically
effective tool whose real use may be restricted or unlawful. Architecture can
make evidence and control surfaces inspectable; it cannot grant permission to
deploy.

## What this is not

- Not a classification decision, compliance determination, certification, or
  legal advice.
- Not a source-code scanner: v1 reads estate artefacts only (cards, lifecycle,
  traces). A code-level inventory builder (SAST-style detectors for model
  calls and agent frameworks, feeding the same evaluator) is a documented
  later phase.
- Single jurisdiction: EU AI Act only. NIST AI RMF / ISO 42001 would be
  additional check packs behind the same findings model.

## The knowledge plane is swappable (replacement is registration)

`evaluator-compliance` consumes only the tool contract:
`{op: "search", query, limit}` → `passages[{passage_id, quote, source_path,
score}]`. The v1 backing is the course wiki store — lexical, inspectable,
deliberately simple. The designed swap is a `tool-reg-knowledge` bridge over
the native `cogs` engine (`cogs ask --json` or the `cogs mcp` server), which
adds embeddings, graph-hop retrieval, contradiction surfacing, and abstention
at the retrieval layer. Registering that bridge under the same contract
replaces the knowledge plane **without touching the evaluator** - the course's
third principle, demonstrated on the evidence-readiness checker itself.
