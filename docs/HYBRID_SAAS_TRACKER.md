# Hybrid SaaS: implementation tracker

Progress against [`HYBRID_SAAS_PLAN.md`](HYBRID_SAAS_PLAN.md). Each step ends with a report in
the format the spec asks for (§24): what was done, files, database changes, tests, what's
unfinished, security notes, and what's next.

| Step | Status |
|---|---|
| H1-1 Audit and plan | Done, approved 2026-11-18 (decisions D1–D9) |
| H1-2 Account types and workspaces | **Done** (2026-11-18) |
| H1-3 Roles, assignments, access grants, RLS | **Done** (2026-11-18) |
| AI Search addendum | Planned 2026-11-18: GEO checks in H1-6, AI referral traffic in H1-7, monitoring as the first H2 module ([`AI_SEARCH_PLAN.md`](AI_SEARCH_PLAN.md)) |
| H1-4 Plans and limits | **Done** (2026-11-18) |
| H1-5 Background jobs | Next |
| H1-6 … H1-12 | Not started |

---

## H1-4: Plans and limits

### 1. What was completed

- **Plans.** The six approved plans, in CAD:
  - Digital Starter, Growth and Professional, for businesses
  - Agency Starter, Professional and Business, for agencies
  - Monthly and annual (20% off, paid upfront) prices, with limits on websites, clients and
    team members, exactly as approved.
- **14-day free trial** for every new sign-up, on the top plan for its account type
  (Digital Professional or Agency Business), until sign-up lets people choose a plan
  (H1-11). Existing organizations, all set up by Outlogik, start on the top plan.
- **Limits enforced by the server** when something is added:
  - **Websites and clients:** archived ones don't count, and restoring one counts again.
  - **Team members:** active members plus open invitations count. Client-portal users and
    disabled members don't; re-enabling someone counts again.
  - **An agency adding a website to a business's shared workspace** counts against the
    business's plan.
  - **The message names the plan and its limit,** e.g. "The Digital Starter plan includes 1
    website. Contact Outlogik to move to a bigger plan."
- **After a trial ends (or if cancelled),** nothing is deleted and everything can still be
  viewed and edited; only adding new things is refused, with a clear message.
- **Settings → Plan** (owners and administrators) shows:
  - the plan, its status and its price (monthly, or the annual amount with its monthly
    equivalent)
  - the trial's end date
  - usage against each limit, with bars
- **A banner** in a trial's last week, and after it has ended.
- **Plans assigned by hand** with `python -m app.cli set-plan` (and `create-organization
  --plan`), until the Super Admin area (H1-11) and billing (H3).
- **Two small display fixes found in the browser check:** a missing icon, and the status
  badge's colours.

**Deliberately not in H1-4:**
- Monthly usage records for metered limits (SEO audits, AI Search). They come with the
  first module that needs them (H1-6), so there's no unused table. Websites, clients and
  team members are counted live.
- Billing, invoices and payment (H3).
- Subscription terms on the website (H1.5, with the pricing page).

### 2. Files changed

**Backend:**
- New module `plans/` (`catalogue.py`, `models.py`, `service.py`, `schemas.py`,
  `router.py`).
- Limit checks in `websites/service.py`, `clients/service.py`,
  `organizations/invitations.py` and `organizations/members.py`.
- `organizations/service.py` (trial or plan at creation), `rbac/catalogue.py` (`plan.read`),
  `cli.py` (`set-plan`, `--plan`), `main.py`, `models.py`.
- Migration `0013`.
- Tests: new `test_plans.py`; `test_row_level_security.py` covers subscriptions;
  `conftest.py` keeps the seeded plans between tests.

**App:**
- New `core/plan.service.ts`, `features/settings/plan.ts` (and spec),
  `layout/plan-banner/plan-banner.ts`.
- `core/api.types.ts`, `layout/nav.ts`, `layout/shell/shell.ts`, `app.routes.ts`, and the
  app icon set (`scripts/build-icons.mjs`, `brand/icon/`).

**Docs:** `ARCHITECTURE.md`, `DEPLOYMENT.md` (§7: giving an organization a plan),
`README.md`, `HYBRID_SAAS_PLAN.md`, this tracker.

### 3. Database changes (migration `0013`)

| Change | Existing data |
|---|---|
| `plans`: key, name, account type, currency, monthly and annual price (cents) | The six approved plans |
| `plan_entitlements`: plan, limit key, value (a number, or null for unlimited) | Websites, clients and team-member limits for each plan |
| `subscriptions`: one per organization; plan, status, monthly/annual, trial end, source (manual) | Every existing organization: active, top plan for its type |
| Row-level security on `subscriptions` (an agency can also read the plan of a business that shared a workspace with it) | None |

The migration was run up, checked, down and up again; the test suite builds from it.

### 4. Tests

| Suite | Result |
|---|---|
| Backend (pytest) | **353 passed** (was 337) |
| App (Vitest) | **113 passed** (was 106) |
| Website (Vitest) | 92 passed (unchanged) |

