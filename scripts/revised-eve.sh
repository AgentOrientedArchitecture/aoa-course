#!/usr/bin/env bash
set -euo pipefail
session=3
mode="${1:-native}"
source "$(dirname "$0")/revised-compose.sh"
case "$mode" in
 native)
  # Stop course services to expose the native framework boundary. Data is retained.
  "${compose[@]}" "${files[@]}" --profile session3 --profile session3-lab-native --profile session3-lab-wrapped down --remove-orphans
  "${compose[@]}" "${files[@]}" build eve-workshop-native
  if [[ "${AOA_LOCAL:-false}" == "true" || "${AOA_LOCAL:-0}" == "1" ]]; then
    "${compose[@]}" "${files[@]}" up -d ollama
  fi
  exec "${compose[@]}" "${files[@]}" run --rm --no-deps --service-ports --user "$(id -u):$(id -g)" -e HOME=/tmp eve-workshop-native;;
 adopt)
  workspace=system/agents-eve/workshop
  for path in agent/agent.ts agent/instructions.md agent/channels/eve.ts; do
    [[ -f "$workspace/$path" ]] || { echo "Missing $workspace/$path. Complete the existing EVE authoring lab first." >&2; exit 1; }
  done
  [[ -f "$workspace/capability-card.yaml" ]] || cp system/agents-eve/runtime/templates/interviewer-questions.yaml "$workspace/capability-card.yaml"
  "${compose[@]}" "${files[@]}" build eve-workshop-native
  "${compose[@]}" "${files[@]}" run --rm --no-deps --user "$(id -u):$(id -g)" -e HOME=/tmp eve-workshop-native npm install --offline --no-audit --no-fund
  exec "${compose[@]}" "${files[@]}" --profile session3 --profile session3-lab-wrapped up --build -d --remove-orphans;;
 *) echo 'Usage: revised-eve.sh native|adopt' >&2; exit 2;;
esac
