#!/usr/bin/env bash
# Reset Session 4 to its demo starting state:
#   - wiki store emptied (re-run scripts/session4-seed.sh afterwards)
#   - planner traces cleared (so Art 12 starts red until a workflow runs)
#   - evaluator-cv demoted to lifecycle status "draft" (so Art 72 starts red
#     and the live approval beat has something to approve)
set -euo pipefail

cd "$(dirname "$0")/.."

WIKI_URL="${WIKI_STORE_URL:-http://localhost:7403}/invoke?capability=tool-wiki-store"
REGISTRY_URL="${REGISTRY_URL:-http://localhost:7100}"

echo "1/4 resetting wiki store..."
curl -sf -X POST "$WIKI_URL" -H 'content-type: application/json' \
  -d '{"inputs":{"op":"reset"}}' >/dev/null && echo "   wiki store reset"

echo "2/4 clearing planner traces..."
find system/services/planner/traces -name '*.jsonl' -delete
echo "   traces cleared"

echo "3/4 restoring the evaluator-cv card (removes the demo's oversight constraint)..."
git checkout -- system/agents/evaluator/capabilities/cv/capability-card.yaml 2>/dev/null \
  && echo "   card restored from git" \
  || echo "   (not a git checkout; card left as-is)"

echo "4/4 demoting evaluator-cv to draft..."
python3 - "$REGISTRY_URL" <<'EOF'
import json, sys, urllib.request, urllib.parse

registry = sys.argv[1]
with urllib.request.urlopen(f"{registry}/find?" + urllib.parse.urlencode({"id": "evaluator-cv"}), timeout=10) as resp:
    found = json.load(resp)
card = found.get("capability") or found
lifecycle = card.setdefault("lifecycle", {})
lifecycle["status"] = "draft"
lifecycle["approved_by"] = ""
lifecycle["approved_at"] = ""
req = urllib.request.Request(
    f"{registry}/update", data=json.dumps(card).encode(),
    headers={"content-type": "application/json"}, method="POST",
)
with urllib.request.urlopen(req, timeout=10) as resp:
    resp.read()
print("   evaluator-cv is now draft (unapproved)")
EOF

echo
echo "Demo starting state ready. Next:"
echo "  ./scripts/session4-seed.sh     # load the regulations corpus"
echo "  run one CV-fit from the Studio # generates trace evidence (Art 12)"
echo "  run the Estate check           # evaluator-cv: Art 14 red, Art 72 red"
