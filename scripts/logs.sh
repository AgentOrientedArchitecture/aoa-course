#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

compose=(docker compose)
if [[ -f .env ]]; then
  compose+=(--env-file .env)
fi

exec "${compose[@]}" \
  -f system/docker-compose.yml \
  -f system/docker-compose.session1.yml \
  -f system/docker-compose.session3.yml \
  -f system/docker-compose.session3-lab.yml \
  --profile session1 \
  --profile session2 \
  --profile session3 \
  --profile session3-lab-native \
  --profile session3-lab-wrapped \
  logs -f --tail=100 "$@"
