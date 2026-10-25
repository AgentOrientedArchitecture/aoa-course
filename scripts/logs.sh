#!/usr/bin/env bash
set -euo pipefail
session=1
source "$(dirname "$0")/compose.sh"
exec "${compose[@]}" "${files[@]}" --profile "*" logs -f --tail=100 "$@"
