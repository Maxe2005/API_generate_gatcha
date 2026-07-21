# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# curl is required by the docker-compose healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# UID 1000 matches the typical host dev user — the `celery` service in the
# root docker-compose bind-mounts the source tree (./API_generate_gatcha:/app),
# so a mismatched container UID would leave root-owned logs/static files on
# the host. `chown` the workdir itself: WORKDIR creates it as root before any
# COPY runs, and a non-root user needs write access on the directory (not
# just its contents) to create logs/, app/static/images, etc. at runtime.
RUN useradd --create-home --uid 1000 --shell /bin/bash appuser \
    && chown appuser:appuser /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY --chown=appuser:appuser . .

USER appuser

# Expose port
EXPOSE 8000

# Run the application. UVICORN_RELOAD=1 opts into --reload for local dev;
# off by default so the image doesn't silently ship a dev-only behavior.
# Shell form + `exec` so uvicorn becomes PID 1 and receives signals directly
# (docker stop) instead of being a child of an intermediary /bin/sh.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port 8000 ${UVICORN_RELOAD:+--reload}
