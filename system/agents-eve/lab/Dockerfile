# Pinned EVE workshop toolchain for Session 3. Participants use the real EVE
# CLI against a bind-mounted workspace without installing Node or npm on the
# host. `npm ci` also warms npm's cache, so `eve init .` can install the
# workshop's already-pinned dependencies with venue networking disabled.
FROM node:24-slim

ENV NODE_ENV=development \
    EVE_APP_ROOT=/workshop \
    EVE_PORT=3000 \
    PATH=/app/node_modules/.bin:$PATH

WORKDIR /app

COPY lab/package.json lab/package-lock.json ./
RUN npm ci --no-audit --no-fund

# The reusable AOA bridge is platform plumbing, not part of the participant's
# EVE project. The generic entry point derives JSON input/output mapping from
# the capability card, so adoption does not require agent-specific code.
COPY interviewer/adapter/ ./adapter/
COPY lab/workshop-shell.sh ./workshop-shell.sh
# Be defensive against an existing Windows checkout created before the
# repository's LF rule was present. A CRLF shebang appears to Docker as a
# missing `/bin/sh\r` interpreter.
RUN sed -i 's/\r$//' ./workshop-shell.sh && chmod +x ./workshop-shell.sh

EXPOSE 3000 8888

CMD ["/app/workshop-shell.sh"]
