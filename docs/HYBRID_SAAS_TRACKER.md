# Hybrid SaaS: implementation tracker

Progress against [`HYBRID_SAAS_PLAN.md`](HYBRID_SAAS_PLAN.md). Each step ends with a report in
the format the spec asks for (§24): what was done, files, database changes, tests, what's
unfinished, security notes, and what's next.

| Step | Status |
|---|---|
| H1-1 Audit and plan | Done, approved 2026-11-18 (decisions D1–D9) |
| H1-2 Account types and workspaces | **Done** (2026-11-18) |
| H1-3 Roles, assignments, access grants, RLS | Next |
| AI Search addendum | Planned 2026-11-18: GEO checks in H1-6, AI referral traffic in H1-7, monitoring as the first H2 module ([`AI_SEARCH_PLAN.md`](AI_SEARCH_PLAN.md)) |
| H1-4 … H1-12 | Not started |

---

## H1-2: Account types and workspaces

### 1. What was completed

- **Merged the website work into `main`** first (chrgomes/Outlogik#4, decision D9).
- **Account types.** Every organization is a **business** or an **agency**.
  - Sign-up asks "Who is the account for?": *My business* or *An agency*. The organization
    name's label follows the choice.
  - The CLI takes `--kind business|agency` (`create-organization`).
  - Existing organizations became agencies (Outlogik works for clients).
  - A business can't create clients: the API refuses (403 `business_account`), and the app
    hides Clients from the sidebar, the dashboard and the website forms. Opening a clients
    URL takes a business to its dashboard.
- **Workspaces.** Marketing data now lives in workspaces.
  - Every organization has exactly one **own** workspace; every agency client has a
    **client** workspace. They're created, renamed and deleted with their organization or
    client, so there's nothing extra to manage.
  - Websites belong to a workspace. An agency can now track **its own websites** too, not
    only clients'.
- **Workspace API.**
  - `GET /orgs/{org}/workspaces` lists the workspaces the caller can open (own first, then
    clients by name, with website counts).
  - `GET /orgs/{org}/workspaces/{id}`, and websites under
    `/orgs/{org}/workspaces/{id}/websites` (list, add, view, edit, move, delete).
  - A shared `require_workspace(permission)` dependency checks the organization, then the
    workspace. Future modules (SEO audits, analytics, reports) plug into it.
  - The existing `/orgs/{org}/websites` endpoints still work, unchanged for current callers.
- **Workspace switcher (agencies).** In the top bar, next to the organization: *All
  workspaces*, *your own marketing*, or a client (archived clients are marked). The choice is
  remembered per organization in the browser. The Websites page follows it; a business never
  sees the switcher.
- **Accessibility fixes found while testing:** dialogs are now named after their heading for
  screen readers (this affected every form dialog), and the role text in an open switcher
  had too little contrast.

### 2. Files changed

**Backend**
- New module `app/modules/workspaces/`: `models.py`, `schemas.py`, `service.py`,
  `context.py` (`require_workspace`), `router.py`.
- `organizations/models.py` (`kind`), `organizations/service.py` (creates the own
  workspace), `organizations/router.py` and `schemas.py` (kind in responses; renames the own
  workspace).
- `clients/service.py` (creates and renames client workspaces; business check).
- `websites/models.py`, `schemas.py`, `service.py`, `router.py` (workspace-aware; new
  workspace routes).
- `auth/schemas.py`, `service.py`, `router.py` (`account_type`; `organization_kind` in
  memberships), `cli.py` (`--kind`), `main.py`, `models.py`.
- Migration `alembic/versions/20261118_0008_account_types_and_workspaces.py`.
- Tests: new `tests/test_workspaces.py`; `conftest.py` (seeded clients get workspaces;
  `register(account_type=…)`); `test_websites.py` (audit key renamed, below).

**App**
- New `core/workspace.service.ts`.
- `core/api.types.ts`, `current-org.service.ts` (`isAgency`), `guards.ts`
  (`agencyGuard`), `org-api.service.ts` (workspace website calls; refreshes the switcher
  after relevant changes), `auth.service.ts`.
- `features/auth/register.ts`, `features/dashboard/dashboard.ts`,
  `features/websites/websites-list.ts`, `website-form-dialog.ts`.
- `layout/nav.ts`, `sidebar/sidebar.ts`, `topbar/topbar.{ts,html,scss}`,
  `shared/dialog/dialog.ts`, `app.routes.ts`.
- Tests: new `features/websites/websites.spec.ts`; additions to the sign-up, sidebar,
  topbar and dashboard specs; `testing/fixtures.ts`.

**Docs:** `ARCHITECTURE.md` (workspaces module, endpoint checklist, data model),
`SECURITY.md` (workspace isolation), this tracker.

### 3. Database changes (migration `0008`)

| Change | Existing data |
|---|---|
| `organizations.kind` (`business` or `agency`, checked), default `agency` | All existing organizations become agencies |
| New table `workspaces`: `organization_id`, `kind` (`own` or `client`), `name`, `client_id` (unique, set only for client workspaces; checked) | One own workspace per organization, one client workspace per client |
| Partial unique index: one own workspace per organization | |
| `websites.workspace_id` (required, indexed, cascades with the workspace) | Filled in from each website's client |
| `websites.client_id` becomes nullable (null in the own workspace) | Kept and kept in step; removed in a later migration once nothing reads it (plan §2) |

- Nothing is deleted. The migration was run **up, checked (`alembic check`), down and up
  again** on a copy of the development database with real records: 2 organizations, 1 client,
  3 websites, all placed correctly.
- **Downgrade** refuses, with a clear message, if any website sits in an own workspace
  (the old schema can't hold it). It never deletes data to make a downgrade work.

### 4. Tests

| Suite | Result |
|---|---|
| Backend (pytest) | **293 passed** (was 271). New: 15 workspace tests, plus the permission matrix covering the 7 new routes automatically |
| App (Vitest) | **93 passed** (was 82) |
| Website (Vitest) | 92 passed (unchanged) |
| Lint (ruff), builds (app) | Clean |
| Migration | Up / check / down / up on a copy of real data |

The new backend tests cover:
- sign-up as business or agency, and rejecting an unknown type
- a business refused clients
- workspaces created, renamed and deleted with their organization or client
- the database refusing a second own workspace
- websites in own and client workspaces, through both the new and the old endpoints
- a website only reachable through its own workspace
- moving websites between workspaces, with an audit entry
- **cross-tenant attempts:** another organization's workspace or website by ID, moving a site
  into another organization's workspace, listing another organization's workspaces
  (all 404, nothing changed)
- portal users seeing only their clients' workspaces, never the agency's own

**Browser check** (Chromium, desktop, against the real API):
- A business signs up, sees no Clients anywhere, adds a website without choosing a workspace,
  and is sent to its dashboard from a clients URL.
- An agency adds two clients; the switcher appears; it adds its own site and three client
  sites; the list filters per workspace and remembers the choice after a reload.
- The switcher works from the keyboard.
- An axe scan of sign-up, Websites and the add dialog found no problems after the two fixes
  above. The one remaining note ("region") is how the menu overlay sits outside the page
  landmarks, and it applies to every menu.

One behaviour change for existing data: the audit entry for moving a website now records
`workspace` (from/to) instead of `client`. Older entries are unchanged.

### 5. Unfinished (on purpose, per the plan)

- **Access grants** (a business letting an agency into its workspace) come in **H1-3**, with
  roles and workspace assignments. Today an agency only works on clients it created.
- **Client users become workspace-level Client Viewers** in H1-3. For now they're still
  linked to clients (`client_users`), which map one-to-one to workspaces.
- The **switcher only affects Websites** for now, because websites are the only
  workspace data so far. The dashboard stays an organization-wide overview. SEO audits,
  analytics and reports (H1-6 to H1-9) will be built on workspaces from the start.
- **No way to change an account's type** after sign-up. It's rarely needed and would need
  rules (e.g. what happens to clients); can be added in H1.5 if asked.
- `websites.client_id` and the organization-level website endpoints are kept until the
  app no longer uses them; removing them is one documented later step.
- **Sign-up stays invitation-only** in production (`SIGNUP_MODE`). Self-serve sign-up behind
  an invitation code is H1-11.

### 6. Security notes

- Workspace access is enforced in the backend by one dependency. The app only hides what
  the API already refuses.
- IDs from another organization are always a 404, the same as an ID that doesn't exist, so
  nothing reveals another tenant's records.
- Moving a website checks the destination workspace with the same rules as reading it.
- Row-level security in PostgreSQL, as a second line of defence, is planned for H1-3. Until
  then isolation relies on the application checks, which the tests cover.
- No new secrets, settings or external services.

### 7. Next: H1-3 roles, assignments, access grants and row-level security

- Role templates by account type (business and agency sets from plan §1.2), mapped from the
  existing four roles.
- Roles that cover all workspaces or only assigned ones ("account managers see their
  clients"), with an assignments table.
- Client users become Client Viewers of a workspace.
- Access grants: a business invites an agency to its workspace, can see and revoke access,
  all audited.
- PostgreSQL row-level security policies on tenant tables, with tests that bypass the
  application layer to prove they hold.
