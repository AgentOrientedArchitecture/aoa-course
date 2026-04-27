# Built on the shared base image; see ../_base/Dockerfile.
FROM aoa-course/agent-base:latest

ENV AGENT_NAME=parser \
    AGENT_HOST=parser \
    AGENT_PORT=7301

WORKDIR /app

COPY agent.py /app/agent.py

EXPOSE 7301
CMD ["python", "-u", "/app/agent.py"]
