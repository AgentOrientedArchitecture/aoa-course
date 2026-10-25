# Architecture diagrams

These SVGs describe the revised course implementation. They are ordinary repository files, viewable in a Markdown preview or browser, with accessible titles/descriptions. They do not require Mermaid or an external rendering service.

- `components.svg`: the running components and their responsibilities.
- `cv-selection.svg`: proposal, eligibility, choice, validation and execution.
- `wiki-decision.svg`: bounded promotion judgement inside an AU.
- `eve-adoption.svg`: EVE authoring, local adoption and external discovery.
- `eve-invocation.svg`: the real EVE session behind the AOA bridge.
- `durable-case.svg`: eligibility, held result, restart and review.

Edit `scripts/render-course-diagrams.py` from the repository root and run `python3 scripts/render-course-diagrams.py` to regenerate them using the Python standard library. The [architecture guide](../ARCHITECTURE.md) supplies the explanatory text and implementation references; the [adoption guide](../sessions/session-03-eve/ADOPTION.md) expands Session 3.
