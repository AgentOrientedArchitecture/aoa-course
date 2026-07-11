#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -e system/agents-eve/workshop/agent ]]; then
  echo "The Session 3 EVE agent already exists."
  echo "Continue with the lab, or remove system/agents-eve/workshop/agent to start again."
  exit 1
fi

compose=(docker compose)
if [[ -f .env ]]; then
  compose+=(--env-file .env)
fi

files=(
  -f system/docker-compose.yml
  -f system/docker-compose.session3.yml
  -f system/docker-compose.session3-lab.yml
)

"${compose[@]}" "${files[@]}" build eve-workshop-native
# EVE normally hands an interactive human straight into `eve dev` after init.
# Mark this wrapper as an agent-driven scaffold so the CLI writes the project,
# prints its handoff, and exits; the learner starts dev at the next checkpoint.
exec "${compose[@]}" "${files[@]}" run --rm --no-deps \
  -e AI_AGENT=course-scaffold \
  eve-workshop-native /app/node_modules/.bin/eve init .
