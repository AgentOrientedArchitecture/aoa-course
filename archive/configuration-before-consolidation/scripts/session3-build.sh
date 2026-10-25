#!/usr/bin/env bash
# Pre-build Session 3 images without starting services or creating the agent.
set -euo pipefail

cd "$(dirname "$0")/.."

source ./scripts/course-mode.sh
if [[ "$course_revised" == true ]]; then
  exec ./scripts/revised-eve.sh build "$@"
fi

compose=(docker compose)
if [[ -f .env ]]; then
  compose+=(--env-file .env)
fi

exec "${compose[@]}" \
  -f system/docker-compose.yml \
  -f system/docker-compose.session3.yml \
  -f system/docker-compose.session3-lab.yml \
  --profile session3 \
  --profile session3-lab-native \
  build "$@"
