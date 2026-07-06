# The EVE-authored interviewer AU. EVE targets Node, so unlike the Python agents
# this one runs on a Node base image — but it registers into the same AOA
# registry and speaks the same A2A surface, which is the Session 3 teaching point.
FROM node:24-slim

ENV NODE_ENV=development \
    EVE_APP_ROOT=/app \
    EVE_PORT=3000

WORKDIR /app

# Install dependencies first for layer caching. No lockfile is committed (the
# scaffold generates one), so a plain install resolves the pinned ranges.
COPY package.json ./
RUN npm install --no-audit --no-fund

# The EVE agent, the co-located capability card, and the aoa-eve adapter. At
# runtime docker-compose re-mounts agent/ and capability-card.yaml read-only so
# host edits hot-reload; the image copy is the build-time default.
COPY tsconfig.json capability-card.yaml ./
COPY agent/ ./agent/
COPY adapter/ ./adapter/

EXPOSE 8888

# boot.mjs starts the EVE runtime (eve dev) and the AOA adapter surface.
CMD ["node", "adapter/boot.mjs"]
