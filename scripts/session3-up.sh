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

# Remove either governed implementation before entering the standalone EVE
# workshop. The agent should not exist in the AOA registry until adoption.
"${compose[@]}" "${files[@]}" --profile session3-lab-wrapped stop eve-workshop-wrapped >/dev/null 2>&1 || true
"${compose[@]}" "${files[@]}" --profile session3-reference stop eve-interviewer >/dev/null 2>&1 || true

"${compose[@]}" "${files[@]}" build eve-workshop-native
"${compose[@]}" "${files[@]}" --profile session3 up --build -d --remove-orphans

echo
echo "AOA is running at http://localhost:8080."
echo "Opening the interactive EVE workshop container..."
echo

exec "${compose[@]}" "${files[@]}" run --rm --no-deps --service-ports eve-workshop-native
