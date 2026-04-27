# Built on the shared base image; see ../_base/Dockerfile.
FROM aoa-course/agent-base:latest

ENV AGENT_NAME=reporter \
    AGENT_HOST=reporter \
    AGENT_PORT=7303

WORKDIR /app

COPY agent.py /app/agent.py

EXPOSE 7303
CMD ["python", "-u", "/app/agent.py"]
