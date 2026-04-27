# Course sessions

Published session material lives here.

The slide decks are Marp-ready markdown snapshots generated from the private
working material in `aoa-knowledge`. The knowledge repo remains the source of
truth; publish updated snapshots with:

```bash
python3 scripts/publish_slides.py
```

Example export commands:

```bash
npx @marp-team/marp-cli course/sessions/01-agentic-inversion/slides/deck.md --pptx
npx @marp-team/marp-cli course/sessions/01-agentic-inversion/slides/deck.md --pdf
```
