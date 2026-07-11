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
  echo "No EVE agent exists yet. Run ./scripts/session3-up.sh and type: eve init ."
  exit 1
fi
if [[ ! -f system/agents-eve/workshop/capability-card.yaml ]]; then
  echo "No capability card exists yet. In the workshop shell run:"
  echo "  cp /adoption-kit/interviewer-questions.yaml capability-card.yaml"
  exit 1
fi

"${compose[@]}" "${files[@]}" --profile session3-lab-native stop eve-workshop-native >/dev/null 2>&1 || true
"${compose[@]}" "${files[@]}" --profile session3-reference stop eve-interviewer >/dev/null 2>&1 || true

"${compose[@]}" "${files[@]}" \
  --profile session3 \
  --profile session3-lab-wrapped \
  up --build -d --remove-orphans "$@"

echo
echo "Your EVE agent is now adopted into AOA."
echo "Open http://localhost:8080 and choose: CV fit + interview"
echo "Registry card: http://localhost:7100/find?id=interviewer-questions"
echo "Agent card:    http://localhost:7311/.well-known/agent-card.json"
