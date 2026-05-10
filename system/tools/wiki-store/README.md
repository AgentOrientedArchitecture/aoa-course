# tool-wiki-store

A registered deterministic capability of `kind: tool`.

The container runs an MCP server plus a small AOA bridge. The MCP server owns
the local wiki store, bind-mounted to `system/wiki/` in the repo:

- `raw/` for captured source files
- `promoted/` for generated markdown pages
- `index.json` for deterministic retrieval

MCP tools:

| Tool | Purpose |
|---|---|
| `write_ingest` | Persist promoted knowledge into the wiki layers |
| `search` | Return citeable passages from `index.json` |
| `graph` | Return typed graph nodes and edges for Studio |
| `reset` | Clear `raw/`, `promoted/`, and `index.json` for replaying the demo |

Agents call the bridge through the registry as `tool-wiki-store`.

Search is deliberately small and inspectable: it tokenises the user query,
drops common stopwords, then scores matches across document title, summary,
passage quote, and `why_it_matters`. This is enough for the course to show
grounded retrieval without hiding the behaviour behind a vector database.

`reset` exists only for the live demo loop. It clears `system/wiki/raw/`,
`system/wiki/promoted/`, and `system/wiki/index.json` so participants can
replay ingest and graph construction from a clean state.

It also exposes a graph projection for the Studio:

- `document` nodes for promoted wiki pages
- `concept` nodes from promoted concepts and relationships
- `passage` nodes for citeable indexed passages
- `open_question` nodes for gaps raised during ingest
