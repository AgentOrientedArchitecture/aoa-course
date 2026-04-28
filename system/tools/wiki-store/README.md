# tool-wiki-store

A registered deterministic capability of `kind: tool`.

The container runs an MCP server plus a small AOA bridge. The MCP server owns
the local wiki store:

- `raw/` for captured source files
- `promoted/` for generated markdown pages
- `index.json` for deterministic retrieval

MCP tools:

| Tool | Purpose |
|---|---|
| `write_ingest` | Persist promoted knowledge into the wiki layers |
| `search` | Return citeable passages from `index.json` |

Agents call the bridge through the registry as `tool-wiki-store`.

It also exposes a graph projection for the Studio:

- `document` nodes for promoted wiki pages
- `concept` nodes from promoted concepts and relationships
- `passage` nodes for citeable indexed passages
- `open_question` nodes for gaps raised during ingest
