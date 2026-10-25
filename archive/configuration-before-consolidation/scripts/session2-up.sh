#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source ./scripts/course-mode.sh
if [[ "$course_revised" == true ]]; then
  exec ./scripts/revised-up.sh 2 "$@"
fi

compose=(docker compose)
if [[ -f .env ]]; then
  compose+=(--env-file .env)
fi
if [[ "${AOA_LOCAL:-}" == "1" || "${AOA_LOCAL:-}" == "true" ]]; then
  compose+=(--profile local)
fi

exec "${compose[@]}" \
  -f system/docker-compose.yml \
  --profile session2 \
  up --build -d --remove-orphans "$@"
