#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "$0")/eve-workshop.sh" build "$@"
