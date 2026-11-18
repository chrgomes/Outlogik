# Outlogik — Hybrid SaaS plan

Status: **Draft for approval** (2026-11-18), **revised the same day for simplicity** (section 0). Source: the
[hybrid SaaS specification](specs/HYBRID_SAAS_SPEC.md). Based on the
[codebase audit](HYBRID_SAAS_AUDIT.md). Nothing in this plan has been built yet. Section numbers
(§) refer to the specification.

**Naming.** The project already has a Phase 1 (app foundation) and a Phase 1.5 (agency
website), both done. To avoid confusion, the specification's phases are called **H1, H1.5, H2
and H3** here ("hybrid"). Their content is the specification's, adjusted where the audit found
a reason, and each adjustment is marked.

---

## 0. Keep it simple (decided 2026-11-18)

The specification describes a very broad product. To keep Outlogik simple to use and simple to
look at, three rules apply to everything below:

1. **A simple core first.** The first version does a few things well:
   - **SEO**
   - **website analytics**
   - **reports**
   - for agencies, **clients with a workspace switcher, and the client portal**

   Further modules are added **one at a time**, in the order customers ask for them, each one
   finished before the next starts.
2. **Only finished features are visible.**
   - A module appears in the navigation only when it works and the customer's plan includes it.
   - No "coming soon" tiles, empty sections or buttons that do nothing (this is also §24).
   - Businesses never see agency vocabulary, and each person sees only what their role allows.
3. **The website stays as it is, plus two things:**
   - **one "Platform" section** describing the software
   - **one pricing page**, with software plans next to agency services by proposal

   The menu stays at about six items, with the same layout and the same black-and-white design.
   No page per module.

Where the specification lists separate modules that fit inside the core, they become **views
inside it** rather than new menu items:
- **competitor comparisons:** inside SEO
- **conversion and funnel insights:** inside Analytics
- **AI explanations and summaries:** inside the module they explain, not a separate AI area

---

## 1. Target architecture

### 1.1 Accounts and workspaces (§4)

The existing **organization** stays the tenant: billing, team and subscription belong to it. A
new **workspace** layer holds the marketing data, so the same tools work for businesses and
agencies.

```
Platform
└── Organization (tenant)                 kind: business | agency
    ├── Members, roles, invitations       (exist today)
    ├── Subscription, entitlements        (new)
    └── Workspaces                        (new)
        ├── "own"    : the organization's own marketing (every business has exactly one;
        │              an agency can have one for itself, as Outlogik will)
        ├── "client" : an agency's client (one per client; replaces the client record's role)
        └── each workspace holds: business profile, websites, integrations, SEO audits,
            analytics snapshots, campaigns, content, tasks, reports, client portal users
```

**A business authorizes an agency (§4.C) without copying data:**
- A business sends an agency an **access grant** for its own workspace, with a permission set.
- The agency accepts it. That workspace then appears in the agency's client list as a
  **linked client**, alongside the clients it created itself.
- Agency staff work on the business's data in place.
- The business can see who has access and **revoke** it at any time. Everything is audited.
- An agency client created by the agency can later be **handed over** to the client as its own
  business account (in a later phase).

**What each customer sees:**
- **Business:** one workspace, no "clients" vocabulary, navigation as in §17.
- **Agency:**
  - agency overview, clients, team and settings
  - a **workspace switcher** for its clients (no signing out)
  - client workspaces reuse exactly the same modules as a business workspace

### 1.2 Roles and permissions (§5)

- **Built on the existing system:** permissions in code, roles in the database per
  organization, and custom roles already work.
- **New role templates by account type:**
  - business: Owner, Administrator, Marketing Manager, Marketing Contributor, Reporting Viewer
  - agency: Owner, Administrator, Account Manager, SEO Specialist, Social Media Manager,
    Marketing Strategist, Content Creator, Analyst
  - **Client Viewer** is a workspace-level role, which the existing client users become
- **Workspace scope:** each role either covers **all workspaces** or only **assigned
  workspaces** ("account managers manage assigned clients"). Assignments are a new table.
- **Permissions get per-module groups** (seo, analytics, social, campaigns, reports and so on),
  each with read, write and approve where needed.
- **Platform roles:** `users.platform_role` is extended with *platform admin*, *support admin*
  and *billing admin*. Super admins stay a flag. Existing `site_admin` and `content_editor`
  are kept for the website admin.
- **Enforced in the backend** by the existing `require(permission)` dependency, extended with
  the workspace check. The interface only hides what the API already refuses.

