#!/usr/bin/env bash
# Seed and verify the inspectable EU AI Act governance/evidence corpus.
# Deterministic (no LLM): post pre-baked promotion sidecars to tool-wiki-store.
set -euo pipefail

cd "$(dirname "$0")/.."

SEED_DIR="course/sessions/session-04-compliance/regulations-seed"
INBOX_DIR="system/inbox/regulations"
BRIDGE_URL="${WIKI_STORE_URL:-http://localhost:7403}/invoke?capability=tool-wiki-store"

if [[ ! -d "$SEED_DIR" ]]; then
  echo "Seed directory not found: $SEED_DIR" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required for this script (standard library only; no packages)." >&2
  exit 1
fi

printf 'Loading corpus: curated EU AI Act Session 4 regulations from %s\n' "$SEED_DIR"
mkdir -p "$INBOX_DIR"
cp "$SEED_DIR"/*.md "$INBOX_DIR/"

python3 - "$SEED_DIR" "$BRIDGE_URL" <<'PY'
import glob
import json
import sys
import urllib.error
import urllib.request

seed_dir, bridge = sys.argv[1], sys.argv[2]


def invoke(inputs):
    body = {"inputs": inputs}
    request = urllib.request.Request(
        bridge,
        data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"tool-wiki-store returned HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"cannot reach tool-wiki-store at {bridge}: {error.reason}") from error


count = 0
for sidecar_path in sorted(glob.glob(f"{seed_dir}/*.promotion.json")):
    with open(sidecar_path, encoding="utf-8") as sidecar_file:
        sidecar = json.load(sidecar_file)
    result = invoke(
        {
            "op": "write_ingest",
            "promotion": sidecar["promotion"],
            "source_path": f"/data/inbox/regulations/{sidecar['source_file']}",
        }
    )
    stored = (result.get("outputs") or {}).get("stored") or {}
    print(
        f"seeded {stored.get('document_id', '?')} "
        f"({stored.get('passage_count', 0)} passages)"
    )
    count += 1
print(f"loaded: {count} regulation notes into the wiki store")

missing = False
for query in (
    "annex iii high-risk employment recruitment selection evaluate candidates",
    "article 14 human oversight natural persons effectively overseen",
):
    print(f'query: "{query}"')
    result = invoke({"op": "search", "query": query, "limit": 1})
    passages = (result.get("outputs") or {}).get("passages") or []
    if not passages:
        print(f"FAILED: no wiki passage found for query: {query}", file=sys.stderr)
        missing = True
        continue
    top = passages[0] if isinstance(passages[0], dict) else {}
    passage_id = str(top.get("passage_id") or "").strip()
    source = str(top.get("source_path") or "").strip()
    if not passage_id or not source:
        print(
            f"FAILED: top wiki passage lacks passage_id or source_path for query: {query}",
            file=sys.stderr,
        )
        missing = True
        continue
    print(f"top passage_id: {passage_id}")
    print(f"top source: {source}")

if missing:
    raise SystemExit("Session 4 wiki verification failed")
print("verified: the exact Session 4 Annex III and Article 14 governance queries return cited evidence")
PY
