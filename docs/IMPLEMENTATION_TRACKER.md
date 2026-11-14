# Implementation tracker — Phase 1

Plan: [`PHASE1_PLAN.md`](PHASE1_PLAN.md). Spec: `MASTER_SPEC.md` (not yet in the repo).

| # | Step | Status | Notes |
|---|---|---|---|
| 1 | Scaffold, Docker Compose, health endpoint, Angular shell | ✅ Done | Angular 22, FastAPI, Postgres 16, Redis 7, Mailpit |
| 2 | Database, Alembic, Phase 1 models, first migration | ✅ Done | Migration `0001`; upgrade/downgrade tested; `alembic check` clean |
| 3 | Authentication backend + tests | ✅ Done | 27 auth tests |
| 4 | Organizations, members, invitations + tests | ✅ Done | 37 tests, incl. tenant isolation |
| 5 | Roles and permissions + permission tests | ⏳ Next | Done early: catalogue, default roles, `require(permission)` enforcement. To do: roles API, custom roles, permission tests across every route |
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
- **URL layout:** `GET /api/v1/organizations` lists your organizations. Everything inside one organization (including get/update, members and invitations) is under `/api/v1/orgs/{slug}/…`, so a single dependency resolves and checks the tenant.
- **`POST /auth/invitations/preview`** shows the accept-invite page who invited you to what. It takes the token in the body, not the URL, so tokens stay out of access logs.
- **`POST /orgs/{slug}/leave`**, **`…/invitations/{id}/resend`** added.
- **Organization slugs don't change** when the name changes, so bookmarked links keep working.

## Security behaviour implemented (step 3)

- Argon2id password hashing, with rehash on login when parameters change. Minimum 10 characters.
- Server-side sessions: a random 256-bit token in an HTTP-only, Secure, SameSite=Lax cookie; only its SHA-256 hash is stored.
- Idle timeout (default 24 h) plus absolute lifetime (default 14 days). Login rotates the session.
- Logout, logout-all, and password reset all revoke sessions server-side. Deactivated users lose access at once.
- Double-submit CSRF check on every state-changing `/api/` request.
- Redis rate limits on login (per email and per IP), register, forgot/reset password and resend-verification. If Redis is down the limiter allows requests and logs a warning.
- Login errors don't reveal whether an email exists, and forgot-password always returns 202. Only the newest reset link works, and each link works once.
- Audit entries: register, organization create, login, failed login, logout, logout-all, password reset requested / completed, email verified, Super Admin granted via CLI.

## Organization, member and invitation rules (step 4)

- Requests resolve the organization from the URL slug and require an **active** membership; otherwise **404**, with the same body as a slug that doesn't exist. Suspended organizations return 403 `org_suspended`.
- Each route declares its permission with `require("…")`. Lacking it returns 403 with the permission named in `details`.
- Tenant-owned rows are loaded through `get_scoped()`, which always filters by the active organization. IDs from another organization (members, roles, clients, invitations) return 404.
- **Owners:** only an owner can make someone an owner, invite an owner, or change, disable or remove an owner. The last active owner can't be demoted, disabled, removed, or leave.
- Nobody can change their own role or status (avoids locking yourself out); use **Leave** to leave.
- **Client users vs team:** the Client role and team roles can't be swapped on an existing member — remove them and invite again. Client invitations must name a client in the same organization; others can't.
- **Invitations:** a new invite to the same email replaces the open one; resend issues a new link and kills the old one. Links expire after 7 days and work once. Inviting an existing member returns 409.
- **Accepting:** if the email already has an account, the invitee must be signed in as that account. A new account is created with the email marked verified (they opened the emailed link) and is signed in. Invitations still work when sign-up is invite-only.
- Removing a member also removes their client-portal links in that organization.
- Audit entries: `organization.update`, `member.update` (with from/to), `member.remove`, `member.leave`, `invitation.create` / `resend` / `revoke` / `accept`.

## Known gaps / follow-ups

- Emails are sent synchronously during the request. A Celery queue with retries comes when the first background job is needed.
- Behind a reverse proxy, uvicorn must run with `--proxy-headers` so rate limits and audit IPs see the real client address.
- `docker compose up` was validated (`docker compose config`) but not run in the build environment, which had no Docker daemon. Tests ran against local PostgreSQL 16 and Redis 7.
