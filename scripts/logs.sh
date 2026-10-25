#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

compose=(docker compose)
if [[ -f .env ]]; then
  compose+=(--env-file .env)
fi
if [[ -f .env.revised ]]; then
  compose+=(--env-file .env.revised)
fi

exec "${compose[@]}" \
  -f system/docker-compose.yml \
  -f system/docker-compose.session1.yml \
  -f system/docker-compose.session3.yml \
  -f system/docker-compose.session3-lab.yml \
  -f system/docker-compose.session4.yml \
  -f system/docker-compose.revised.yml \
  -f system/docker-compose.revised-eve.yml \
  -f system/docker-compose.directory.yml \
  --profile session1 \
  --profile session2 \
  --profile session3 \
  --profile session3-lab-native \
  --profile session3-lab-wrapped \
  --profile session4 \
  --profile directory \
  --profile local \
  logs -f --tail=100 "$@"
