# Outlogik — Phase 1 Plan (Foundation)

Status: **Approved 2026-11-14.** Progress is tracked in `docs/IMPLEMENTATION_TRACKER.md`.
Source of truth: `docs/MASTER_SPEC.md`.

---

## 1. Scope

**In Phase 1**

- Project scaffolding: Angular, FastAPI, PostgreSQL, Redis, Docker Compose
- Monochrome brand, light and dark themes, collapsible sidebar layout
- Authentication: register, login, logout, sessions, password reset, invitations
- Multi-tenant organizations, members, clients, websites
- Roles and permissions, enforced in the backend
- Main dashboard framework, showing only real internal records
- Audit logging for sensitive actions
- Tests for auth, permissions and tenant isolation
- Initial documentation and an implementation tracker

**Not in Phase 1**

- Google, Bing or social integrations (Phase 2+)
- SEO tool containers: SEOnaut, Lychee, Unlighthouse, Umami (Phase 2)
- Crawl4AI (Phase 2)
- Public website (Phase 1.5)
- Billing, subscriptions, Super Admin console UI (later phases)
- MFA (optional; the schema leaves room for it)

---

## 2. Repository structure

```
outlogik/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, routers, middleware
│   │   ├── core/                   # config, security, db session, errors
│   │   ├── tenancy/                # org context + tenant-scoped query helpers
│   │   ├── modules/
│   │   │   ├── auth/               # register, login, sessions, reset
│   │   │   ├── users/
│   │   │   ├── organizations/      # orgs, members, invitations
│   │   │   ├── rbac/               # roles, permissions, checks
│   │   │   ├── clients/
│   │   │   ├── websites/
│   │   │   ├── dashboard/
│   │   │   └── audit/
│   │   └── cli.py                  # e.g. create-super-admin
│   ├── alembic/                    # migrations
│   ├── tests/
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── core/               # auth service, guards, interceptors
│       │   ├── layout/             # shell, sidebar, topbar
│       │   ├── features/           # auth, dashboard, clients, websites, settings
│       │   └── shared/             # UI components, pipes
│       ├── assets/brand/           # logos (light + dark)
│       └── styles/                 # SCSS tokens, themes, Bootstrap overrides
├── docs/                           # MASTER_SPEC.md + project docs
├── docker-compose.yml
├── THIRD_PARTY_LICENSES
└── README.md
```

The backend is a **modular monolith**. Each module owns its models, schemas, service and router.

---

## 3. Local development setup (Windows + WSL2)

| Runs in Docker (docker-compose.yml) | Runs directly in WSL2 Ubuntu |
|---|---|
| PostgreSQL 16 | FastAPI (`uvicorn --reload`) |
| Redis 7 | Celery worker (added when first needed) |
| Mailpit (dev-only email inbox) | Angular (`ng serve`) |

- Running the app itself outside Docker keeps hot-reload fast during development.
- **Mailpit** (MIT) catches outgoing emails (invites, password resets) so they can be tested without a real email provider. *Needs your approval, since it isn't on the approved container list.*

---

## 4. Authentication design

- **Password hashing:** Argon2id.
- **Sessions:** server-side sessions stored in PostgreSQL (`user_sessions`). The browser holds only a random session ID in an **HTTP-only, Secure, SameSite=Lax cookie**.
  - Why not JWT: sessions can be revoked instantly (logout everywhere, disable a user), and no token ever lives in JavaScript.
- **CSRF protection:** double-submit token. An Angular interceptor sends it on every state-changing request.
- **Rate limiting:** login, register and password-reset endpoints, using Redis.
- **Session expiry:** idle timeout plus an absolute maximum lifetime.
- **Flows:** register (creates a user + a new agency organization), login, logout, logout-all, forgot/reset password, email verification, accept invitation.
- **Super Admin:** a flag on the user, created only through a backend CLI command, never through the UI.

---

## 5. Multi-tenancy and permissions

**Tenant isolation**

- Every tenant-owned table has an `organization_id`.
- Each request resolves the active organization from the URL and checks that the user is a member. If not, the API returns **404**, so it never confirms that another organization's records exist.
- All tenant data goes through scoped query helpers that always filter by `organization_id`.
- Tenant isolation tests try to read and change other organizations' data and must fail.
- *Option for later:* PostgreSQL row-level security as a second layer of protection.

**Roles and permissions**

