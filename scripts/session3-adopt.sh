#!/usr/bin/env bash
# Adopt the learner-authored EVE agent into AOA and start the intent surface.
set -euo pipefail

cd "$(dirname "$0")/.."

workspace="system/agents-eve/workshop"
template="system/agents-eve/runtime/templates/interviewer-questions.yaml"
card="$workspace/capability-card.yaml"

for required in \
  "$workspace/agent/agent.ts" \
  "$workspace/agent/instructions.md" \
  "$workspace/agent/channels/eve.ts"; do
  if [[ ! -f "$required" ]]; then
    echo "Missing EVE agent file: $required"
    echo "Run ./scripts/session3-up.sh, then create and test the agent with eve init and eve dev."
    exit 1
  fi
done

card_created=false
if [[ ! -f "$card" ]]; then
  cp "$template" "$card"
  card_created=true
fi

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

"${compose[@]}" "${files[@]}" \
  --profile session3 \
  --profile session3-lab-wrapped \
  up --build --force-recreate -d --remove-orphans "$@"

ready=false
for _ in {1..120}; do
  if curl --fail --silent --output /dev/null "http://localhost:7311/healthz"; then
    ready=true
    break
  fi
  sleep 1
done

if [[ "$ready" != "true" ]]; then
  echo "AOA started, but the adopted EVE agent was not healthy within 120 seconds."
  echo "Run ./scripts/logs.sh eve-workshop-wrapped registry to inspect the failure."
  exit 1
fi

if ! curl --fail --silent --output /dev/null \
  "http://localhost:7100/find?id=interviewer-questions"; then
  echo "The adopted EVE agent is healthy, but interviewer-questions is absent from the registry."
  echo "Run ./scripts/logs.sh eve-workshop-wrapped registry to inspect the failure."
  exit 1
fi

echo
if [[ "$card_created" == "true" ]]; then
  echo "Created AOA contract: $card"
else
  echo "Using existing AOA contract: $card"
fi
echo
echo "Your EVE agent is now adopted into AOA."
echo "Added by adoption:"
echo "  Agent ID: urn:aoa:agent:eve-workshop-interviewer"
echo "  Registry lifecycle and discovery"
echo "  Outward A2A endpoint and trace boundary"
echo "  Model provenance and skills_hash"
echo
echo "The EVE-authored agent files were not changed."
echo "Open http://localhost:8080 and choose: CV fit + interview"
echo "Registry card: http://localhost:7100/find?id=interviewer-questions"
echo "Agent card:    http://localhost:7311/.well-known/agent-card.json"
