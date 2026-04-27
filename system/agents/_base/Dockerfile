FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Shared dependencies for every agent
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Shared scaffold modules — agents import from /app/_base
COPY base.py model.py registry_client.py json_utils.py /app/_base/
RUN touch /app/_base/__init__.py

# Concrete agents add their own agent.py and capabilities/ via their
# own Dockerfile (FROM aoa-course/agent-base) and a CMD that invokes
# _base.base.run().
