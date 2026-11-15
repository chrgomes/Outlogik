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
| `frontend/` | Angular 22 workspace: the app (`src/`) and the public marketing website (`projects/marketing/`), sharing `brand/` |
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

Open **http://localhost:4200**. Sign-up is **invite-only** (Outlogik invites its clients), so
create the first organization from the command line, then sign in and invite everyone else from
the app:

```bash
cd backend
uv run python -m app.cli create-organization --name "Outlogik" --owner-email you@example.com --owner-name "Your Name"
```

For local experiments you can set `SIGNUP_MODE=open` in `backend/.env` to allow sign-up.

The public marketing website runs separately:

```bash
cd frontend
npx ng serve marketing
```

It opens on **http://localhost:4300**. Its "Log in" button goes to the client portal (the app) on
port 4200. The client-portal screenshots on the site are captured from the app with
`frontend/scripts/capture-marketing-screenshots.mjs` (instructions at the top of the file). The dev server forwards `/api` to the
backend, so the browser sees a single site and the session and CSRF cookies just work.

> Session cookies are marked `Secure`. Chrome, Edge and Firefox accept them on
> `http://localhost`. If your browser doesn't, set `COOKIE_SECURE=false` in `backend/.env`
> for local development only.

### Super Admin and staff access

Super Admins, and Outlogik staff who manage the marketing website, are set up from the command
line only, never through the app:

```bash
cd backend
uv run python -m app.cli create-super-admin --email you@example.com --name "Your Name"
```

```bash
uv run python -m app.cli grant-staff --email colleague@example.com --role content_editor
```

Roles are `content_editor` (website content) and `site_admin` (everything in the admin area).
Remove access with `revoke-staff --email …`.

## Tests and checks

```bash
cd backend
uv run pytest            # 196 tests; rebuilds the outlogik_test schema from the migrations
uv run ruff check .      # lint
uv run alembic check     # migrations match the models
```

```bash
cd frontend
npx ng test frontend --watch=false    # app unit tests (Vitest)
npx ng test marketing --watch=false   # marketing site unit tests
npx ng build frontend                 # production builds; fail if a bundle budget is exceeded
npx ng build marketing                # also prerenders the static pages
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
