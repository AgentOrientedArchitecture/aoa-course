FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY mcp_server.py bridge.py capability-card.yaml /app/

EXPOSE 7402
CMD ["python", "-u", "/app/bridge.py"]
