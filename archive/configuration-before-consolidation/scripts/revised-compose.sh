#!/usr/bin/env bash
# Shared configuration; source this file from the revised launchers.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
compose=(docker compose)
[[ ! -f .env ]] || compose+=(--env-file .env)
[[ ! -f .env.revised ]] || compose+=(--env-file .env.revised)
[[ "${AOA_LOCAL:-false}" != "true" && "${AOA_LOCAL:-0}" != "1" ]] || compose+=(--profile local)
files=(-f system/docker-compose.yml -f system/docker-compose.directory.yml)
case "$session" in
  1) files+=(-f system/docker-compose.session1.yml);;
  2) ;;
  3) files+=(-f system/docker-compose.session3.yml -f system/docker-compose.session3-lab.yml);;
  4) files+=(-f system/docker-compose.session4.yml);;
  *) echo 'Choose session 1, 2, 3 or 4.' >&2; exit 2;;
esac

export COURSE_DISCOVERY_BACKEND=local
if [[ "$session" == 3 || "$session" == 4 ]]; then
  compose+=(--profile directory)
  export COURSE_DISCOVERY_BACKEND=agntcy
  export DIRECTORY_UID="$(id -u)" DIRECTORY_GID="$(id -g)"
fi
files+=(-f system/docker-compose.revised.yml)
[[ "$session" != 3 ]] || files+=(-f system/docker-compose.revised-eve.yml)

# Keep the displayed registry aligned with this session's running estate.
case "$session" in
  1|3)
    export COURSE_REGISTRY_ALLOWLIST=tool-document-text,parser-cv,evaluator-cv,evaluator-cv-data,evaluator-cv-frontend,reporter-cv-fit
    export COURSE_EVALUATOR_ALLOWLIST=evaluator-cv
    [[ "$session" != 3 ]] || COURSE_REGISTRY_ALLOWLIST+=,interviewer-questions;;
  2)
    export COURSE_REGISTRY_ALLOWLIST=tool-filesystem,tool-document-text,tool-wiki-store,parser-cv,parser-notes,parser-query,evaluator-cv,evaluator-cv-data,evaluator-cv-frontend,evaluator-promote,evaluator-wiki-query,reporter-cv-fit,reporter-ingest-summary,reporter-answer
    export COURSE_EVALUATOR_ALLOWLIST=evaluator-cv,evaluator-promote,evaluator-wiki-query;;
  4)
    export COURSE_REGISTRY_ALLOWLIST=tool-filesystem,tool-document-text,tool-wiki-store,parser-cv,parser-query,parser-estate,evaluator-cv,evaluator-cv-data,evaluator-cv-frontend,evaluator-wiki-query,evaluator-plan-governance,evaluator-agent-evidence,evaluator-flow-evidence,reporter-cv-fit,reporter-answer,reporter-agent-evidence,reporter-flow-audit
    export COURSE_EVALUATOR_ALLOWLIST=evaluator-cv,evaluator-wiki-query,evaluator-plan-governance,evaluator-agent-evidence,evaluator-flow-evidence;;
esac
export COURSE_DIRECTORY_EXPECTED_AUS
COURSE_DIRECTORY_EXPECTED_AUS="$(tr ',' '\n' <<< "$COURSE_REGISTRY_ALLOWLIST" | sed '/^tool-/d' | paste -sd, -)"
