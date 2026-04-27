#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo ".env not found"
  exit 1
fi

set -a
. ./.env
set +a

BASE="${OPENAI_BASE_URL%/}"
KEY="${AOA_OPENAI_API_KEY:-${OPENAI_API_KEY:-}}"
MODEL_NAME="${MODEL:-}"
REASONING="${OPENAI_REASONING_EFFORT:-low}"
FORMAT="${OPENAI_RESPONSE_FORMAT:-json_object}"

if [ -z "$BASE" ] || [ -z "$KEY" ] || [ -z "$MODEL_NAME" ]; then
  echo "OPENAI_BASE_URL, AOA_OPENAI_API_KEY, and MODEL must be set"
  exit 1
fi

BODY="$(mktemp)"
STATUS="$(
  curl -sS -o "$BODY" -w "%{http_code}" \
    -H "Authorization: Bearer ${KEY}" \
    -H "Content-Type: application/json" \
    -d "{
      \"model\":\"${MODEL_NAME}\",
      \"messages\":[
        {\"role\":\"system\",\"content\":\"Return only JSON. No prose.\"},
        {\"role\":\"user\",\"content\":\"Return exactly {\\\"ok\\\":true}.\"}
      ],
      \"max_tokens\":256,
      \"temperature\":0,
      \"reasoning_effort\":\"${REASONING}\",
      \"response_format\":{\"type\":\"${FORMAT}\"}
    }" \
    "${BASE}/chat/completions"
)"

echo "status=${STATUS}"
python3 - "$BODY" <<'PY'
import json
import sys

path = sys.argv[1]
data = json.load(open(path))
if "error" in data:
    print("error=", data["error"])
    raise SystemExit(1)

choice = (data.get("choices") or [{}])[0]
message = choice.get("message") or {}
print("model=", data.get("model"))
print("finish_reason=", choice.get("finish_reason"))
print("message_keys=", sorted(message))
print("content=", repr((message.get("content") or "")[:200]))
reasoning = message.get("reasoning") or ""
print("reasoning_len=", len(reasoning))
PY
