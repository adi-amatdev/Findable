FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir fastapi uvicorn[standard]

# Copy source
COPY app/ app/
COPY prompts/ prompts/

# Pre-download Tranco list at build time so first request is fast
RUN python -c "from tranco import Tranco; Tranco(cache=True, cache_dir='.tranco_cache').list()" || true

EXPOSE 8080

# SSE queues and in-progress audit results are intentionally in-process.  Keep a
# single worker so /audit/start, /agent/stream, and /audit/{id}/result always
# reach the same registry.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
