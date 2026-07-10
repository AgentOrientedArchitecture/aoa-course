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

"${compose[@]}" "${files[@]}" --profile session3-lab-native stop eve-red-flags-native >/dev/null 2>&1 || true

exec "${compose[@]}" "${files[@]}" \
  --profile session3 \
  --profile session3-lab-wrapped \
  up --build -d --remove-orphans "$@"
