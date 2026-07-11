#!/usr/bin/env bash
# Publish the learner-authored EVE agent into AOA and start the intent surface.
set -euo pipefail
exec "$(dirname "$0")/session3-lab-wrap.sh" "$@"
