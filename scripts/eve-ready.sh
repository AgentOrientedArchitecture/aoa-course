#!/usr/bin/env bash
set -euo pipefail
ready=false
for _ in {1..120}; do
  if curl --fail --silent --output /dev/null http://localhost:7311/healthz; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "$ready" != true ]]; then
  echo 'The adopted EVE agent was not healthy within 120 seconds. Inspect scripts/logs.sh eve-workshop-wrapped registry.' >&2
  exit 1
fi
curl --fail --silent --output /dev/null 'http://localhost:7100/find?id=interviewer-questions' || {
  echo 'EVE is healthy but interviewer-questions is absent from the registry.' >&2
  exit 1
}
echo 'EVE adopted and registered. Open http://localhost:8080 and choose CV fit + interview.'
