# Built on the shared base image; see ../_base/Dockerfile.
FROM aoa-course/agent-base:latest

ENV AGENT_NAME=parser \
    AGENT_HOST=parser \
    AGENT_PORT=8888

WORKDIR /app

COPY agent.py /app/agent.py

EXPOSE 8888
CMD ["python", "-u", "/app/agent.py"]
