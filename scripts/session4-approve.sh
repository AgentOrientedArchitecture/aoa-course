#!/usr/bin/env bash
# The live approval beat: approve evaluator-cv through the registry lifecycle.
# The card_approved governance event appears in the Studio; the next estate
# check flips the Art 72 finding because the estate changed - not the checker.
set -euo pipefail

REGISTRY_URL="${REGISTRY_URL:-http://localhost:7100}"

python3 - "$REGISTRY_URL" <<'EOF'
import json, sys, urllib.request, urllib.parse

registry = sys.argv[1]
with urllib.request.urlopen(f"{registry}/find?" + urllib.parse.urlencode({"id": "evaluator-cv"}), timeout=10) as resp:
    found = json.load(resp)
card = found.get("capability") or found
lifecycle = card.setdefault("lifecycle", {})
lifecycle["status"] = "approved"
lifecycle["approved_by"] = ""   # registry stamps the approver role + emits card_approved
lifecycle["approved_at"] = ""
req = urllib.request.Request(
    f"{registry}/update", data=json.dumps(card).encode(),
    headers={"content-type": "application/json"}, method="POST",
)
with urllib.request.urlopen(req, timeout=10) as resp:
    resp.read()
print("evaluator-cv approved - watch the governance pane, then re-run the estate check")
EOF
