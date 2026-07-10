# One dependency image for both halves of the Session 3 lab. The native and
# wrapped services mount the same authored agent files and change only the
# process exposed at the boundary.
FROM node:24-slim

ENV NODE_ENV=development \
    EVE_APP_ROOT=/app \
    EVE_PORT=3000

WORKDIR /app

COPY lab/package.json lab/package-lock.json ./
RUN npm ci --no-audit --no-fund

# Reuse the known-good EVE project shell and generic AOA adapter. The lab's
# authored behaviour and capability-specific adapter entry point replace only
# the files that should vary between Agentic Units.
COPY interviewer/tsconfig.json ./tsconfig.json
COPY interviewer/agent/ ./agent/
COPY interviewer/adapter/ ./adapter/
COPY red-flags/agent.ts ./agent/agent.ts
COPY red-flags/instructions.md ./agent/instructions.md
COPY red-flags/capability-card.yaml ./capability-card.yaml
COPY red-flags/boot.mjs ./adapter/boot.mjs

EXPOSE 3000 8888

CMD ["node", "adapter/boot.mjs"]