### 1.3 Tenant isolation (§4.C, §16, §21)

- **Workspace-scoped API:** `/api/v1/orgs/{org}/workspaces/{workspace}/…`. One dependency
  resolves the organization, the membership, the workspace (owned, client or granted) and the
  permissions, and answers **404** for anything outside them. That's the same rule as today.
- **PostgreSQL row-level security as a backstop** on workspace tables. Each request and each
  background job sets the allowed organization and workspaces for its transaction. Policies
  refuse other rows even if an application query forgot its filter.
- **Background jobs** carry the workspace in their arguments and set the same context.
- **A cross-tenant test suite** (§21's critical tests) grows with every module: for each new
  endpoint, another business, another agency, a client user and an unassigned team member must
  all be refused.

### 1.4 Subscriptions and entitlements (§12)

- **Tables:**
  - **plans:** category (business or agency), name, public flag, prices per interval
  - **plan entitlements:** key → limit, boolean or list
  - **subscriptions:** organization, plan, status (trial, active, past due, cancelled), period,
    source (manual now, payment provider later)
  - **usage records:** per organization, metric and period
- **Entitlement keys are defined in code; their values only in the database,** so Super Admin
  edits plans without code changes. Examples: `limits.websites`, `limits.clients`,
  `limits.team_members`, `limits.seo_audits_per_month`, `limits.ai_tokens_per_month`,
  `features.white_label`, `integrations.ga4`.
- **One backend policy layer:**
  - `require_entitlement(...)` and `check_limit(...)`, called by the services, never by the
    interface
  - a friendly error explaining the limit and how to upgrade
- **Billing provider later (H3),** behind an adapter. Stripe supports Canada.

### 1.5 Background processing (§19)

- **Celery** with Redis as the broker, plus **Celery beat** for schedules. Both are ordinary
  Python processes, with no Docker needed.
- **A `jobs` table** records each job: type, workspace, status, attempts, timings and the error
  shown to users. Uniqueness keys prevent duplicates (one audit per website at a time).
- **Retries** with backoff; per-integration rate limits and quota tracking.
- **First users:** sending email (moved out of requests), crawls, analytics syncs, reports.

### 1.6 Integrations (§11)

- **Adapters:** each integration (GA4, Search Console, …) implements one interface: connect
  (OAuth), list accounts or properties, sync, health check, disconnect.
- **Credentials are encrypted at rest,** with a key from the environment. Tokens are never
  returned to the browser and never logged. Refresh happens in the background jobs.
- **Data lands in snapshot tables** per workspace and day (for example search performance by
  query and page, GA4 sessions by source). Dashboards and reports read only these, never the
  live APIs, so they're fast and keep history.

### 1.7 SEO crawler (§6 Module 1)

- Our own crawler in Python (httpx, async):
  - follows robots.txt
  - limits on pages, depth, time, bytes and concurrency per site, with polite rate limits
  - **checks every resolved IP address**, for redirects too, to block SSRF
- **Checks:**
  - status codes and broken links
  - redirect chains
  - titles and meta descriptions (missing, duplicate, length)
  - headings
  - canonical URLs, robots meta and robots.txt
  - XML sitemap validation
  - image alt text
  - duplicate content (content hashes)
  - JSON-LD structured data syntax and types
  - viewport and basic mobile signals
  - internal links
- **Plus PageSpeed Insights** (free API) for speed and Lighthouse results.
- **Results** are stored per audit, so history and comparisons work, with issues ranked by
  severity and number of pages affected.

### 1.8 Reports (§10)

- Report data is put together from the snapshot tables and saved with its **period, sources and
  any unavailable metrics** (§10).
- **PDFs** come from HTML templates. WeasyPrint is the likely choice; it needs some system
  libraries, which the deployment can install.
- **CSV and Excel** (openpyxl) exports.
- **White-label settings** (logo, colours, footer) per agency, checked against the plan.

### 1.9 AI layer (§6 Module 9, H2)

- **A provider interface,** with the first provider to be chosen. Calls go through background
  jobs or a streaming endpoint.
- **Every request is recorded:** tokens, cost, user and workspace. Per-plan limits, plus a
  platform-wide cost cap.
- **Answers are built only from the workspace's own stored data,** and show which data they
  used, with observations and suggestions labelled separately (§6).
- **Crawled page text is treated as untrusted,** to protect against prompt injection.

---

## 2. Migration strategy: nothing is deleted

The existing data moves into the new model with **additive** migrations, each one reversible:

1. Add `organizations.kind`. Existing organizations become **agency** (Outlogik works for
   clients). The default for new sign-ups depends on the choice made at sign-up.
2. Create `workspaces`:
   - one **client** workspace for every existing client, linked by `client_id`
   - an **own** workspace for each organization
3. Add `workspace_id` to `websites`, filled in from each website's client (or the own
   workspace). The old columns stay until every reader has moved over; they're removed in a
   later migration, once tests prove nothing uses them.
