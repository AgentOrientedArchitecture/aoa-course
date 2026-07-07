#!/usr/bin/env bash
# Seed the wiki store with the EU AI Act regulations corpus for Session 4.
# Deterministic (no LLM): posts pre-baked promotion sidecars straight to the
# wiki-store bridge, exactly as reporter-ingest-summary would after an LLM
# promotion. Re-runnable after scripts like session4-reset.sh.
set -euo pipefail

cd "$(dirname "$0")/.."

SEED_DIR="course/data/session-04-compliance/regulations-seed"
INBOX_DIR="system/inbox/regulations"
BRIDGE_URL="${WIKI_STORE_URL:-http://localhost:7403}/invoke?capability=tool-wiki-store"

mkdir -p "$INBOX_DIR"
cp "$SEED_DIR"/*.md "$INBOX_DIR/"

python3 - "$SEED_DIR" "$BRIDGE_URL" <<'EOF'
import json, sys, glob, urllib.request

seed_dir, bridge = sys.argv[1], sys.argv[2]
count = 0
for sidecar_path in sorted(glob.glob(f"{seed_dir}/*.promotion.json")):
    sidecar = json.load(open(sidecar_path))
    body = {
        "inputs": {
            "op": "write_ingest",
            "promotion": sidecar["promotion"],
            "source_path": f"/data/inbox/regulations/{sidecar['source_file']}",
        }
    }
    req = urllib.request.Request(
        bridge, data=json.dumps(body).encode(),
        headers={"content-type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.load(resp)
    stored = (result.get("outputs") or {}).get("stored") or {}
    print(f"seeded {stored.get('document_id', '?')} ({stored.get('passage_count', 0)} passages)")
    count += 1
print(f"done: {count} regulation notes in the wiki store")
EOF
