# Outlogik

SEO and reporting platform for agencies. Each agency is an **organization** with its own team,
clients and client websites. Client contacts can be given read-only access to their own
business through the client portal.

**Status:** Phase 1 (Foundation) is complete. See
[`docs/IMPLEMENTATION_TRACKER.md`](docs/IMPLEMENTATION_TRACKER.md) for what was built and the
decisions made along the way.

| Folder | What's in it |
|---|---|
| `backend/` | FastAPI modular monolith: Python 3.12, SQLAlchemy 2, Alembic, PostgreSQL 16, Redis 7 |
| `frontend/` | Angular 22 app: standalone components, signals, Bootstrap 5.3 with Outlogik's tokens |
| `docs/` | Plan, tracker, [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md), [brand](docs/brand/README.md) |
| `docker-compose.yml` | Local PostgreSQL, Redis and Mailpit |

## Local development (Windows + WSL2 Ubuntu)

You need Docker Desktop (with the WSL2 backend), Python 3.12+, [uv](https://docs.astral.sh/uv/)
and Node.js 22+. Run everything below inside WSL2.

### 1. Start PostgreSQL, Redis and Mailpit

```bash
docker compose up -d
```

Mailpit catches every email the app sends (invitations, password resets, email confirmation).
Its inbox is at http://localhost:8025.

### 2. Backend

```bash
cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The API runs on http://localhost:8000; interactive docs are at http://localhost:8000/api/docs.

### 3. Frontend

```bash
cd frontend
npm ci
npm start
```

Open **http://localhost:4200** and create an account. The dev server forwards `/api` to the
backend, so the browser sees a single site and the session and CSRF cookies just work.

> Session cookies are marked `Secure`. Chrome, Edge and Firefox accept them on
> `http://localhost`. If your browser doesn't, set `COOKIE_SECURE=false` in `backend/.env`
> for local development only.

### Super Admin

Super Admins can only be created from the command line, never through the app:

```bash
cd backend
uv run python -m app.cli create-super-admin --email you@example.com --name "Your Name"
```

## Tests and checks

```bash
cd backend
uv run pytest            # 171 tests; rebuilds the outlogik_test schema from the migrations
uv run ruff check .      # lint
uv run alembic check     # migrations match the models
```

```bash
cd frontend
npm test -- --watch=false   # 65 unit tests (Vitest)
npx ng build                # production build; fails if the bundle budget is exceeded
```

The backend tests use the `outlogik_test` database, which Docker Compose creates on first
start. The same checks run on GitHub Actions for every push and pull request
(`.github/workflows/ci.yml`).

## Common tasks

**Add a database change**

```bash
cd backend
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```

Review the generated file before committing, and name multi-column constraints explicitly.

**Add an icon:** add its Bootstrap Icons name to `frontend/scripts/build-icons.mjs`, then run
`npm run icons`.

**Add an API endpoint or a page:** follow the checklists in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Every organization endpoint must declare a
permission; a test fails the build if one doesn't.

## Project rules

- **No third-party CDNs.** Fonts, icons, scripts and styles are bundled and served by Outlogik
  itself. Nothing loads from Google Fonts or similar.
- **No fake data.** Pages show real records or an honest empty state. Features that need
  Phase 2 integrations say "Not connected yet".
- **The API enforces every permission.** Hiding a button in the UI is only a convenience.
- Third-party licenses are listed in [`THIRD_PARTY_LICENSES`](THIRD_PARTY_LICENSES).
