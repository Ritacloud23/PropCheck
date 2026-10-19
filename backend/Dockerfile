FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir "uv>=0.8,<1"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN useradd --create-home propcheck && mkdir -p /data/storage && chown -R propcheck /data /app
USER propcheck

EXPOSE 8000
# SEED_DEMO_DATA=true loads the demo data on start (idempotent; restores photos lost with the disk).
CMD ["sh", "-c", "alembic upgrade head && if [ \"$SEED_DEMO_DATA\" = true ]; then python -m app.seed || echo 'Demo seed failed; starting the API anyway.'; fi && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
