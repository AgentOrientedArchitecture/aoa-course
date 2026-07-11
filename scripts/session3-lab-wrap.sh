#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

compose=(docker compose)
if [[ -f .env ]]; then
  compose+=(--env-file .env)
fi
if [[ "${AOA_LOCAL:-}" == "1" || "${AOA_LOCAL:-}" == "true" ]]; then
  compose+=(--profile local)
fi

files=(
  -f system/docker-compose.yml
  -f system/docker-compose.session3.yml
  -f system/docker-compose.session3-lab.yml
)

if [[ ! -f system/agents-eve/workshop/agent/instructions.md ]]; then
  echo "No EVE agent exists yet. Run ./scripts/session3-lab-init.sh first."
  exit 1
fi
if [[ ! -f system/agents-eve/workshop/capability-card.yaml ]]; then
  echo "No capability card exists yet. Add it before adopting the agent into AOA."
  exit 1
fi

"${compose[@]}" "${files[@]}" --profile session3-lab-native stop eve-workshop-native >/dev/null 2>&1 || true
"${compose[@]}" "${files[@]}" --profile session3-reference stop eve-interviewer >/dev/null 2>&1 || true

exec "${compose[@]}" "${files[@]}" \
  --profile session3 \
  --profile session3-lab-wrapped \
  up --build -d --remove-orphans "$@"
