FROM ghcr.io/agntcy/dir-ctl:v1.8.0@sha256:a6cd66961f89ee0b4cc768996b6f621d6424a7059c8571c8faa2489c55218c4e AS upstream
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
COPY --from=upstream /usr/local/bin/dirctl /usr/local/bin/dirctl
COPY system/services/directory/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY scripts/directory-lab.py /app/directory-lab.py
COPY system/services/directory/bridge.py system/services/planner/directory_contract.py /app/
ENV COURSE_DIRECTORY_CLI=/usr/local/bin/dirctl
WORKDIR /course-data
USER 1000:1000
CMD ["dirctl", "daemon", "start", "--data-dir", "/course-data/directory"]
