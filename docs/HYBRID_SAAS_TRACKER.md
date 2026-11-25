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
| H1-5 Background jobs | **Done** (2026-11-18) |
| H1-6 SEO crawler and audits | **Done** (2026-11-18) |
| H1-7 Integrations and Google | **Done** (2026-11-19); waits on your Google Cloud setup to connect real accounts |
| H1-8 Dashboards | **Done** (2026-11-19) |
| H1-9 Basic reporting | **Done** (2026-11-24) |
| H1-10 Client portal on workspaces | **Done** (2026-11-24) |
| H1-11 Self-serve sign-up and basic Super Admin | Next |
| H1-12 H1 review | Not started |

---

## H1-10: Client portal

### 1. What was completed

I signed in as a client user first, to see what clients got before this step. Their data was
already limited to their own client, but the experience was the agency's: they landed on the
agency overview ("Northline Agency · all clients", "Needs attention", "Google not connected"),
had the agency's Clients and Organization pages in the menu, and had no way to reach their
account manager. Now:

- **Clients land on their own dashboard:** their workspace's figures, charts, AI tool visits,
  searches and latest audit. There's no "All workspaces"; a client linked to two businesses
  switches between those two only.
- **"Your account manager"** at the top of their dashboard, with an email link. If the agency
  hasn't assigned one, it shows the agency's owners instead.
- **A menu of three:** Dashboard, Audits, Reports. They can download their reports (PDF and
  CSV) and open their audits.
- **Agency pages are closed to them:** Clients, Websites and Organization settings send them
  back to their dashboard; team, roles, plan and integrations say they don't have access.
- **Written for clients:** "Appears when Northline connects Google Analytics" rather than
  "connect it in Integrations"; "No audit yet. Northline will run the first one."; no audit
  schedule column (an agency setting).
- **The server enforces it too:** the agency overview is refused to client users (403), not
  just hidden. Team lists, internal notes and other clients stay out of reach, as before.
- **"Your account" for everyone** (in the user menu): change your name, change your password
  (needs the current one; your other devices are signed out and you get an email), sign out
  everywhere, and see where you're a member. Until now there was no way to change a password
  while signed in.

The spec's other client portal items (campaign progress, approving content, tasks, messages)
come with those features in H1.5 and H2.

### 2. Files changed

**Backend:**
- `dashboard/router.py`: the overview refused to client users; new `contacts` endpoint.
- `auth/`: `PATCH /auth/me` and `POST /auth/change-password` (schemas, service, router).
- Tests: new `test_portal.py`; one dashboard test updated (clients now get their own
  dashboard instead of the overview, by design).