- Permissions are fine-grained strings, e.g. `clients.read`, `clients.write`, `members.invite`, `websites.delete`.
- Default roles per organization: **Owner, Admin, Team Member, Client**. Owners can create custom roles.
- **Client users** are linked to specific clients (`client_users`) and only see those clients' records.
- Every endpoint declares the permission it needs; the backend checks it. The frontend hides buttons too, but only for convenience.

---

## 6. Phase 1 database tables

| Table | Purpose | Key fields |
|---|---|---|
| `users` | Accounts | email (unique), password_hash, full_name, is_super_admin, is_active, email_verified_at |
| `organizations` | Agency workspaces | name, slug (unique), status (active/suspended) |
| `organization_members` | User ↔ org link | organization_id, user_id, role_id, status |
| `roles` | Default + custom roles | organization_id, name, is_system |
| `permissions` | Permission catalogue | code (unique), description |
| `role_permissions` | Role ↔ permission | role_id, permission_id |
| `user_sessions` | Server-side sessions | user_id, token_hash, expires_at, last_seen_at, ip, user_agent |
| `invitations` | Team + client invites | organization_id, email, role_id, client_id (optional), token_hash, expires_at, accepted_at |
| `password_reset_tokens` | Reset links | user_id, token_hash, expires_at, used_at |
| `clients` | Agency's clients | organization_id, name, contact_email, status, notes |
| `client_users` | Client-portal access | organization_id, client_id, user_id |
| `websites` | Client websites | organization_id, client_id, name, url, domain, status |
| `audit_logs` | Sensitive-action log | organization_id, actor_user_id, action, target_type, target_id, metadata, ip, created_at |

- All tables use UUID primary keys and `created_at` / `updated_at` timestamps.
- Tokens (session, invite, reset) are stored only as hashes.
- Projects and domains from the spec are deferred until a module needs them.

---

## 7. API (v1) for Phase 1

- `/api/v1/auth` — register, login, logout, logout-all, me, forgot-password, reset-password, verify-email, accept-invite
- `/api/v1/organizations` — list mine, get, update, members, invitations
- `/api/v1/orgs/{slug}/roles` — list, create, update; permission catalogue
- `/api/v1/orgs/{slug}/clients` — CRUD, client users
- `/api/v1/orgs/{slug}/websites` — CRUD
- `/api/v1/orgs/{slug}/dashboard` — summary counts + recent activity
- `/api/v1/health` — liveness/readiness

All endpoints get consistent error responses, pagination, filtering, sorting, and OpenAPI docs.

---

## 8. Frontend

- Angular standalone components with signals, Reactive Forms and route guards.
- **Routes:** `/login`, `/register`, `/forgot-password`, `/reset-password`, `/accept-invite`, then `/o/:orgSlug/` → dashboard, clients, websites, settings (organization, members, roles).
- **Layout:** collapsible sidebar (symbol-only logo when collapsed), top bar with organization switcher, theme toggle, user menu.
- **Brand:** monochrome SCSS design tokens, light and dark themes, Bootstrap 5 customized on top.
- **Dashboard:** real counts (clients, websites, team members), recent activity from the audit log, and clearly labelled "Not connected yet" cards for Phase 2 metrics. No fake numbers.
- **States:** consistent loading, empty, success and error states.
- **Charts:** Apache ECharts is added in Phase 2, when there's real data to chart.

---

## 9. Build order (small, runnable steps)

1. Repo scaffold, Docker Compose (PostgreSQL, Redis, Mailpit), FastAPI health endpoint, Angular app shell
2. Database setup, Alembic, Phase 1 models and first migration
3. Authentication backend + tests
4. Organizations, members and invitations + tests
5. Roles and permissions + permission tests
6. Clients and websites + tenant isolation tests
7. Frontend: brand, themes, layout shell
8. Frontend: authentication pages
9. Frontend: clients, websites and settings pages
10. Dashboard (backend + frontend)
11. Documentation, implementation tracker, final test pass

Each step ends with the app running and the tests passing, committed to a feature branch.

---

## 10. Decisions (approved 2026-11-14)

1. **Sessions:** server-side sessions in HTTP-only cookies, not JWT.
2. **Mailpit:** approved as a dev-only email container.
3. **Sign-up:** open sign-up (anyone can register a new agency), matching the spec's end-to-end test flow. Can be switched to invite-only with a config flag.
4. **Tenant isolation:** app-level scoping + isolation tests now; PostgreSQL row-level security later.
5. **GitHub repo:** `chrgomes/Outlogik`. Work is pushed to feature branches.
