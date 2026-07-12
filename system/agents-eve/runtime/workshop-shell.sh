#!/bin/sh
set -eu

cat <<'EOF'

Session 3 · Native EVE workshop
===============================

You are inside the pinned EVE container. The current directory is mounted from:
  system/agents-eve/workshop

AOA is not running yet. First create and prove the standalone EVE agent.
EOF

if [ -f agent/instructions.md ] && [ ! -x node_modules/.bin/eve ]; then
  echo
  echo "Restoring the pinned workshop dependencies from the offline image cache..."
  npm install --offline --no-audit --no-fund
fi

if [ -f agent/instructions.md ]; then
  cat <<'EOF'

Existing EVE agent detected.
  Inspect: eve info
  Run/test: eve dev
  Edit the files on your host while this shell stays open.
EOF
else
  cat <<'EOF'

No EVE agent exists yet.
  1. Type: eve --help
  2. Type: eve init .
  3. If EVE opens its dev UI, press Ctrl+C to return here.
  4. Edit agent/agent.ts and agent/instructions.md on your host.
  5. Type: eve info
  6. Type: eve dev
  7. Test the standalone agent until it reliably returns complete JSON.
EOF
fi

cat <<'EOF'

After native testing:
  1. Press Ctrl+C to leave eve dev.
  2. Type: exit
  3. On the host run scripts\session3-adopt.bat (Windows) or
     ./scripts/session3-adopt.sh (macOS/Linux).

AOA adoption creates the capability card and starts the governed estate.

Useful commands:
  eve --help    eve info    eve dev    exit

EOF

export PS1='eve-workshop> '
exec /bin/sh -i
