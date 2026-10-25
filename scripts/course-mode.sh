#!/usr/bin/env bash
# Source from a launcher after changing to the repository root.
course_revised=false
case "${AOA_REVISED:-auto}" in
  1|true) course_revised=true;;
  0|false) ;;
  auto)
    # Both October examples may be copied to the usual .env. Inspect only the
    # decision setting's name; never source an environment file as shell code.
    if [[ -f .env.revised ]] || { [[ -f .env ]] && grep -Eq '^[[:space:]]*DECISION_PROVIDER[[:space:]]*=' .env; }; then
      course_revised=true
    fi;;
  *) echo 'AOA_REVISED must be auto, 1/true or 0/false.' >&2; exit 2;;
esac
