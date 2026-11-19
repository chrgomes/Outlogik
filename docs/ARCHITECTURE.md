# Architecture

How Outlogik is put together, and the rules to follow when extending it. For the security
model in detail, see [`SECURITY.md`](SECURITY.md).

## Overview

```
Browser ── Angular app ──/api──▶ FastAPI ──▶ PostgreSQL (all data)
                                   │
                                   ├──▶ Redis (rate limits)
                                   └──▶ SMTP (Mailpit locally)
```

In development, the Angular dev server proxies `/api` to FastAPI, so the browser sees one
origin. Production should do the same with a reverse proxy: the cookies are `SameSite=Lax` and
the CSRF check relies on same-origin requests.

## Backend (`backend/app`)

A **modular monolith**: one deployable app, split into modules that each own their models,
schemas, service functions and router.

| Path | Responsibility |
|---|---|
| `core/` | Settings, database session, base model and mixins, password and token hashing, error format, CSRF, security headers, rate limiting, email, pagination |
| `tenancy/` | Resolves the organization from the URL and checks access (`context.py`); query helpers that always filter by organization (`scoped.py`) |
| `modules/auth` | Register, login, sessions, password reset, email verification, accepting invitations |
| `modules/users` | The `User` model |
| `modules/organizations` | Organizations, members, invitations |
| `modules/rbac` | Permission catalogue, built-in roles, custom roles, escalation guard |
| `modules/workspaces` | Workspaces (an organization's own, and one per agency client), the workspace list API, `require_workspace(...)` for `/orgs/{slug}/workspaces/{id}/…` routes, and member workspace assignments |
| `jobs/` and `worker.py` | Background jobs: the `jobs` table, `enqueue()`, retries, recovery, the job kinds (`jobs/handlers.py`), and the Celery worker with its schedule |
| `modules/audits` | Website audits: the safe fetcher (`fetch.py`), page reader (`parse.py`), crawler, the check catalogue (`checks.py`), PageSpeed, the audit job, schedules and comparison |
| `modules/integrations` | Outside accounts connected to a workspace (Google): sign-in with PKCE (`service.py`), every Google call (`google.py`), encrypted tokens (`crypto.py`), the GA4 and Search Console syncs (`sync.py`) and the traffic summary (`summary.py`) |
| `modules/plans` | Plans, their limits, subscriptions and trials; `check_limit(...)`, called by the services that add websites, clients and team members |
| `modules/grants` | Access grants: a business shares its workspace with an agency (send, accept, revoke, disconnect) |
| `modules/clients`, `modules/websites` | Clients, client-portal access, websites and URL validation |
| `modules/dashboard` | Dashboard counts and recent activity |
| `modules/audit` | The append-only audit log |
| `modules/site` | Marketing site settings and product module statuses (public and admin API) |
| `platform.py` | Outlogik staff roles (`content_editor`, `site_admin`) and `require_staff(...)` for `/api/v1/admin/...` |
| `cli.py` | Admin commands (create a Super Admin, create an organization with `--kind business` or `agency`, grant or revoke staff roles, sync permissions) |

Conventions:

- **Sync SQLAlchemy 2** with psycopg 3. FastAPI runs sync endpoints in a thread pool.
- **UUID primary keys** and `created_at` / `updated_at` on every table.
- **Errors** are always `{"error": {"code", "message", "details"}}`. Raise `AppError`,
  `NotFound`, `Forbidden`, `Conflict` or `Unauthorized` from `core/errors.py`. Validation
  errors list `{field, message}` in `details`, which the frontend maps onto form fields.
- **Lists** return `{items, total, page, page_size}` and accept `page`, `page_size` (max 100),
  `sort` (`name` or `-name`, from a whitelist) and filters. Use `core/pagination.py`.
- **Audit:** call `audit.service.record(...)` in the same transaction as the change.
- **Startup** syncs the permission catalogue and every organization's built-in roles.

### Checklist: adding an organization endpoint

1. Put it under `/api/v1/orgs/{org_slug}/…` in the module's router. Marketing data that
   belongs to a workspace goes under `/api/v1/orgs/{org_slug}/workspaces/{workspace_id}/…`
   and depends on `require_workspace("<permission>")` instead, which also loads the
   workspace (404 if the caller can't see it).
2. Depend on `require("<permission>")`. Add new permissions to `rbac/catalogue.py` and decide
   which built-in roles get them; startup applies the change to every organization.
3. Load rows with `get_scoped()` / `scoped_select()`, or `get_visible()` plus
   `client_visibility()` / `workspace_visibility()` for anything tied to a client or workspace,
   so members limited to assigned workspaces only see theirs. Never query tenant tables by ID
   alone. A new tenant table also needs a row-level security policy (see migration 0012).
4. Record an audit entry for any change.
5. Add tests: behaviour, and a member limited to assigned workspaces where relevant.
   `test_cross_tenant.py` attacks every new route with another organization's ids
   automatically, and fails until it knows each new kind of id. `test_permission_matrix.py` checks the new route's
   permission automatically.

### API surfaces

| Prefix | Who | Notes |
|---|---|---|
| `/api/v1/auth`, `/api/v1/organizations`, `/api/v1/orgs/{slug}/…` | Signed-in users | Organization permissions, tenant isolation |
| `/api/v1/public/…` | Anyone (the marketing site) | No sign-in; only data meant to be public; cacheable |
| `/api/v1/admin/…` | Outlogik staff | `require_staff(...)`; everyone else gets 404; a test checks every route |

## Frontend workspace (`frontend/`)

One Angular workspace with two projects that build and deploy separately:

| Project | Path | What it is |
|---|---|---|
| `frontend` | `src/` | The signed-in app (single-page app) |
| `marketing` | `projects/marketing/src/` | The public website: server-rendered per request with `@angular/ssr` (cached 60 s), served by Express (`src/server.ts`), which also forwards `/api/public/*` to the API (`API_INTERNAL_URL`) |

Shared brand code lives in `brand/` and is imported as `@brand/...`: the palette
(`brand/scss/_palette.scss`), logo and icon components, and logo and icon assets. Each site
provides its own icon set with `provideIcons(...)`.

Commands: `npx ng serve frontend` (port 4200) and `npx ng serve marketing` (port 4300);
`npx ng test <project>`; `npx ng build <project>`.

## App (`frontend/src`)

| Path | Responsibility |
|---|---|
| `app/core/` | Auth state (`AuthService`), current organization and permissions (`CurrentOrgService`), API writes (`OrgApi`), route guards, session interceptor, theme, layout state, API error mapping |
| `app/layout/` | Signed-in shell (sidebar, top bar, email banner) and the centred layout for sign-in pages |
| `app/features/` | One folder per area: `auth`, `dashboard`, `clients`, `websites`, `settings`, `system` |
| `app/shared/` | Icons, logo, page header, empty/loading/error states, dialogs, toasts, forms, table parts, `*olCan` |
| `styles/` | Design tokens (`_tokens.scss`), light and dark themes (`_theme.scss`), base and shared component styles |
| `testing/` | Test fixtures and helpers |

Conventions:

- **Standalone components, signals, `OnPush`, zoneless.** New Angular file naming
  (`clients-list.ts`, no `.component` suffix).
- **Reading data:** `httpResource` in the component, with the URL from `OrgApi.url()`. Every
  list handles loading, error (with retry), empty and no-results states.
- **Writing data:** `OrgApi` methods, then `toast.success(...)`, or `toast.error(apiProblem(err).message)`.
  In forms, `applyFieldErrors()` puts API validation errors on the right fields.
- **Permissions in templates:** `*olCan="'clients.write'"` or `org.can(...)`, for showing and
  hiding only. Use `org.isOwner()` / `org.isClientUser()` rather than role names.
- **Pages load on demand** (`loadComponent` in `app.routes.ts`) behind `permissionGuard`.
- **Colours** come from CSS variables (`--ol-text`, `--ol-surface`, …), never raw hex in
  components, so both themes work.
- **Dialogs** use `DialogService.open()`; destructive actions use `confirm()` (with
  `typeToConfirm` when data is lost).

### Checklist: adding a page

1. Create the component in `app/features/<area>/` and add a lazy route with
   `canActivate: [permissionGuard]` and `data: { permission }`.
2. Add it to `layout/nav.ts` if it belongs in the sidebar (hidden by permission).
3. Use `ol-page-header`, the shared states, and `ol-pager` / `ol-search` for lists.
4. Add unit tests for permission-dependent behaviour, and check it at phone width in both
   themes.

## Data model

```
users ─┬─ user_sessions, password_reset_tokens, email_verification_tokens
       └─ organization_members ─┬─ organizations (kind: business | agency)
                                │    ├─ roles ── role_permissions ── permissions
                                │    ├─ invitations
                                │    ├─ clients ── workspaces (kind client, one per client)
                                │    ├─ workspaces (kind own, exactly one) ─┬─ websites
                                │    │                                       ├─ workspace_assignments ── organization_members
                                │    │                                       └─ workspace_grants ── agency organizations
                                │    └─ audit_logs
                                └─ roles
```

- **Organizations** are the tenant: team, roles and (later) the subscription belong to them. A
  **business** markets itself; an **agency** also works for clients.
- **Workspaces** hold marketing data. Every organization has one `own` workspace; each agency
  client has a `client` workspace. Both are created and renamed with their organization or
  client; deleting a client deletes its workspace and websites.
- **Websites** belong to a workspace (`workspace_id`). `websites.client_id` is kept in step
  (null in the own workspace) until every reader has moved to `workspace_id`
  (docs/HYBRID_SAAS_PLAN.md §2).
- Business accounts can't create clients (403 `business_account`).
- **Roles** are built in per account type (rbac/catalogue.py): Owner, Administrator,
  Marketing Manager and Reporting Viewer for everyone; agencies also get Account Manager and
  Client Viewer. A role sees every workspace (`workspace_scope = all`) or only the ones each
  member is assigned (`assigned`, stored in `workspace_assignments`). The startup sync adds new
  built-in roles to existing organizations and keeps names and permissions current.
- **Access grants** (`workspace_grants`) let a business share its own workspace with an
  agency. The agency's requests then include that workspace (`OrgContext.linked`), with
  "manage" or "view" access. Websites created there belong to the business.
- **Plans** (`plans`, `plan_entitlements`, `subscriptions`; migration 0013): limit keys are
  defined in `plans/catalogue.py`, values in the database. Each organization has one
  subscription: a 14-day trial of the top plan at sign-up, or a plan set by staff. Limits are
  checked by the services when something is added (never by the interface), against live
  counts. After a trial ends, or when cancelled, nothing new can be added; nothing is removed.
  A new limit (for example, audits per month) is a catalogue entry, a migration adding values
  to the plans, and a `check_limit` call where the thing is created.
- **Background jobs** (`jobs` table, migration 0014; `app/jobs`, `app/worker.py`):
  - `enqueue(kind, payload, dedupe_key=…)` records a job in its own transaction and hands it
    to the worker. A `dedupe_key` stops the same work being queued twice.
  - The worker claims a job with one UPDATE, so a message delivered twice runs once.
  - A failure is retried with a growing wait (30 s, 2 min, 8 min…) up to the kind's
    `max_attempts`, then the job is `dead`, kept for a person to retry.
  - `JOBS_MODE=inline` (development, tests) runs jobs straight away in the same process;
    `queue` (staging, production) uses the Celery worker, started with
    `celery -A app.worker worker --beat`.
  - Schedule: `jobs.recover` every 5 minutes (stuck or lost jobs), `maintenance.cleanup`
    nightly (expired sessions and tokens, finished jobs after 30 days).
  - Email always goes through a job (`email.send`). A kind's `scrub` removes sensitive payload
    once it's done.
  - **To add a kind:** a function with `@handler("area.thing")` in `jobs/handlers.py` (or the
    module's own file, imported there), then `enqueue("area.thing", {...})` where it's needed.
    Handlers get a session with no organization set, so they filter by organization themselves.
- **Website audits** (`audits`, `audit_pages`, `audit_issues`, `usage_records`; migration 0015):
  - An audit runs as a background job (`audit.run`, up to 50 minutes): crawl, then checks,
    then PageSpeed if a key is set. One at a time per website.
  - Each check in `checks.py` has a severity, an area (technical, SEO, AI search readiness),
    and the "why it matters" and "how to fix it" text shown in the app.
  - An audit belongs to the organization that owns the website, and counts against that
    organization's plan (`limits.audits_per_month`, metered per UTC month in
    `usage_records`; `limits.pages_per_audit` caps each crawl).
  - Websites can be audited weekly or monthly (`audits.schedule`, nightly).
  - **To add a check:** an entry in `CHECKS` and the code that appends `Found(...)` in
    `run_checks()`, with a test page in `tests/test_audits.py`.
  - **Anything that fetches another website goes through `audits/fetch.py`**, never a plain
    HTTP client (see SECURITY.md).
- **Google integration** (`integrations`, `data_sources`, `ga4_daily`, `ga4_breakdowns`,
  `gsc_daily`, `gsc_queries`; migration 0016):
  - One Google connection per workspace, with at most one GA4 property and one Search Console
    site (`data_sources`). Only what the connected account can see may be chosen.
  - Syncs run as jobs (`integrations.sync`; nightly `integrations.sync_all` at 05:23 Toronto):
    90 days the first time, then the last 7 days replaced each night. Synced days are kept as
    daily rows ("snapshots"), so reports don't call Google.
  - Visits from AI tools are GA4 sessions whose source is an AI assistant's site
    (`AI_SOURCES` in `sync.py`: ChatGPT, Perplexity, Gemini, Copilot, Claude, You.com).
  - `GET /orgs/{slug}/workspaces/{id}/analytics/summary?days=28` compares the period with the
    one before; the comparison is left out unless that earlier period was fully synced.
  - Tests use a fake Google (`tests/test_integrations.py`, `google.TRANSPORT`) that answers with
    the real APIs' paths and JSON shapes.
- **Row-level security** (migration 0012) backs all of this up in Postgres. `get_org_context`
  calls `core.db.set_tenant`, which sets `app.org_id` and `app.linked_ws` at the start of each
  transaction for the rest of the request.

Every tenant-owned table has `organization_id`. Migrations are in `backend/alembic/versions`
(`0001` initial schema … `0008` account types and workspaces … `0010` role scope and
assignments, `0011` access grants, `0012` row-level security).
