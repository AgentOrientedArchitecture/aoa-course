#!/usr/bin/env bash
set -euo pipefail
session="${1:?Usage: revised-up.sh 1|2|3|4 [compose up options]}"; shift
source "$(dirname "$0")/revised-compose.sh"
if [[ "$session" == 3 ]]; then
  echo 'Use revised-eve.sh native for authoring, then revised-eve.sh adopt.' >&2
  exit 2
fi
exec "${compose[@]}" "${files[@]}" --profile "session$session" up --build -d --remove-orphans "$@"
