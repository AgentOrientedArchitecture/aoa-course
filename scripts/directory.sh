#!/usr/bin/env bash
# Directory, CLI and Python helper all run in Docker, including on learner laptops.
set -euo pipefail
cd "$(dirname "$0")/.."
mode="${1:-help}"
[[ $# == 0 ]] || shift
export DIRECTORY_UID="$(id -u)" DIRECTORY_GID="$(id -g)"
compose=(docker compose -f system/docker-compose.yml --profile directory)
case "$mode" in
  up|start)
    mkdir -p "${COURSE_DIRECTORY_DATA_ROOT:-.course-data}"
    exec "${compose[@]}" up --build -d --wait --wait-timeout 120 "$@" agntcy-directory;;
  stop)
    exec "${compose[@]}" stop "$@" agntcy-directory;;
  logs)
    exec "${compose[@]}" logs -f --tail=100 "$@" agntcy-directory;;
  cli)
    exec "${compose[@]}" exec -T agntcy-directory dirctl --server-addr 127.0.0.1:8890 --auth-mode insecure "$@";;
  export|push|search|pull|check|sync)
    exec "${compose[@]}" exec -T agntcy-directory python /app/directory-lab.py "$mode" "$@";;
  help|--help|-h)
    echo 'Usage: directory.sh up|stop|logs|export|push|search|pull|check|sync|cli [arguments]';;
  *) echo 'Unknown Directory command. Use directory.sh help.' >&2; exit 2;;
esac
