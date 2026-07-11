# Pinned EVE workshop toolchain for Session 3. Participants use the real EVE
# CLI against a bind-mounted workspace without installing Node or npm on the
# host. `npm ci` also warms npm's cache, so `eve init .` can install the
# workshop's already-pinned dependencies with venue networking disabled.
FROM node:24-slim

ENV NODE_ENV=development \
    EVE_APP_ROOT=/workshop \
    EVE_PORT=3000

WORKDIR /app

COPY lab/package.json lab/package-lock.json ./
RUN npm ci --no-audit --no-fund

# The reusable AOA bridge is platform plumbing, not part of the participant's
# EVE project. The generic entry point derives JSON input/output mapping from
# the capability card, so adoption does not require agent-specific code.
COPY interviewer/adapter/ ./adapter/

EXPOSE 3000 8888

CMD ["npm", "exec", "--", "eve", "dev", "--no-ui", "--host", "0.0.0.0", "--port", "3000"]
