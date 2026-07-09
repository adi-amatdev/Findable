# syntax=docker/dockerfile:1

# ── Builder: install deps into a venv ──
FROM python:3.12-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ReadMe.md ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
      "fastapi>=0.111" \
      "uvicorn[standard]>=0.30" \
      "pydantic>=2.7" \
      "pydantic-settings>=2.3" \
      "httpx>=0.27" \
      "beautifulsoup4>=4.12" \
      "lxml>=5.2" \
      "python-dotenv>=1.0" \
      "redis>=5.0" \
      "fpdf2>=2.7"

# ── Runtime: slim image with just the venv + app ──
FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY app ./app

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT:-8000}"]
