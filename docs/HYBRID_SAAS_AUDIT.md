# Outlogik — codebase audit for the hybrid SaaS platform

Date: 2026-11-18. The audit asked for in section 2 of the
[hybrid SaaS specification](specs/HYBRID_SAAS_SPEC.md). It describes what exists today, how it
fits the new direction, and what's missing or needs changing. The phased plan built on it is in
[`HYBRID_SAAS_PLAN.md`](HYBRID_SAAS_PLAN.md).

**In short:** the existing application is a solid, well-tested foundation for the hybrid
platform. It's already multi-tenant, with organizations, clients, a client portal, configurable
roles, audit logging and strong security. But almost all of the *marketing tools* in the
specification (SEO crawler, analytics integrations, social media, ads, email, AI, reporting)
**don't exist yet**. In particular, **there is no social media module** to preserve: the
specification assumes one, but the codebase has none.

---

## 1. What exists today

### 1.1 Repository and stack

| Area | What's there |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (sync) with psycopg 3, Pydantic 2, Alembic, Redis, Argon2id. A modular monolith in `backend/app/modules/*`. |
| Frontend | An Angular 22 workspace with two projects: the **app** (`frontend/src`, a single-page app: client portal and website admin) and the **marketing website** (`frontend/projects/marketing`, server-rendered with Node and Express). Bootstrap 5.3 (a subset) and SCSS, standalone components, signals, `httpResource`, Reactive Forms, the Angular CDK. TypeScript throughout. |
| Shared design | `frontend/brand/`: palette, logo, icon sets, the self-hosted Albert Sans font, and the proof-of-work helper. |
| Database | PostgreSQL 16; 7 Alembic migrations (`0001`–`0007`), each with a downgrade. |
| Tests | Backend: 271 tests (pytest). App: 82, website: 92 (Vitest). All passing. |
| CI | GitHub Actions: backend lint, tests and `alembic check`; frontend tests and builds for both projects; website server-rendering checks; Docker image builds and smoke tests. |
| Deployment | Prepared for DigitalOcean App Platform in Toronto: Dockerfiles and app specs (`.do/`), managed PostgreSQL and Valkey. Guide: `docs/DEPLOYMENT.md`. **Not yet deployed.** |
| Git | 45 commits on `claude/new-session-id3h0b`; `main` is 26 commits behind (Phase 1.5 isn't merged yet). |

### 1.2 Backend modules (67 API endpoints)

| Module | What it does | Endpoints |
|---|---|---|
| `auth` | Sign-up (open or invite-only), sign-in, sign-out (one device or all), sessions, email verification, password reset, invitation preview and acceptance, CSRF cookie. Lockout after failed sign-ins; invisible proof-of-work bot check. | 12 |
| `organizations` | Organizations (tenants), members, invitations, organization settings | part of the 30 under `/orgs/{slug}` |
| `rbac` | 17 permissions, 4 built-in roles (owner, admin, member, client), and custom roles per organization | ″ |
| `clients` | Clients of an organization, and client users (portal access limited to one client) | ″ |
| `websites` | Websites per organization and client; URL checks (refuses private and internal addresses) | ″ |
| `dashboard` | Counts (clients, websites, team), recent activity from the audit log, and "Not connected yet" cards for future metrics | ″ |
| `audit` | Audit log of every sensitive action | (internal) |
| `site` | Website settings and portal feature statuses (public and admin) | 7 public, part of 15 admin |
| `leads` | Website forms (consultation, contact, newsletter with double opt-in), leads inbox, notes, CSV exports, spam checks (honeypot, timing, proof of work, content, email domain), duplicates | ″ |
| `health` | Liveness and readiness | 2 |

Tenancy is enforced in `backend/app/tenancy/`:
- Every organization-scoped request goes through `/api/v1/orgs/{slug}/…`. It resolves membership and permissions (`OrgContext`), answers 404 to non-members, and offers scoped query helpers (`scoped_select`, `get_scoped`, `client_visibility`).
- Client users only ever see their own client's data.
- Platform staff (`users.platform_role`: `content_editor` or `site_admin`, plus super admins) use `/api/v1/admin/*`, which also answers 404 to everyone else.

### 1.3 Database (19 tables)

| Group | Tables |
|---|---|
| Identity | `users`, `user_sessions`, `email_verification_tokens`, `password_reset_tokens` |
| Tenancy | `organizations`, `organization_members`, `invitations`, `roles`, `permissions`, `role_permissions` |
| Client work | `clients`, `client_users`, `websites` |
| Platform | `audit_logs`, `site_settings`, `portal_features` |
| Website leads | `leads`, `lead_notes`, `newsletter_subscribers` |

All tenant data carries `organization_id` with foreign keys. Website URLs are unique per
organization. There's no soft deletion yet, and no row-level security (RLS) yet.

### 1.4 Frontend

- **App** (`frontend/src`):
  - sign-in pages: login, register, forgot and reset password, verify email, accept invitation
  - shell with sidebar, top bar, workspace (organization) switcher, light and dark themes
  - dashboard, clients (list and detail, client users), websites
  - settings: organization, team, roles (with a role editor)
  - website admin for staff: leads inbox and detail, newsletter, website settings, portal features
  - shared parts: page header, tables (pager, search, status badges, permission directive), dialogs, toasts, empty, loading and error states
- **Marketing website:** 22 pages, forms, SEO, consent banner, legal pages. It currently presents Outlogik as a **digital marketing agency** (plan revision 2), not as software.
- **Design system:** monochrome palette, Albert Sans, restrained radii. Accessibility: axe finds 0 violations in light and dark mode, keyboard navigation has been checked, Lighthouse scores 92–100.

### 1.5 Security already in place

- **Accounts:** Argon2id passwords; server-side sessions (HTTP-only, Secure, SameSite=Lax cookie, hashed tokens, idle and absolute expiry, rotation on sign-in); double-submit CSRF; single-use tokens that are only stored hashed.
- **Abuse protection:** rate limits and sign-in lockout; a proof-of-work bot check.
- **Access control:** 404 for anything outside a tenant; an audit log.
- **Headers:** a strict CSP on both front ends and the API, HSTS, `nosniff`, no framing.
- **Hosting:** real visitor IPs behind the hosting platform (shared secret); API docs are off in production; containers run as non-root users.
- **Deliberately off for now:** MFA (the schema has room for it) and RLS.

---

## 2. Gaps against the specification

### 2.1 What the specification assumes exists but doesn't

| Specification | Reality |
|---|---|
| §2, §6 Module 3, §23 item 12: "**the existing social media management module**", "preserve and expand", "existing social media functionality remains operational" | **There is no social media module in the code.** The only mentions of "social" are links in the website settings and "Social Media Management" as an **agency service** on the website, delivered by people. Social media has to be **built new** (see the plan), and definition-of-done item 12 can't be met as written. |
| §22 Phase 1: "Existing codebase audit … Phase 1.5 …" | The project already has a **Phase 1** (app foundation) and a **Phase 1.5** (agency website), both done. Reusing those names would be confusing, so the plan calls the specification's phases **H1, H1.5, H2 and H3** ("hybrid"). |

### 2.2 Feature coverage

| Specification area | Today | Gap |
|---|---|---|
| §4 Business and agency account types | One kind of organization (agency-shaped) | Account types, business profile, and an onboarding path for each |
| §4.C Workspaces | Organization → clients → websites | A **workspace** layer: one per business, one per agency client. Business-to-agency access grants. |
| §5 Roles | 4 built-in roles, 17 permissions, custom roles; platform roles `site_admin` and `content_editor` | The business and agency role sets; assignment to specific clients ("assigned clients only"); platform roles (super, platform, support, billing admin) |
| §6 Module 1 SEO, crawler | None (the dashboard shows "Not connected yet") | Everything: crawler, audit engine, history, PageSpeed |
| §6 Module 2 Analytics | None | Integration framework, OAuth, GA4, Search Console, then Bing, Clarity, Tag Manager |
| §6 Modules 3–9 (social, ads, content, email, CRO, competitors, AI) | None | Everything |
| §7 Client management and portal | Clients, client users and a restricted portal exist | Client profiles, documents, notes, onboarding, approvals, messaging |
| §8 Campaigns, §15 Tasks and approvals | None | Everything |
| §9 Dashboards | One dashboard with counts | Business and agency dashboards, widgets, customization, ECharts |
| §10 Reporting | CSV export of leads only | Reporting engine, PDF and Excel, schedules, white-labeling |
| §11 Integration center | None | Everything (adapters, encrypted credentials, sync history) |
| §12 Subscriptions | None | Plans, entitlements, usage records, enforcement, then billing |
| §13 Super Admin | A super admin flag; a website admin for staff (leads, settings, portal features) | Platform overview, user and organization management, plans, feature flags, integration and job monitoring |
| §14 Notifications | Email only (sent during the request) | In-app notifications, preferences, a queue |
| §18 Data export and deletion; MFA | Lead and subscriber deletion only | Account export and deletion workflows; optional MFA |
| §19 Celery | None (emails are sent during the request) | Celery worker and scheduler, job records, retries, monitoring |

### 2.3 Technical debt and limitations

1. **No background jobs.** Emails go out during the request, so a slow mail server slows that
   request. Celery is needed before anything long-running: crawling, syncing, reports.
2. **Tenancy is organization-only.** The `/orgs/{slug}` scoping is sound, but every module
   assumes "organization = agency" and "client = the agency's customer". Workspaces need careful
   migration (plan, step H1-2).
3. **No row-level security.** Isolation relies on application code (well-tested). The
   specification asks for RLS where appropriate; it's planned as a second layer.
4. **No crawler SSRF protection beyond URL checks.** Website URLs are checked when added
   (private and internal hosts are refused), but a crawler must also check the **resolved IP
   address** of every request and redirect. This was already noted in the Phase 1 tracker.
5. **Website positioning.** The website sells Outlogik as an agency. A hybrid SaaS needs product
   pages, plans and self-serve sign-up. Revision 1 of the website plan (software for agencies)
   is in git history and can be partly reused.
6. **Label maps duplicated.** Service, budget and topic labels exist in the backend, the
   website and the admin area, kept in step by tests. Acceptable now; worth centralizing when
   the API serves more reference data.
7. **Sign-up mode.** `SIGNUP_MODE` is `invite_only` in production. Self-serve business and
   agency sign-up needs it opened, with abuse protection (the bot check and rate limits exist).
8. **The app's initial bundle** is about 637 kB (139 kB compressed). Fine now, but the new
   modules must load on demand (lazy routes), as the existing pages do.
9. **Docker.** The specification says Docker mustn't be a requirement. Today:
   - Local development already runs **without** Docker. Docker Compose is optional, for
     PostgreSQL, Redis and Mailpit.
   - **Deployment** uses Dockerfiles, which DigitalOcean builds on its side.
   - The plan proposes keeping that, and documenting a Docker-free deployment as well.

### 2.4 Security observations

There are no known vulnerabilities in the current code. `npm audit` and `pip-audit` are clean,
and the step 14 review is in `SECURITY.md`. The risks to manage as the platform grows:

- **More tenant paths:** every new module and background job must be scoped to a workspace.
  Plan: a shared scoping layer, RLS as a backstop, and a cross-tenant test suite that grows
  with each module.
- **Third-party tokens:** OAuth tokens must be encrypted at rest, never logged, never returned
  to the browser, and revocable.
- **Crawler:** SSRF (above); limits on size, time and redirects; respect for robots.txt.
- **AI:** prompt injection from crawled pages, and data sent to third-party providers. Limit
  the data, label AI output, enforce cost limits.
- **File uploads** (media, documents, logos): type checks, re-encoding images, storage outside
  the web root.
- **Self-serve sign-up:** abuse and spam accounts (the bot check, email verification and rate
  limits exist).

---

## 3. External dependencies the specification implies

These matter for scheduling, because several need **approval from the platform**, which can
take weeks. The application can't shortcut them.

| Integration | Access | Cost | Notes |
|---|---|---|---|
| Google Analytics 4 (Data API), Search Console API | OAuth app in Google Cloud | Free | The analytics and Search Console read scopes count as **sensitive**: Google requires **OAuth app verification** (privacy policy, demo video, domain verification) before unlimited users. Allow 2–6 weeks. |
| PageSpeed Insights | API key | Free (quota) | |
| Bing Webmaster Tools | API key per user | Free | |
| Google Tag Manager API, Microsoft Clarity (data export API) | OAuth or token | Free | Clarity's export API is limited (recent days, daily quota) |
| Google Trends | — | — | **No official public API** (an alpha exists, by invitation). Treat as "where available". |
| Facebook / Instagram (Meta Graph API) | Meta app + **App Review** | Free | Review per permission, business verification |
| LinkedIn | **Partner approval** for the Community Management API | Free | Approval isn't guaranteed |
| X | API plans | **Paid** (posting beyond the minimal free tier) | Conflicts with "free-first"; defer |
| TikTok, YouTube, Pinterest | App audits | Free | Posting APIs need audits |
| Google Ads, Meta Ads, LinkedIn Ads | Developer token or app review | Free | Google Ads needs a developer token approval |
| Keyword research and ranking for keywords | — | — | **Search Console gives positions only for a site's own queries.** Keyword volumes and rankings for arbitrary keywords or competitors need paid data (for example DataForSEO); scraping Google breaks its terms. The specification defers paid data, so keyword features start with Search Console data, and competitor and keyword-research features stay labelled accordingly. |
| Listmonk (email) | Self-hosted | Free (hosting) | Its own process and database; plus a sending service (Resend or similar) |
| AI provider | API key | Paid per use | Provider-agnostic layer; usage and cost limits |

---

## 4. What to preserve

Everything that exists is working and tested, and stays:

- **Auth, security, audit, RBAC and custom roles.** They extend to the new role sets.
- **Organizations, members, invitations, clients, client users, websites.** They become part
  of the workspace model, and nothing is deleted (see the migration strategy in the plan).
- **The dashboard.** It's replaced by the business and agency dashboards, reusing its
  activity feed.
- **The website admin** (leads, newsletter, settings, portal features). It moves into the Super
  Admin control center.
- **The marketing website and its deployment setup.**
- **The design system and shared components.** They're extended, not replaced.