4. Client users become **Client Viewer** members of their client's workspace. The old table is
   kept, read-only, until removal.
5. Existing roles keep working, mapped to the new permission groups. The four built-in roles
   map to Owner, Administrator, Marketing Manager and Client Viewer.
6. The API keeps today's endpoints, as aliases, until the app has moved to the workspace
   endpoints. Then they're removed in one documented step.

Every migration is tested in both directions (upgrade and downgrade) on a copy of the data, as
`alembic check` and the test suite already do.

---

## 3. Phases

Each step ends the way the specification asks (§24): what was done, files, database changes,
tests and results, what's unfinished, security notes, and the recommended next step. A feature
counts as done only when its backend, storage, permissions, error handling and tests are done
(§21).

### H1 — Hybrid foundation

| # | Step | Specification |
|---|---|---|
| H1-1 | **This audit and plan:** decisions (section 4) and approval | §2 |
| H1-2 ✅ | **Account types and workspaces:** the data model and migration above; workspace-scoped API; the app's workspace switcher | §4 |
| H1-3 | **Roles, assignments and isolation:** business and agency role templates, workspace scope and assignments, platform roles, RLS backstop, cross-tenant test suite | §5, §16, §21 |
| H1-4 | **Entitlements foundation:** plans, entitlements, subscriptions (assigned by hand), usage records, backend enforcement (websites, clients, team, audits) | §12 |
| H1-5 | **Background jobs:** Celery and beat, the jobs table, retries, duplicate prevention; email moves to the queue | §19 |
| H1-6 | **SEO crawler and audits:** the crawler, checks, PageSpeed, scheduled audits, history and comparison, prioritized issues | §6.1 |
| H1-7 | **Integration framework and Google:** encrypted credentials, Google OAuth, GA4 and Search Console syncs into snapshots. **Google's app verification is applied for at the start of H1**, because it takes weeks. | §6.2, §11 |
| H1-8 | **Business and agency dashboards:** ECharts, real data only, empty states that explain how to connect | §9 |
| H1-9 | **Basic reporting:** SEO and analytics reports per workspace, PDF and CSV | §10 |
| H1-10 | **Client portal on workspaces:** Client Viewer sees the dashboard, audits and reports, never agency-wide or internal data | §7 |
| H1-11 | **Self-serve sign-up and basic Super Admin:** choose business or agency at sign-up (behind an invitation code during beta); Super Admin lists organizations and users, assigns plans, suspends accounts | §13, §23 |
| H1-12 | **H1 review:** security review, isolation tests, staging deployment for an internal alpha | §21 |

**Not in H1, as the audit found:**
- The specification's "existing social media module integration" item doesn't apply, because
  there is no such module (see decision D2).
- **Keyword tracking** in H1 means the positions Search Console reports for a site's own
  queries. Keyword research and competitor rankings need paid data (H2, optional).

### H1.5 — Ready for customers

The core made usable for real businesses and agencies. No new modules.

- **Getting started:**
  - guided onboarding, short, for businesses and for agencies
  - the integration center: Google connections, plus Bing Webmaster Tools, Microsoft Clarity
    and PageSpeed, with connection status, sync history, errors and reconnect
- **Staying informed:**
  - SEO monitoring and **alerts** for real changes (for example new broken pages or a traffic
    drop)
  - **notifications** (in-app and email), with simple preferences
  - **scheduled reports**; **white-label** basics for agencies (logo, colours, footer)
- **Agency workflow:**
  - client invitations
  - **tasks and approvals**, with clients approving in the portal
- **Super Admin control center:** overview, organizations and users, plans and limits,
  feature flags, job and integration health, administrative logs
- **Account security and privacy:** optional **MFA**; account **data export and deletion**
  (PIPEDA)
- **Website:** the **Platform section** and the **pricing page** (section 0), plus sign-up
- **Beta:** a security and isolation test round, then a closed beta

Dashboard customization (widgets and saved layouts) waits until beta users ask for it. The
default dashboards should be good enough without it.