The new tests cover:
- the trial (plan and length)
- the Plan endpoint (prices, limits, usage; hidden from roles without it)
- each limit, including archived items not counting and restoring counting again
- team counting (open invitations count, client-portal users don't, a counted invitation can
  still be accepted, re-enabling counts)
- unlimited values, trial ended and cancelled
- plan changes recorded and checked against the account type, and the command line
- a shared workspace counting against the business's plan
- subscriptions under row-level security
- in the app: the Plan page (usage, at-limit, annual price, trial dates) and the banner
  (shown only in a trial's last week or after it, and only to people who can see the plan)

**Browser check** (Chromium, against the real API):
- A new business sees its trial on the Plan page.
- After `set-plan` to Digital Starter (annual), a second website is refused in the dialog,
  with the plan's message.
- The Plan page shows "1 of 1" in red and $278.40 a year ($23.20 a month).
- The banner appears with 3 trial days left, and changes once the trial has ended.
- No page errors. An axe scan of the Plan page found no problems in light or dark mode.

### 5. Unfinished (on purpose)

- **Changing plans is done by Outlogik staff** (command line) until the Super Admin area
  (H1-11); customers email sales@outlogik.com.
- **Nothing reminds anyone by email** before a trial ends. That comes with notifications
  (H1.5).
- **Lowering a plan below current usage is allowed:** nothing is removed, but nothing more
  can be added until usage is under the new limit.

### 6. Security notes

- **Limits are enforced only in the backend services;** the app just shows them.
- **Only owners and administrators can see the plan and its prices** (`plan.read`). Client
  Viewers, Account Managers and Marketing Managers can't.
- **Subscriptions are under row-level security** like the other tenant tables.
- **Plans can't be changed through the API yet:** only staff, with the command line.

### 7. Next: H1-5 background jobs

Celery and beat with Redis:
- a jobs table, retries, and duplicate prevention
- email moved onto the queue
- the base for scheduled audits (H1-6) and syncs (H1-7)

---

## H1-3: Roles, assignments, access grants and row-level security

### 1. What was completed

- **Built-in roles by account type.**
  - Everyone gets: **Owner**, **Administrator**, **Marketing Manager** (was Team Member),
    **Reporting Viewer** (new, read-only).
  - Agencies also get: **Account Manager** (new, works only on assigned clients) and
    **Client Viewer** (was Client).
  - Existing organizations got the new roles and names automatically at startup. If a custom
    role already used one of the new names, the built-in role kept its old name.
- **Roles that see only assigned workspaces.** Any role, built-in or custom, either sees
  every workspace or only the ones each person is given. Everything follows it: the workspace
  switcher, clients, websites and dashboard counts. Assignments are made per person from the
  Team page ("Choose workspaces…").
- **Client-portal users are now workspace assignments.** Every existing client-portal link was
  carried over; linking a client user from a client's page works as before.
- **Business-to-agency access grants (spec §4.C).**
  - A business sends access to someone at an agency by email, as "can make changes" or
    "view only".
  - That person accepts it into one of their agencies (owners and administrators only). The
    business then shows in the agency's workspace switcher under **Linked businesses**.
  - The agency works on the business's websites in place; nothing is copied, and websites stay
    the business's.
  - Either side can end it (business: Settings → Agency access; agency: Settings → Linked
    businesses). Access stops at once.
  - Every step is in both organizations' activity logs.
- **Row-level security in Postgres:** a second, independent wall between organizations (see
  section 6).
- **An automated cross-organization attack suite** over every route that takes an id.
- **A bug fixed along the way:** the sidebar links to Organization, Team and Roles had pointed
  to "Page not found" since Phase 1 (their path's slash was encoded). Found while testing in
  the browser; fixed, with a test.

**Deliberately left out of H1-3** (no placeholders):
- Specialist roles (SEO Specialist, Content Creator, …): today they'd have identical
  permissions. Each comes with the module that sets it apart.
- Platform staff roles (platform, support, billing admin): moved to H1-11, with the Super
  Admin area they'd control.

### 2. Files changed

**Backend**
- `rbac/catalogue.py` (roles per account type, scopes, two new permissions),
  `rbac/service.py` (account-type role creation; startup sync adds, renames and updates
  built-in roles; escalation check covers scope), `rbac/models.py`, `rbac/roles.py`,
  `rbac/router.py`, `rbac/schemas.py`.
- `tenancy/context.py` (visible workspaces from assignments; linked workspaces; sets the
  database tenant), `tenancy/scoped.py` (`workspace_visibility`).
- `core/db.py` (`set_tenant`, per-transaction settings, startup check), `main.py`.
- New `workspaces/assignments.py`; `workspaces/models.py` (`WorkspaceAssignment`),
  `service.py`, `context.py` (view-only check), `router.py`, `schemas.py`.
- New module `grants/` (models, schemas, service, router).
- `websites/service.py` (linked workspaces, both-organization audit, owner-based URL
  uniqueness), `clients/service.py` (portal users via assignments),
  `organizations/members.py`, `organizations/invitations.py`, `organizations/schemas.py`,
  `dashboard/service.py`, `auth/schemas.py`, `auth/service.py`.
- Migrations `0010`, `0011`, `0012`.
- Tests: new `test_workspace_roles.py`, `test_access_grants.py`,
  `test_row_level_security.py`, `test_cross_tenant.py`; updated role names in existing tests.
- `.github/workflows/ci.yml`: tests run as an ordinary database user.

**App**
- New `features/access/` (`agency-access.ts`, `accept-access.ts`, `linked-businesses.ts`,
  specs), `features/settings/member-workspaces-dialog.ts`.
- `core/` (types, `current-org.service.ts`, `guards.ts`, `org-api.service.ts`,
  `workspace.service.ts`), `app.routes.ts`, `layout/` (nav, sidebar, topbar),
  `features/settings/` (role editor, roles, team, organization), `features/websites/`,
  `shared/table/table-parts.ts`.

**Docs:** `ARCHITECTURE.md`, `SECURITY.md`, `DEPLOYMENT.md` (§4: ordinary database user),
`HYBRID_SAAS_PLAN.md`, this tracker.

### 3. Database changes

| Migration | Change | Existing data |
|---|---|---|
| `0010` | `roles.workspace_scope` (`all` or `assigned`); new table `workspace_assignments` | Client roles become `assigned`; every client-portal link becomes an assignment; unused Client roles are removed from business accounts. `client_users` is kept, unused, for a later removal |
| `0011` | New table `workspace_grants` (one active grant per agency and workspace) | None |
| `0012` | Row-level security: two helper functions and a policy on each tenant table (`organization_members`, `roles`, `invitations`, `clients`, `client_users`, `workspaces`, `websites`, `workspace_assignments`, `workspace_grants`; `audit_logs` for reading) | None (policies only) |

All three were run up, checked, down and up again on the development database, and the
test suite builds its schema from them on every run.

### 4. Tests

| Suite | Result |
|---|---|
| Backend (pytest) | **337 passed** (was 293) |
| App (Vitest) | **106 passed** (was 93) |
| Website (Vitest) | 92 passed (unchanged) |
| CI | Green for every H1-3 commit, with the tests running as an ordinary database user |

New backend tests:
- roles per account type; startup sync adding and renaming roles (and respecting a custom
  role's name)
- members limited to assigned workspaces: what they see, what's a 404, assignment rules,
  audit, handing out only what they see, no escalation to a role that sees everything
- access grants: sending, preview, wrong account, members without permission, accepting,
  expiry and reuse, working in the business's workspace, view-only refusals, assignments to
  linked workspaces, revoking, disconnecting, and isolation from the rest of the business
- row-level security on its own (queries with no organization filter): each organization
  sees only its rows, writes into another are refused, the setting holds across a request's
  transactions and never leaks to the next session
- the cross-organization attack: 26 routes, the victim's ids in the URL and in the body; all
  refused and the victim unchanged

**Checking the checks:** I deliberately removed the app's own website filter.
- With row-level security on, every attack still failed: the database alone held.
- With row-level security also off, the attack suite caught the leak straight away (an
  attacker could delete another organization's website).
- Then I restored both.

**Browser check** (Chromium, against the real API):
- A business sends access, and the agency accepts it from the emailed link (the code is
  removed from the address bar).
- The business appears under Linked businesses in the agency's switcher. The agency adds a
  website there, and the business sees it straight away.
- The business ends access, and it disappears from the agency.
- No page errors. An axe scan of Agency access, the accept page, Linked businesses, Roles and
  the role editor found no problems.

### 5. Unfinished (on purpose)

- **Changing what a grant allows** (manage ↔ view) means ending it and sending a new one.
- **Agencies' dashboard counts** cover their own organization, not linked businesses. The
  H1-8 dashboards will add them.
- **Someone at an agency without an Outlogik account** can't accept until their agency is set
  up. Sign-up is invitation-only until H1-11.
- **`client_users`** is still in the database, unused; a later migration removes it once this
  has run in production.

### 6. Security notes

- **Two independent walls between organizations:** the application's checks (as before), and
  now Postgres row-level security. Each was shown to stop a cross-organization attack on its
  own.
- **Row-level security only works if production connects as an ordinary database user.** The
  DigitalOcean specs already do (`outlogik`, `outlogik_staging`, not `doadmin`). DEPLOYMENT.md
  §4 has a one-line check, and the API logs a warning at startup if the database user is one
  the policies don't apply to.
- **Docker development** (`docker compose`) connects as Postgres's superuser, so the policies
  aren't enforced there. The warning appears, and the tests in CI cover it.
- **A grant link is tied to one email address,** expires after 14 days, and is single-use. Its
  code is stored only as a hash, and the page removes it from the address bar.
- **A grant never opens the business's team, roles, invitations or activity log** to the
  agency. The tests check this in the application and in the database.

### 7. Next: H1-4 entitlements

Plans, entitlements and subscriptions (assigned by hand for now), usage records, and backend
enforcement of limits (websites, clients, team members, audits). No billing yet (H3).

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
