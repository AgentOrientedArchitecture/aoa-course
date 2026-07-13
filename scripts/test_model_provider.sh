#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "error=.env not found in the repository root" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "error=Docker Compose v2 is required; run 'docker compose version' to diagnose" >&2
  exit 1
fi

exec docker compose \
  --env-file .env \
  -f system/docker-compose.yml \
  --profile session1 \
  run --rm --no-deps --build \
  evaluator python -u -m _base.provider_test