### H2 — More modules, one at a time

Each module is planned, built, tested and released on its own, and appears in the app only when
it's done. The proposed order, to be adjusted to what beta customers ask for:

1. **Social media** (built new; see D2): account connections, calendar, drafts, approvals,
   scheduling, and publishing **only where the platform's API allows it** (§6.3), plus
   analytics. Facebook and Instagram first, then LinkedIn, then others; X only if paid API
   access is worth it.
2. **Campaigns and content:** one place to plan a campaign across channels, with a content
   calendar, briefs and approvals.
3. **Paid ads (read-only):** Google Ads, Meta Ads, LinkedIn Ads results next to the rest.
4. **Email marketing:** Listmonk, with CASL consent and unsubscribe. Only if customers want it
   inside Outlogik rather than in their existing email tool.

Within the existing modules, in H2:
- **AI explanations and summaries,** with usage and cost limits (§6.9), added inside SEO,
  Analytics and Reports
- **Competitor comparisons** in SEO, clearly labelled as estimated or verified
- **Conversion and funnel views** in Analytics
- Keyword research and competitor rankings need paid data. They'd be optional add-ons, only
  with a clear business case (§11).

### H3 — Commercial expansion

- **Billing:** full subscription billing (payment provider, invoices, taxes, failed payments).
- **Branding:** advanced white-labeling and custom agency domains.
- **Later, only on demand:** a public API for customers, enterprise permissions and
  reporting, more integrations and AI providers.

---

## 4. Decisions needed before H1-2

| # | Decision | Recommendation |
|---|---|---|
| D1 | **Phase names.** Call the specification's phases H1, H1.5, H2, H3. | Yes, to avoid confusion with the finished Phase 1 and 1.5. |
| D2 | **Social media.** There's no existing module (audit). Where does it go? | **The first H2 module**, built new. Publishing depends on Meta, LinkedIn and others approving the app, which takes weeks, so **apply for those approvals during H1**. |
| D3 | **Docker** (§3: "not a requirement"). Local development already runs without it; deployment uses Dockerfiles that DigitalOcean builds. | **Keep the Dockerfiles** for DigitalOcean (you never need Docker installed). Also document a Docker-free deployment (a plain server, or DigitalOcean's buildpacks) so nothing depends on Docker. |
| D4 | **The agency website.** It's ready to launch and sells Outlogik as an agency. | **Launch it now.** The agency is the business today, and H1 takes a while. In H1.5 it gains only the **Platform section** and the **pricing page** (section 0). |
| D5 | **Outlogik's own account.** | Outlogik becomes an **agency tenant** on its own platform, and its clients become client workspaces. You use the product you sell. |
| D6 | **The workspace design** (section 1.1). | Approve as described: workspaces under organizations, access grants for business-to-agency links, no copied data. |
| D7 | **Beta sign-up.** | Open sign-up behind an **invitation code** at the end of H1; open to everyone in H1.5. |
| D8 | **AI provider** for the first adapter (H2). | Decide in H2; the layer is provider-agnostic. |
| D9 | **Merge first.** The website work (26 commits) isn't on `main` yet. | Merge it before H1-2 starts, so H1 builds on `main`. |

---

## 5. Definition of done (§23) mapped to phases

| Item | Phase |
|---|---|
| 1 business registers and manages its marketing | H1 (sign-up, workspace, SEO, analytics), extended in H1.5 and H2 |
| 2 agency registers | H1 |
| 3 agency onboards multiple clients | H1 (client workspaces); H1.5 (onboarding flow) |
| 4 business authorizes an agency | H1-2/H1-3 (access grants) |
| 5 agency switches between clients | H1-2 |
| 6 independent data and permissions per client | H1-2/H1-3 |
| 7 the same SEO and analytics tools for both account types | H1-6/H1-7 |
| 8 client portal | H1-10 |
| 9 reports for businesses and agency clients | H1-9 |
| 10 entitlements enforced in the backend | H1-4 |
| 11 Super Admin manages organizations, users, subscriptions, configuration | H1-11 (basic), H1.5 (complete) |
| 12 "existing social media functionality remains operational" | **Not applicable as written:** there's none. Replaced by the social module, the first H2 module (D2). |
| 13 reliable integration connections and syncs | H1-7, H1.5 |
| 14 reliable background jobs | H1-5, H1.5 (monitoring) |
| 15 cross-tenant tests pass | From H1-3, every step |
| 16 ready for staging and controlled beta | End of H1.5 |