**App:**
- New `features/account/` (Your account page, portal and account tests).
- `core/workspace.service.ts` (a client always has a workspace selected), `core/guards.ts`
  (`staffGuard`), routes, menu (`staffOnly`), top bar (no "All workspaces" for clients; "Your
  account" in the user menu).
- Dashboard: the account manager card and client wording; audits: no schedule column for
  clients.

**Docs:** `ARCHITECTURE.md`, `SECURITY.md`, `HYBRID_SAAS_PLAN.md`, this tracker.

### 3. Database changes

None.

### 4. Tests

| Suite | Result |
|---|---|
| Backend (pytest) | **497 passed** (was 486) |
| App (Vitest) | **148 passed** (was 141) |
| Website (Vitest) | 93 passed (unchanged) |

The new tests cover:
- clients get their own dashboard, not the overview, and not another client's
- contacts: the assigned account manager, else the owners; disabled managers left out;
  another client's contacts refused; no team list or internal notes for clients
- changing your name; changing your password (other devices signed out, this one kept, an
  email sent, recorded); the current password required; guessing it limited; both need a
  session
- in the app: a client always has one of their workspaces selected; the portal menu; the
  account manager card and client wording; agency pages redirect; the account page

**Browser check:** signed in as a client user and visited every page, then tried the agency
pages and APIs directly. Everything above held. An axe scan of the portal dashboard and the
account page found no problems in light or dark mode; no sideways scrolling on a phone.

### 5. Unfinished (on purpose)

- **Campaign progress, content approvals, tasks and messaging** in the portal come with
  those features (H1.5 and H2). For now clients contact their account manager by email.
- **Changing your email address** isn't possible yet; the account page says to ask for an
  invitation to the new address. A safe email change (confirming both addresses) can come
  with the account security work in H1.5, alongside two-step sign-in.
- **The portal shows the agency's name** in the top bar; the agency's logo and colours come
  with white-label branding in H1.5.

### 6. Security notes

- The agency overview is refused by the server to client users, so hiding it in the app
  isn't the only protection.
- Contacts show only account managers assigned to that workspace (or the owners), never the
  rest of the team.
- Password changes need the current password, are rate-limited, sign out other devices and
  notify the person by email.

### 7. Next: H1-11 self-serve sign-up and basic Super Admin

Choose business or agency at sign-up (behind an invitation code during the beta); a Super
Admin area to list organizations and users, assign plans and suspend accounts; platform roles.

---

## H1-9: Reports

### 1. What was completed

- **Reports for a workspace** (a new **Reports** item in the menu):
  - Choose the **period** (last 7, 28 or 90 days, or your own dates, up to 16 months) and
    what to **compare with** (the period before, the same period last year, or nothing).
  - Choose what to **include**: Traffic, Visits from AI tools, Google search, Website audit.
    Sections a person's role can't see aren't offered.
  - Give it a **title**, or keep the suggested one ("Corner Bakery: marketing report").
- **Saved as they were made.** A report keeps its figures, so the PDF you sent a client last
  month says exactly what it said then, whatever has synced since.
- **Every report says where its numbers come from** (spec §10):
  - the **period** and the comparison period
  - the **sources**, with how recent their data is (for example "Google Search Console:
    sc-domain:bakery.example.com, data through November 21")
  - **what's not available or limited**, in plain words, for example "Google search figures
    run to November 21: Search Console reports 2–3 days behind" or "Search Console isn't
    connected"
  - "Every figure comes from the sources above. Outlogik doesn't estimate missing data or
    forecast results."
- **PDF**, with Outlogik's Albert Sans font:
  - a title block and "About this report"
  - What changed and the key figures
  - charts: visits per day with the comparison period, search clicks per day, audit errors
    and warnings over time
  - tables: channels, pages that bring the most visits, AI tools, top searches, searches you
    almost rank for, pages rarely clicked, audit issues **with how to fix each one**
  - "Prepared by Northline Agency for Alpha Dental" on agencies' client reports, and a page
    footer
- **CSV files**, one per table (daily figures, channels, pages, AI tools, searches, almost
  ranking, rarely clicked, audit issues), which open correctly in Excel, accents included.
- **Agency dashboard:** the **Client report** button on each client row (approved as #11)
  opens New report with that client already chosen.
- **Permissions:** viewing and downloading (`reports.read`): everyone except custom roles
  without it, including Client Viewers for the client portal (H1-10). Making and deleting
  (`reports.create`): owners, administrators, Marketing Managers and Account Managers.

### 2. A change from the plan

The plan expected **WeasyPrint** for PDFs. I used **ReportLab** instead. WeasyPrint needs system
libraries that are awkward to install on Windows, where you develop; ReportLab is pure Python,
so PDFs work the same on your computer and the servers, with nothing extra to install. It also
draws the charts itself. The plan is updated.

### 3. Files changed

**Backend:**
- New module `reports/`: `models.py`, `schemas.py`, `service.py` (the saved snapshot, sources
  and what's unavailable), `pdf.py`, `exports.py` (CSV), `router.py`, and `fonts/` (Albert Sans,
  with its open font licence).
- `rbac/catalogue.py` (`reports.read`, `reports.create`). Migration `0018`.
- `pyproject.toml`: `reportlab` (and `pypdf`, for tests only).
- Tests: new `test_reports.py`; updated cross-tenant and role tests.

**App:** new `features/reports/` (Reports page, New report dialog, tests); the menu, route,
types and API calls; the Client report button on the agency dashboard; one new icon. A small
fix for every page: hidden column labels in scrolling tables could widen the page on a phone.

**Docs:** `ARCHITECTURE.md`, `SECURITY.md`, `HYBRID_SAAS_PLAN.md`, this tracker.

### 4. Database changes (migration `0018`)

| Change | Existing data |
|---|---|
| `reports` (organization, workspace, title, sections, period, comparison, the saved figures) | None |
| Row-level security on `reports`: the organization that made it only | None |

Run up, down and up again; the test suite builds from it.

### 5. Tests

| Suite | Result |
|---|---|
| Backend (pytest) | **486 passed** (was 464) |
| App (Vitest) | **141 passed** (was 132) |
| Website (Vitest) | 93 passed (unchanged) |

The new backend tests cover:
- a report naming its period, sources and what's unavailable; a report before anything is
  connected
- the PDF containing every part, read back from the PDF itself
- figures staying the same after new data syncs
- only the chosen sections; a custom period
- **outside text can't change the PDF:** markup in a search term is printed, not obeyed
- **CSV formula injection:** a `=HYPERLINK(...)` search term is made safe
- safe download names; an unknown CSV table
- listing and deleting (recorded in the audit log)
- viewers download but can't make or delete; a role without traffic access can't make or
  open a report with traffic in it
- client-portal users see only their client's reports
- an agency's report on a business's shared workspace stays the agency's
- the cross-organization attack suite found the new routes by itself, now includes a victim's
  report, and every attempt failed

**Browser check:**
- made a report through the dialog; downloaded the PDF (27 KB) and a CSV
- the agency's **Client report** button opened the dialog with the right client chosen
- an axe scan found no problems on the page in light or dark mode, nor in the dialog (one
  note was about the dimmed page behind it)
- no sideways scrolling on a phone

The check caught two things, both fixed: the dialog showed the wrong client while making the
report for the right one, and a hidden table label made the page scroll sideways on a phone.

### 6. Unfinished (on purpose)

- **White-label branding** (agency logo, colours, footer) and **scheduled reports** come in
  H1.5, as planned. Reports say "Prepared by" the agency's name for now.
- **Excel files:** CSV for now; Excel later if you want it.
- **Search terms in other alphabets** (for example Chinese) show as `?` in the PDF, because
  Albert Sans covers Latin languages (English and French are fine). The CSV files keep them
  exactly.
- **The searches and page lists** cover Search Console's latest 28 days whatever period is
  chosen; the report says so.
- Real data still waits on the Google Cloud setup.

### 7. Security notes

- Outside text is escaped before it reaches the PDF, and CSV cells are protected against
  formula injection; both are tested.
- Reports are visible only within the organization that made them, to people who can see the
  workspace and every section in the report; row-level security backs this up.
- Downloads are signed-in requests like the rest of the app, never public links.

### 8. Next: H1-10 client portal on workspaces

Client Viewers see their workspace's dashboard, audits and reports, and never anything
agency-wide or internal.

---

## H1-8: Dashboards

Built to the mockup approved on 2026-11-19, with the additions you chose (#1–#5, #7, #9–#11).

### 1. What was completed

- **The business dashboard** (also an agency's view of one client):
  - **Period:** last 7, 28 or 90 days, or a custom range up to 16 months. **Compare with** the
    period before, the same period last year, or nothing.
  - **What changed** (#4): plain sentences worked out from the numbers by fixed rules, for
    example "Visits are up 6% (3,113), mostly from Organic Search (+131) compared with
    before." No AI writing, no forecasts.
  - **Headline figures:** visits, visitors, visits from AI tools, search clicks, key events and
    audit errors, each with its change.
  - **Charts:** visits per day with the comparison period as a dashed line; Google search
    clicks per day; audit errors and warnings over the last six audits (#5).
  - **Visits from AI tools** by tool, and **where visits came from** by channel.
  - **Latest audit:** errors, warnings and notices, what to fix first, and a link to it.
  - **Pages that bring the most visits** (#1), by the page each visit started on.
  - **Searches you almost rank for** (#2): positions 8 to 20.
  - **Shown in search, rarely clicked** (#3): pages on Google's first page clicked less than
    half as often as the site's other pages, with a link to the audit's title advice.
  - **Top Google searches.**
  - **Before anything is connected:** three steps (add your website, run an audit, connect
    Google) and, in each empty section, what will appear there and what it needs.
- **The agency dashboard** (all workspaces):
  - Headline figures across clients, **what needs attention** (Google needs reconnecting, visits
    down 20% or more, audit errors, Google not connected) with a button to fix each, and weekly
    visits across all clients for 12 weeks.
  - **Client table** with a trend line per client, visits and change, AI visits, search
    clicks, audit status and Google status.
  - **Sort and filter** (#9): biggest drop or gain, most AI visits, most audit errors, name;
    needs attention, audit errors, Google not connected, my clients.
  - **Account manager and "Reviewed" date** per client (#10), with **Mark reviewed**.
- **More history from Google:** the first sync now copies 16 months (what Search Console
  keeps), so "same period last year" works from day one. Visits by landing page start with 90
  days.
- **Honest comparisons:** a comparison is shown only when the whole earlier period was synced;
  otherwise the dashboard says "No earlier data to compare".
- **Permissions:** the dashboard leaves out what a role can't read (traffic, audits). Client
  Viewers see their client's numbers but never the team details. **Mark reviewed** needs the
  new `workspaces.review` permission (owners, administrators, Marketing Managers, Account
  Managers).

### 2. Files changed

**Backend:**
- `dashboard/`: new `analytics.py` (one workspace), `overview.py` (agency), `models.py`
  (reviews); `router.py` and `schemas.py` extended.
- `integrations/`: `sync.py` (16 months, landing pages, Search Console pages and searches by
  page), `models.py` (three tables, `history_from`, `pages_from`), `summary.py` (same
  comparison rule as the dashboard).
- `rbac/catalogue.py` (`workspaces.review`). Migration `0017`.
- Tests: new `test_dashboards.py`; updated integration, cross-tenant and role tests.

**App:** `features/dashboard/` rewritten (page, workspace view, agency view, chart component,
ECharts setup, styles, tests); chart colours in the theme; one API call; the Integrations page
mentions 16 months. ECharts 5.6.0 added.

**Docs:** `ARCHITECTURE.md`, `SECURITY.md`, `DEPLOYMENT.md`, `HYBRID_SAAS_PLAN.md`, this
tracker.

### 3. Database changes (migration `0017`)

| Change | Existing data |
|---|---|
| `ga4_pages` (daily visits by landing page) | None |
| `gsc_pages`, `gsc_query_pages` (Search Console's latest 28 days by page, and by search and page) | None |
| `workspace_reviews` (organization, workspace, when, by whom) | None |
| `data_sources.history_from`, `pages_from` | Empty until the next first sync |
| Row-level security on the four new tables (reviews: the reviewing organization only) | None |

Run up, down and up again; the test suite builds from it.

### 4. Tests

| Suite | Result |
|---|---|
| Backend (pytest) | **464 passed** (was 443) |
| App (Vitest) | **132 passed** (was 128) |
| Website (Vitest) | 93 passed (was 92, the privacy policy test) |

The new backend tests cover:
- the default period and its comparison; same period last year; no comparison; a comparison
  left out when the earlier period wasn't synced
- "what changed", including the channel that explains a change
- custom ranges and their limits
- top pages, searches in positions 8–20, rarely clicked pages
- the latest audit, its history, new and fixed issues, what to fix first
- a workspace with nothing connected
- roles without traffic or audit access
- the agency overview, what needs attention (including a drop in visits and Google needing
  reconnection), account managers, reviews, "my clients", client-portal users, archived
  clients, and an agency's review of a business's shared workspace staying the agency's
- the cross-organization attack suite found the new routes by itself, now includes a victim's
  review, and every attempt failed

**Browser check** with data synced through the real code (from the fake Google, with numbers
that vary by day): business dashboard, agency dashboard and the getting-started view in light
and dark mode. An axe scan found no problems in any of them; no sideways scrolling on a phone;
Mark reviewed worked.

### 5. Unfinished (on purpose)

- **The "Client report" button (#11) isn't there yet.** Reports are H1-9; a button that does
  nothing would break the no-placeholders rule, so it arrives with the reports.
- **Alerts, AI search visibility and Google Business Profile** are planned for later (H1.5 and
  H2), as agreed. **A marketing score and forecasts are left out** on purpose.
- **The searches and page lists** cover Search Console's latest 28 days whatever period is
  chosen; the dashboard says so under them.
- **Still waiting on Google Cloud** for real data; until then the dashboard shows the
  getting-started steps.

### 6. Security notes

- Parts a role can't read are left out of the API response, not just hidden in the app.
- Team details (account managers, reviews) are only sent to people who can see the team.
- Reviews are under row-level security for the reviewing organization only.
- The new routes are covered by the cross-organization attack suite.

### 7. Next: H1-9 basic reporting

SEO and analytics reports per workspace as PDF and CSV, including the **Client report** button
on the agency dashboard.

---

## H1-7: Integrations and Google

### 1. What was completed

- **Connect Google per workspace** (Integrations, a new item in the menu):
  - Sign-in with Google using read-only access to Analytics and Search Console. Outlogik can
    see reports, never change anything in the Google account.
  - Pick one **GA4 property** and one **Search Console site** from the ones that Google
    account can see (unverified Search Console sites aren't offered).
  - See which Google account is connected, when each source last synced, and any error.
  - **Sync now**, **Change what's synced**, and **Disconnect** (with a confirmation). Disconnect
    removes Outlogik's access at Google and deletes the synced history.
  - If Google stops accepting the connection (for example, the person removed access in their
    Google account), the page says so and offers **Reconnect Google**.
- **Syncing into Outlogik's own history:**
  - The first sync copies the last 90 days; then every night the last 7 days are refreshed
    (Google revises recent days).
  - GA4: sessions, visitors, new visitors, engaged sessions, page views, key events, and
    sessions by channel.
  - Search Console: clicks, impressions and average position by day, and the top 250 searches
    over 28 days.
- **Visits from AI tools** (the addendum): GA4 sessions referred by ChatGPT, Perplexity,
  Gemini, Microsoft Copilot, Claude and You.com, grouped by tool. The page says plainly that
  some AI tools don't pass on where a visitor came from, so the real number can be higher.
- **A 28-day summary** on the Integrations page: totals against the 28 days before, visits from
  AI tools, channels and top Google searches. A comparison is shown only when the earlier
  period was fully synced; otherwise it says "No earlier data to compare". Charts come with the
  dashboards (H1-8).
- **Permissions:**
  - **Connect, choose, sync, disconnect:** owners, administrators, Marketing Managers and
    Account Managers.
  - **See the connection and the numbers:** also Reporting Viewers.
  - **Client Viewers** see the numbers only (for the client portal, H1-10), not which Google
    account is connected.
  - An agency with **view-only** access to a business's workspace sees the numbers but can't
    change the connection.
- **If Google isn't set up on the server** (today), the page says so, and nothing else is
  affected.

### 2. Files changed

**Backend:**
- New module `integrations/`: `google.py` (every call to Google), `crypto.py` (token
  encryption), `models.py`, `schemas.py`, `service.py` (connect, choose, disconnect),
  `sync.py`, `summary.py`, `router.py`.
- `jobs/handlers.py` (`integrations.sync`, `integrations.sync_all`), `worker.py` (nightly at
  05:23 Toronto).
- `rbac/catalogue.py` (`integrations.read`, `integrations.manage`, `analytics.read`).
- `tenancy/context.py` (the organization check reused for Google's return).
- `core/config.py` (Google and encryption settings; production refuses Google without an
  encryption key). `pyproject.toml` adds `cryptography`.
- Migration `0016`.
- Tests: new `test_integrations.py`; updated cross-tenant and role tests.

**App:** new `features/integrations/` (page and tests); menu, route, types, API calls.

**Docs:** `DEPLOYMENT.md` (Google Cloud setup, step by step, and the launch checklist),
`ARCHITECTURE.md`, `SECURITY.md`, `.env.example`, this tracker.

### 3. Database changes (migration `0016`)

| Change | Existing data |
|---|---|
| `integrations` (workspace, provider, status, Google account, encrypted refresh token) | None |
| `data_sources` (the GA4 property or Search Console site, sync status) | None |
| `ga4_daily`, `ga4_breakdowns` (channels and AI tools), `gsc_daily`, `gsc_queries` | None |
| Row-level security on all six (an agency can see a business's that shared its workspace) | None |

Run up, down and up again; the test suite builds from it.

### 4. Tests

| Suite | Result |
|---|---|
| Backend (pytest) | **443 passed** (was 414) |
| App (Vitest) | **128 passed** (was 121) |
| Website (Vitest) | 92 passed (unchanged) |

**Honest limit:** these tests use a fake Google that answers with the real APIs' addresses and
data shapes, written from Google's documentation. Nothing has talked to the real Google yet,
because that needs the Google Cloud project. The first real connection on staging is the real
test; if Google's answers differ anywhere, I'll fix it then.

The new backend tests cover:
- **Signing in:** the full round trip; read-only scopes and PKCE in the request; the one-time
  state (expires in 10 minutes, works once, only for the person who started it); signed out;
  cancelled at Google; scopes unticked (token revoked, nothing stored); no lasting access.
- **Storage:** the token is encrypted at rest and never in an API response; reconnecting
  revokes the old token.
- **Syncing:** only sources the account can see; 90 days then 7; replaced, not doubled; AI
  sources merged (chatgpt.com and chat.openai.com are both ChatGPT); Search Console's delay.
- **Failures:** Google withdrawing access (marked for reconnection, skipped nightly); Google
  down (sync marked failed, history kept).
- **Summary:** totals, the previous period, no comparison without a full earlier period, before
  anything is connected.
- **Access:** viewers read only; Marketing Managers manage; a view-only agency sees but can't
  change.
- **The cross-organization attack suite** found the new routes by itself, now includes a
  victim's Google connection, and every attempt failed.

**Browser check** with data synced through the real sync code (fed by the fake Google): the
page, summary, AI visits and disconnect all worked; no console errors; no sideways scrolling on
a phone; an axe scan found no problems in light or dark mode.

### 5. Unfinished (on purpose)

- **Real Google connections wait on your Google Cloud setup** (DEPLOYMENT.md has the steps).
  Until the app is verified, only test users you list (up to 100) can connect, and their
  connections expire after 7 days.
- **The privacy policy now covers Google data** (section 3, approved 2026-11-19): what's read,
  that it's used only for the workspace's own reports, not sold, used for ads or to train AI
  models, who can see it, how to disconnect, and Google's Limited Use statement. A lawyer's
  review is still on the launch checklist. When Google access is removed from the Google
  account side, copied data stays until the person disconnects in Outlogik or asks us; the
  policy says so.
- **Google Business Profile** moved to the SEO and AI Search module (H2), as agreed.
- **No charts yet.** The dashboards (H1-8) add charts from this same history.
- **No email when a connection breaks.** Comes with alerts and notifications (H1.5).

### 6. Security notes

- **Read-only access** at Google; refused and revoked if either read permission is unticked.
- **Sign-in protection:** PKCE, a one-time state tied to the person, and on return the
  membership, permission and workspace are checked again.
- **Tokens are encrypted** with a key that lives only in the server's secrets, are never sent
  to the browser, and are revoked at Google on disconnect.
- **Row-level security** on every new table; the cross-organization suite covers the new
  routes and a victim's connection.

### 7. Next: H1-8 dashboards

Business and agency dashboards with charts, using real data only (audits, and the Google
history from this step), and empty states that explain how to connect.

---

## H1-6: Website crawler and audits

### 1. What was completed

- **A safe, polite crawler** that only fetches public websites:
  - **Public addresses only:** every connection checks the real address it's about to
    connect to, and refuses private networks, the server itself and cloud metadata.
  - **Redirects:** each hop is checked again.
  - **Limits:** no proxies; size and time limits.
  - **Polite:** it obeys robots.txt, reads the sitemap, stays on the site, and waits between
    requests.
- **Website audits with 29 checks in three areas,** each with plain "why it matters" and "how
  to fix it" text:
  - **Technical:**
    - broken pages, with the page linking to them
    - server errors, HTTPS, redirect chains, slow pages
    - robots.txt, sitemap, the mobile viewport, pages hidden from search
  - **SEO:**
    - titles and meta descriptions (missing, too long, duplicated)
    - headings, image alt text, thin pages, canonicals, the page language
  - **AI search readiness** (from the addendum):
    - AI search crawlers blocked by robots.txt
    - structured data, and business details in it
    - the same name, phone and address across pages
    - questions without FAQ markup
  - **AI training crawlers** (GPTBot and others) are shown as information. Blocking them is
    the site owner's choice and doesn't affect AI search.
- **Page speed** from Google PageSpeed (mobile, home page) once a key is set. Until then,
  audits say "not connected".
- **Results:**
  - a summary, and what's new or fixed since the previous audit
  - issues grouped by check, most serious first, filtered by area
  - every page checked
- **Plan limits you approved:** audits a month (counted per calendar month) and pages per
  audit.
  - An agency's audit of a business's shared workspace counts against the business's plan.
  - Both show on the Plan page.
- **Schedules:** each website can be audited weekly or monthly, started at night within the
  plan's limits.
- **Permissions:**
  - **View audits:** everyone except custom roles without it, including Client Viewers, so
    clients will see audits in their portal (H1-10).
  - **Run audits and set schedules:** owners, administrators, Marketing Managers and Account
    Managers.
  - **View-only shared workspaces** can't run audits.

**Audited Outlogik's own website as a real test.** It found three false alarms, all now fixed
and covered by tests:
- the crawler wandered from the website onto the client portal's login page (same host
  locally, different port)
- the home page was counted twice through a redirect
- the booking page's `?service=…` variants were reported as duplicates, although they
  already point search engines to the main version

What's left on your site is accurate:
- **About page:** its meta description is 164 characters, just over the ~160 shown in search
  results.
- **Booking-page variants:** informational notices for the four `?service=…` addresses.
- **HTTPS:** reported only because the local copy runs without it.

### 2. Files changed

**Backend:**
- New module `audits/`: `fetch.py`, `parse.py`, `crawler.py`, `checks.py`, `pagespeed.py`,
  `models.py`, `schemas.py`, `service.py`, `router.py`.
- `jobs/handlers.py` (`audit.run`, `audits.schedule`), `jobs/registry.py` and `service.py`
  (a time limit per job kind).
- `worker.py` (nightly scheduled audits).
- `plans/` (audit limits, monthly usage, caps), `websites/` (audit schedule),
  `rbac/catalogue.py` (`audits.read`, `audits.run`).
- `core/config.py` (crawler and PageSpeed settings; private crawling refused in
  production).
- Migration `0015`.
- Tests: new `test_crawler.py` and `test_audits.py`; updated cross-tenant, plans and role
  tests.

**App:**
- New `features/audits/` (Audits list, audit page, shared parts, tests).
- The Plan page shows caps; navigation, routes, types, API calls.

**Docs:** `ARCHITECTURE.md`, `SECURITY.md` (fetching safely), `DEPLOYMENT.md` (the optional
PageSpeed key), `HYBRID_SAAS_PLAN.md` (audit limits in the plans table), `.env.example`, this
tracker.

### 3. Database changes (migration `0015`)

| Change | Existing data |
|---|---|
| `audits` (status, trigger, page limit, counts, site-level facts, timings) | None |
| `audit_pages` and `audit_issues` (check, severity, area, page, details) | None |
| `usage_records` (organization, metric, month, count) | None |
| `websites.audit_frequency` (off, weekly, monthly) | All off |
| Plan limits `limits.audits_per_month` and `limits.pages_per_audit` | The approved values for all six plans |
| Row-level security on the new tables (an agency can write audits and usage for a business that shared its workspace) | None |

Run up, checked, down and up again; the test suite builds from it.

### 4. Tests

| Suite | Result |
|---|---|
| Backend (pytest) | **414 passed** (was 367) |
| App (Vitest) | **121 passed** (was 113) |
| Website (Vitest) | 92 passed (unchanged) |

The new backend tests cover:
- **Safety:**
  - 15 address types allowed or refused
  - private addresses refused at connection time, including through a redirect
  - only http and https; size caps; proxies never used
- **Crawling and reading:**
  - reading pages, including broken HTML
  - robots.txt, sitemaps, page limits, another port as another site
- **Full audits** against a local test site with known problems:
  - each finding, and new or fixed against the previous audit
  - an unreachable site
  - one audit at a time
  - PageSpeed parsing
- **Limits, schedules and access:**
  - the monthly limit and the page cap
  - schedules, including when the plan's limit is used up
  - who can view or run audits; another workspace's website
  - an agency auditing a shared workspace on the business's plan
- **The cross-organization attack suite** found the new routes by itself, and every attempt
  failed.

**Browser check** against the real API:
- A real audit of the Outlogik website ran: 24 pages checked.
- Results, AI search readiness and issues displayed correctly. No page errors.
- An axe scan of both pages found no problems in light or dark mode.

### 5. Unfinished (on purpose)

- **Links to other websites aren't checked yet;** only the site's own pages are. External link
  checks can come later, with rate limits.
- **No email when an audit finishes or finds new errors.** That comes with alerts and
  notifications (H1.5).
- **Pages that need JavaScript to show their content** are read as the server sends them. The
  crawler doesn't run JavaScript. Most business sites (and Outlogik's, which is rendered on
  the server) are fine.
- **Page speed waits for a Google API key** (DEPLOYMENT.md has the steps).

### 6. Security notes

- **Server-side request forgery** is the main risk of a crawler, and it's handled at
  connection time, not just when a website is added. The tests include a redirect to an
  internal address.
- **`CRAWLER_ALLOW_PRIVATE`** exists only for tests. The API refuses to start with it in
  production.
- **Untrusted pages and sitemaps** are read as text: no XML parser, no JavaScript, size-capped.
- **Audit results** are under row-level security, and the cross-organization suite covers the
  new routes.

### 7. Next: H1-7 integrations and Google

Encrypted credentials for connected services:
- Google sign-in for connecting accounts
- Google Analytics 4 and Search Console data synced into history, including the AI referral
  traffic view from the addendum

Google's app verification can take weeks, so it's worth applying as soon as the Google Cloud
project exists.

---

## H1-5: Background jobs

### 1. What was completed

- **A job system** for work that shouldn't happen during a click:
  - **Recorded:** every job is in a `jobs` table, with its kind, status, attempts and last
    error.
  - **Retried:** a failure is tried again with a growing wait (30 seconds, 2 minutes,
    8 minutes, …). After the kind's maximum attempts the job "gives up", and is kept for a
    person to look at and retry.
  - **No duplicates:** the same work can't be queued twice, and a message delivered twice
    still runs once.
  - **Recovered:** jobs left half-done by a stopped worker, or whose message was lost, are
    picked up again automatically.
- **Email now goes through a job.** A slow or failing mail server no longer slows down
  sign-up, invitations or the website forms, and failed emails are retried. Once an email is
  sent (or gives up), its text, which can contain a sign-in or reset link, is erased from the
  job record.
- **Scheduled jobs:**
  - **Every 5 minutes:** recover stuck or lost jobs.
  - **Nightly (3:17 am Toronto time):** delete expired and idle sessions, used or expired
    one-time tokens, and finished jobs older than 30 days. Nothing deleted any of these
    before, so they were piling up.
- **Two modes:**
  - **inline** (development and tests): jobs run straight away inside the API, so nothing
    extra runs on your computer
  - **queue** (staging and production): a separate worker process (Celery with Redis/Valkey)
- **DigitalOcean:** both app specs get a `worker` component, built from the API's image. Each
  environment has its own queue name, because staging and production share one Valkey.
- **Command line:** `python -m app.cli jobs [--status dead]` and `retry-job ID`, until the
  Super Admin area shows job health (H1.5).

**Found and fixed while testing:** a job freed from a stopped worker was requeued but only
re-sent on the next recovery run, 5 minutes later. It's now sent straight away.

### 2. Files changed

- **New:** `app/jobs/` (`models.py`, `registry.py`, `service.py`, `handlers.py`),
  `app/worker.py`, migration `0014`, `tests/test_jobs.py`.
- **Changed:**
  - `core/email.py` (`send_email` queues; `deliver` sends), `core/config.py`
    (`JOBS_MODE`, `JOBS_QUEUE`)
  - `main.py`, `models.py`, `cli.py` (`jobs`, `retry-job`)
  - `pyproject.toml` / `uv.lock` (Celery)
  - `.env.example`
- **Deployment:** `.do/staging/app.yaml`, `.do/production/app.yaml` (worker component, queue
  settings); `.github/workflows/ci.yml` (the API image must be able to start the worker).
- **Docs:** `ARCHITECTURE.md`, `SECURITY.md`, `DEPLOYMENT.md` (§6: the worker, its secrets,
  checking and retrying jobs), `README.md`, `HYBRID_SAAS_PLAN.md`, this tracker.

### 3. Database changes (migration `0014`)

| Change | Existing data |
|---|---|
| New table `jobs`: kind, organization (optional), status, payload, dedupe key (unique while waiting or running), attempts, max attempts, run after, started/finished, last error | None |
| Row-level security on `jobs` | None |

Run up, checked, down and up again; the test suite builds from it.

### 4. Tests

| Suite | Result |
|---|---|
| Backend (pytest) | **367 passed** (was 353) |
| App (Vitest) | 113 passed (unchanged; no app changes) |
| Website (Vitest) | 92 passed (unchanged) |

The 14 new tests cover:
- recording and success; erasing sensitive content
- retries and the backoff schedule; giving up after the last attempt, and a person retrying
- running once when delivered twice; no duplicate queued work
- unknown kinds refused
- recovery of stuck and lost jobs (and giving up on stuck ones with no attempts left)
- the queue being down not breaking the request
- queue mode through Celery
- scheduled work recorded once
- email through the queue (with its text erased), and a mail-server failure retried while the
  request still succeeds
- the nightly cleanup deleting only what's no longer needed

**With a real worker** (Celery, the local Redis and Postgres, the API in queue mode):
- A sign-up's confirmation email was sent by the worker, and its text erased from the job.
- With the worker stopped, a sign-up still succeeded and its email waited in the queue. When
  the worker restarted, the email was sent.

### 5. Unfinished (on purpose)

- **Job health on screen** (counts, failures, retry button) comes with the Super Admin control
  center (H1.5). Until then, the command line.
- **Inline mode (development) doesn't retry failed jobs,** since there's no worker to come back
  later. Development email goes to Mailpit or the console anyway.
- **No metrics or alerting on the queue yet:** monitoring is in DEPLOYMENT.md's checklist for
  launch.

### 6. Security notes

- **Email text erased:** an email's text, which may contain a sign-in, reset or invitation
  link, is erased from the job record once sent or given up. A failed email therefore can't be
  retried by staff; the person asks again from the app.
- **Errors stored briefly:** last errors are stored truncated, without the payload.
- **Automatic deletion:** finished jobs after 30 days; expired and idle sessions and used
  tokens nightly (less personal data kept, as PIPEDA asks).
- **`jobs` is under row-level security** like other tenant tables.
- **Separate queues** for staging and production, so neither can run the other's jobs.
- **Handlers filter by organization themselves.** They run without an organization set, as
  the architecture checklist says.

### 7. Next: H1-6 SEO crawler and audits

Our own crawler with safe fetching (blocking private addresses), on-page and technical checks,
the **AI search readiness** checks from the addendum, PageSpeed, scheduled audits on the new job
system, history and comparison, and prioritized issues. Monthly audit limits per plan arrive
here, with the first metered usage records.

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
