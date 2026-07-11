#!/usr/bin/env bash
# Backwards-compatible name for the interactive Session 3 workshop.
set -euo pipefail
exec "$(dirname "$0")/session3-up.sh" "$@"
