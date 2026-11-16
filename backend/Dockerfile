# Outlogik API (FastAPI). Built by DigitalOcean App Platform from this directory; see
# docs/DEPLOYMENT.md. The same image runs the pre-deploy migration job (alembic upgrade head).

# 1. Install the dependencies into a virtual environment.
FROM python:3.12-slim AS build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv
RUN pip install --no-cache-dir uv==0.11.32
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. The runtime image: the environment and the code, without the build tools.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/app/.venv/bin:$PATH
WORKDIR /app
COPY --from=build /app/.venv ./.venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
RUN useradd --create-home --uid 10001 outlogik
USER outlogik

EXPOSE 8080
# Visitor IPs come from CLIENT_IP_HEADER / SITE_PROXY_SECRET (app/core/request.py), not from
# X-Forwarded-For, so uvicorn's own proxy handling is left at its safe default.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2", "--no-server-header"]
