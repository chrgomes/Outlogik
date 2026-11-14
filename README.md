# Outlogik

SEO and reporting platform for agencies. Multi-tenant: each agency is an organization with
its own team, clients and websites.

- `backend/` — FastAPI modular monolith (Python 3.12, SQLAlchemy 2, Alembic, PostgreSQL, Redis)
- `frontend/` — Angular 22 app
- `docs/` — plan, implementation tracker and project docs

Current status: see [`docs/IMPLEMENTATION_TRACKER.md`](docs/IMPLEMENTATION_TRACKER.md).

## Local development (Windows + WSL2 Ubuntu)

Requirements: Docker Desktop (WSL2 backend), Python 3.12+, [uv](https://docs.astral.sh/uv/),
Node.js 22+.

### 1. Start PostgreSQL, Redis and Mailpit

```bash
docker compose up -d
```

Mailpit's inbox, which catches every email the app sends, is at http://localhost:8025.

### 2. Backend

```bash
cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

API docs: http://localhost:8000/api/docs

Create a Super Admin (only possible from the command line):

```bash
uv run python -m app.cli create-super-admin --email you@example.com --name "Your Name"
```

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

Open http://localhost:4200. The dev server proxies `/api` to the backend on port 8000, so
cookies and CSRF work on a single origin.

## Tests

```bash
cd backend && uv run pytest
```

The backend tests use the `outlogik_test` database, which Docker Compose creates on first
start. They rebuild its schema from the migrations on every run.

```bash
cd frontend && npm test -- --watch=false
```

## Database migrations

```bash
cd backend
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```
