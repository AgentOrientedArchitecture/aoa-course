#!/usr/bin/env bash
# Source from a launcher after changing to the repository root.
course_revised=false
case "${AOA_REVISED:-auto}" in
  1|true) course_revised=true;;
  0|false) ;;
  auto) [[ ! -f .env.revised ]] || course_revised=true;;
  *) echo 'AOA_REVISED must be auto, 1/true or 0/false.' >&2; exit 2;;
esac
