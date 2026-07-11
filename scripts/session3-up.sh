#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

compose=(docker compose)
if [[ -f .env ]]; then
  compose+=(--env-file .env)
fi

local_ollama=false
if [[ "${AOA_LOCAL:-}" == "1" || "${AOA_LOCAL:-}" == "true" ]]; then
  compose+=(--profile local)
  local_ollama=true
fi

files=(
  -f system/docker-compose.yml
  -f system/docker-compose.session3.yml
  -f system/docker-compose.session3-lab.yml
)

# Native authoring is deliberately isolated from AOA. Remove a previous estate
# before opening EVE so no stale interviewer card appears during this checkpoint.
"${compose[@]}" "${files[@]}" \
  --profile session3 \
  --profile session3-lab-native \
  --profile session3-lab-wrapped \
  down --remove-orphans

"${compose[@]}" "${files[@]}" build eve-workshop-native

if [[ "$local_ollama" == "true" ]]; then
  "${compose[@]}" "${files[@]}" up -d ollama
fi

echo
echo "Opening the native EVE workshop. AOA is not running yet."
echo "Use eve init, eve info, and eve dev to build and test the agent."
echo

exec "${compose[@]}" "${files[@]}" \
  run --rm --no-deps --service-ports eve-workshop-native
