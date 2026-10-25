#!/usr/bin/env bash
set -euo pipefail
session="${1:?Usage: session-up.sh 1|2|3|4 [compose up options]}"; shift
source "$(dirname "$0")/compose.sh"
if [[ "$session" == 3 ]]; then
  echo 'Use eve-workshop.sh native for authoring, then eve-workshop.sh adopt.' >&2
  exit 2
fi
if [[ "$session" == 4 ]]; then
  mkdir -p "${COURSE_DIRECTORY_DATA_ROOT:-.course-data}"
  "${compose[@]}" "${files[@]}" --profile "session$session" up --build -d --remove-orphans "$@"
  exec ./scripts/directory.sh sync --wait 120
fi
exec "${compose[@]}" "${files[@]}" --profile "session$session" up --build -d --remove-orphans "$@"
