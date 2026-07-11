#!/bin/sh
set -eu

cat <<'EOF'

Session 3 · EVE workshop
========================

You are inside the pinned EVE container. The current directory is mounted from:
  system/agents-eve/workshop
EOF

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
  1. Type: eve init .
  2. When EVE opens its dev UI, press Ctrl+C to return here.
  3. Edit agent/agent.ts and agent/instructions.md on your Windows host.
  4. Type: eve info
  5. Type: eve dev
  6. Talk to and test your standalone agent in EVE's terminal UI.
EOF
fi

cat <<'EOF'
Adoption, after the standalone agent works:
  cp /adoption-kit/interviewer-questions.yaml capability-card.yaml
  # edit the card on the host, then type: exit
  # back on the host run: scripts\session3-adopt.bat

Useful commands:
  eve --help    eve info    eve dev    exit

EOF

export PS1='eve-workshop> '
exec /bin/sh -i
