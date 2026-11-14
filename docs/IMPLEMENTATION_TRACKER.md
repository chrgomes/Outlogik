# Implementation tracker — Phase 1

Plan: [`PHASE1_PLAN.md`](PHASE1_PLAN.md). Spec: `MASTER_SPEC.md` (not yet in the repo).

| # | Step | Status | Notes |
|---|---|---|---|
| 1 | Scaffold, Docker Compose, health endpoint, Angular shell | ✅ Done | Angular 22, FastAPI, Postgres 16, Redis 7, Mailpit |
| 2 | Database, Alembic, Phase 1 models, first migration | ✅ Done | Migration `0001`; upgrade/downgrade tested; `alembic check` clean |
| 3 | Authentication backend + tests | ✅ Done | 27 auth tests |
| 4 | Organizations, members, invitations + tests | ⏳ Next | Includes `accept-invite` |
| 5 | Roles and permissions + permission tests | ◐ Partly | Catalogue, default roles and startup sync done; enforcement dependency and role API to do |
| 6 | Clients and websites + tenant isolation tests | ☐ | |
| 7 | Frontend: brand, themes, layout shell | ☐ | Needs logo files |
| 8 | Frontend: authentication pages | ☐ | |
| 9 | Frontend: clients, websites, settings pages | ☐ | |
| 10 | Dashboard (backend + frontend) | ☐ | |
| 11 | Docs, tracker, final test pass | ☐ | |

## Changes from the plan

Small additions made while building. None change an approved decision.

- **`email_verification_tokens` table.** The plan lists email verification as a flow but had no table for its tokens. Same shape as `password_reset_tokens`; stored as hashes.
- **`roles.system_key`** (`owner` / `admin` / `member` / `client`): a stable key for system roles, so code doesn't depend on display names that owners may want to translate or rename.
- **`invitations.invited_by_user_id` and `invitations.revoked_at`**: who sent an invite, and support for cancelling one.
- **`users.last_login_at`**, and **`users.mfa_secret` / `mfa_enabled_at`** reserved for optional MFA.
- **`organization_members.role_id`** uses `ON DELETE RESTRICT`, so a role still assigned to members can't be deleted.
- **CSRF cookie/header names** are `XSRF-TOKEN` / `X-XSRF-TOKEN`, Angular's built-in names.
- **`POST /auth/resend-verification`** and **`GET /auth/csrf`** added to the auth API.

## Security behaviour implemented (step 3)

- Argon2id password hashing, with rehash on login when parameters change. Minimum 10 characters.
- Server-side sessions: a random 256-bit token in an HTTP-only, Secure, SameSite=Lax cookie; only its SHA-256 hash is stored.
- Idle timeout (default 24 h) plus absolute lifetime (default 14 days). Login rotates the session.
- Logout, logout-all, and password reset all revoke sessions server-side. Deactivated users lose access at once.
- Double-submit CSRF check on every state-changing `/api/` request.
- Redis rate limits on login (per email and per IP), register, forgot/reset password and resend-verification. If Redis is down the limiter allows requests and logs a warning.
- Login errors don't reveal whether an email exists, and forgot-password always returns 202. Only the newest reset link works, and each link works once.
- Audit entries: register, organization create, login, failed login, logout, logout-all, password reset requested / completed, email verified, Super Admin granted via CLI.

## Known gaps / follow-ups

- Emails are sent synchronously during the request. A Celery queue with retries comes when the first background job is needed.
- Behind a reverse proxy, uvicorn must run with `--proxy-headers` so rate limits and audit IPs see the real client address.
- `docker compose up` was validated (`docker compose config`) but not run in the build environment, which had no Docker daemon. Tests ran against local PostgreSQL 16 and Redis 7.
