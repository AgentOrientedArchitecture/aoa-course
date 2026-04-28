FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

ENV AGENT_NAME=reporter \
    AGENT_HOST=reporter \
    AGENT_PORT=8888

WORKDIR /app

COPY _base/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY _base/base.py _base/model.py _base/registry_client.py _base/json_utils.py /app/_base/
RUN touch /app/_base/__init__.py

COPY reporter/agent.py /app/agent.py

EXPOSE 8888
CMD ["python", "-u", "/app/agent.py"]
