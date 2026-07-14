#!/usr/bin/env bash
# Reset Session 4 to its learner starting state:
#   - empty the wiki store (re-run session4-seed.sh afterwards)
#   - clear persisted planner traces
#   - remove only the learner-added evaluator-cv review constraint
set -euo pipefail

cd "$(dirname "$0")/.."

WIKI_URL="${WIKI_STORE_URL:-http://localhost:7403}/invoke?capability=tool-wiki-store"
CARD_PATH="system/agents/evaluator/capabilities/cv/capability-card.yaml"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required for this script (standard library only; no packages)." >&2
  exit 1
fi

echo "1/3 resetting wiki store..."
python3 - "$WIKI_URL" <<'PY'
import json
import sys
import urllib.error
import urllib.request

url = sys.argv[1]
request = urllib.request.Request(
    url,
    data=json.dumps({"inputs": {"op": "reset"}}).encode("utf-8"),
    headers={"content-type": "application/json; charset=utf-8"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()
except urllib.error.HTTPError as error:
    detail = error.read().decode("utf-8", errors="replace")
    raise SystemExit(f"wiki reset failed with HTTP {error.code}: {detail}") from error
except urllib.error.URLError as error:
    raise SystemExit(f"cannot reach tool-wiki-store at {url}: {error.reason}") from error
print("   wiki store reset")
PY

echo "2/3 clearing planner traces..."
find system/services/planner/traces -type f -name '*.jsonl' -delete
echo "   traces cleared"

echo "3/3 restoring the evaluator-cv learner baseline..."
python3 - "$CARD_PATH" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
learner_constraint = (
    "- Every verdict is a draft and must be approved by a human reviewer before "
    "it informs candidate screening, interview, or employment action."
)
lines = path.read_text(encoding="utf-8").splitlines()
filtered = [line for line in lines if line.strip() != learner_constraint]
path.write_text("\n".join(filtered) + "\n", encoding="utf-8")
print("   evaluator-cv restored to the red-by-missing-declaration baseline")
PY

echo
echo "Session 4 learner state ready. Next:"
echo "  ./scripts/session4-seed.sh  # load and verify the EU AI Act corpus"
echo "  open http://localhost:8080 and run Agent card check"
