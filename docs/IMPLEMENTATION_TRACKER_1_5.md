# Implementation tracker — Phase 1.5 (public marketing website)

Plan: [`PHASE1_5_PLAN.md`](PHASE1_5_PLAN.md) (**revision 2, agency direction, approved 2026-11-15**). Spec: [`specs/MARKETING_WEBSITE_SPEC.md`](specs/MARKETING_WEBSITE_SPEC.md).

> **2026-11-15: direction change.** Outlogik is a digital marketing agency; the website sells its services and the app is the client portal. Steps 1–2 carry over; steps 3 onward follow plan revision 2 once approved. The table below is from revision 1.

**Milestone A** (launchable site) = steps 1–7, 11, 12, and the release checks in 14.
**Milestone B** (CMS and resources) = steps 8–10, 13, and the rest of 14.

| # | Step (plan revision 2) | Milestone | Status |
|---|---|---|---|
| 1 | Brand, palette, marketing app shell, CI | A | ✅ Done |
| 2 | Staff roles, site settings, statuses, public API | A | ✅ Done |
| 3 | Agency navigation, invite-only sign-up, portal features, homepage | A | ✅ Done |
| 4 | Service pages (4) and `/services` | A | ⏳ Next |
| 5 | Who we help, How we work, Pricing (how it works), About | A | ☐ |
| 6 | Leads: consultation, contact, newsletter; attribution; notifications; old-path redirects | A | ☐ |
| 7 | Admin area: leads inbox, settings, portal feature statuses | A | ☐ |
| 8 | CMS backend and media library | B | ☐ |
| 9 | CMS admin UI | B | ☐ |
| 10 | Resources: blog, guides, glossary | B | ☐ |
| 11 | SEO (adds `ProfessionalService` schema once business details are known) | A | ☐ |
| 12 | Analytics and consent; legal pages | A | ☐ |
| 13 | Content pass | B | ☐ |
| 14 | QA and release | A + B | ☐ |

## On hold (decisions 12, 13, 15)

- **Legal details** (business name, address, province, sales and privacy emails): legal pages are drafted but not published, and the footer shows no legal links until they are.
- **Domain and hosting:** the site and app addresses are build settings (`OL_SITE_URL`, `OL_APP_URL`), with local defaults.
- **Lead notification email:** leads will still be stored and shown in the admin area.

## Step 1 — brand, palette, marketing app shell

- **Layout (a change from the plan):** the marketing site is a second project in the existing Angular workspace (`frontend/projects/marketing`), rather than a separate top-level `marketing/` folder. Both projects share one Angular version, one lockfile and the brand code, and each still builds and deploys on its own. Shared brand code lives in `frontend/brand/`, not a top-level `brand/`, so both projects can use it without file-path workarounds.
- **`frontend/brand/`** holds:
  - `scss/_palette.scss`: the spec's palette, plus neutral in-between steps and status colours
  - `assets/logo` and `assets/icons`: logos, favicon, home-screen icons
  - `logo/` and `icon/`: shared Angular components, imported as `@brand/...`
- **Palette (decision 3):** the app now uses the spec's colours (black `#000`, charcoal `#171717` text, `#737373` muted, `#E5E5E5` borders, `#FAFAFA` surfaces). Dark mode is built from the same greys. The logo is pure `#000` / `#FFF`, and the PNG icons and favicon were regenerated.
- **Icons:** the generator writes one set per site (`icons-app.ts` with 36 icons, `icons-marketing.ts` with 28); each site provides its own with `provideIcons()`.
- **Server-rendering fixes in shared components:** the logo picks its SVG with a CSS class (the server can't set CSS custom properties), and the icon renders its `<svg>` as host markup (the server can't set `innerHTML` on SVG elements).
- **Marketing app** (Angular 22, `@angular/ssr` 22.2.7, Express 5.3.0):
  - The homepage is prerendered at build time; unknown paths are server-rendered with a real **404** status.
  - Hydration with event replay, so clicks made before the JavaScript loads still work.
  - Light theme, Albert Sans, a Bootstrap subset with no utilities API (CSS 42 kB, 7.5 kB compressed).
- **Header:**
  - sticky, with mega-menus for Platform and Solutions and a dropdown for Company
  - menus are disclosure buttons with `aria-expanded`; one is open at a time
  - Escape closes a menu and returns focus; clicking outside, tabbing away or navigating also closes it
  - "In development" labels on the six unbuilt modules; Resources stays hidden until content exists
- **Phone drawer:** a native `<dialog>`, which provides the focus trap and Escape to close.
- **Footer:** a black band with Platform, Solutions and Company columns. Legal links appear once the legal pages are published.
- **Calls to action:** "Log in" and "Get started" go to the app (`OL_APP_URL/login`, `/register`). Override them at build time, e.g.
  `ng build marketing --define "OL_APP_URL='https://app.example.com'" --define "OL_SITE_URL='https://example.com'"`.
- **Bundle:** the first download is 369 kB raw, about 98 kB compressed. Angular itself is about 256 kB of that. Pages are readable before any JavaScript runs because the HTML is server-rendered. The budget is 400 kB warning, 600 kB error.
- **Tests:** 7 marketing unit tests (header links, menu behaviour, Escape and focus, outside click and navigation, status labels, hidden Resources, footer); the 65 app tests still pass.
- **Checked by running it:**
  - the built server returns full HTML (heading, title, 21 module links, app links), a 404 for unknown paths, and the logo and favicon
  - in Chromium: keyboard menu behaviour, the drawer focus trap, no horizontal scroll at 390 and 820 px, no console errors
  - the app checked in light and dark with the new palette
- **CI:** the frontend job now tests and builds both projects, starts the marketing server, and checks for server-rendered HTML and a 404.

## Step 2 — staff roles, site settings, module statuses, public API

- **Staff roles** (`users.platform_role`, migration `0003`): `content_editor` (website content, milestone B) and `site_admin` (the whole admin area). Super Admins count as site admins. Granted and removed only from the command line, and audited:
  `python -m app.cli grant-staff --email … --role site_admin` and `python -m app.cli revoke-staff --email …`.
  `/auth/me` returns `platform_role`, so the app can show the admin area in step 7. Staff roles are separate from organization roles; agencies never get one.
- **Admin API** (`/api/v1/admin/…`): every route requires a staff role. Anyone else gets **404**, so the API doesn't reveal itself (401 if signed out). A test checks every admin route for this, like the organization permission matrix.
  - `GET/PUT /admin/site/settings` (site admins)
  - `GET /admin/site/modules`, `PATCH /admin/site/modules/{slug}`
  - Changes are audited as `site.settings_update` (with changed fields) and `site.module_update` (with from/to).
- **Site settings** (`site_settings`, one row): company description, tagline, contact and sales email, phone, address, social links (fixed list of networks, http(s) URLs only), call-to-action labels, the early-access flag, and SEO defaults. Validated strictly (unknown keys rejected); empty values mean "not shown".
- **Product modules** (`product_modules`): name, summary, status (`available`, `in_development` or `hidden`) and order. They're seeded with Phase 1 reality, where only Client Management is available. Startup restores any missing defaults without overwriting admin changes (needed because the test suite empties tables).
- **Public API** (`/api/v1/public/site`): settings and non-hidden modules. No sign-in, nothing private, and `Cache-Control: public, max-age=60`.
- **Marketing site:**
  - `SiteData` (an `httpResource`) loads `/api/public/site`. The header, menus, drawer and footer use it: module statuses, the CTA label, and the tagline, description, contact email and social links once set.
  - If the API is down, the built-in defaults are used and the page still renders.
- **Change from the plan:** marketing pages are now **server-rendered on request and cached for 60 seconds** (`s-maxage=60, stale-while-revalidate=300`) instead of prerendered at build. Admin changes (statuses, settings) show up within a minute without rebuilding the site. Unknown paths still return 404 with `no-store`.
- **Marketing server** (`server.ts`):
  - forwards `GET /api/public/*` to the API (`API_INTERNAL_URL`, default `http://localhost:8000`) with a 5-second timeout, returning 502 if the API is down; POST comes with the forms in step 6
  - adds security headers (`nosniff`, `DENY` framing, a referrer policy, a permissions policy) and stops announcing Express
  - in development, `ng serve marketing` forwards `/api/public` through `proxy.conf.json`
- **No double fetching:** during rendering, the site requests the same relative URL the browser uses, so the response is embedded in the page and the browser reuses it. A first attempt rewrote the URL on the server; the embedded copy was then never matched, and the browser fetched again. Checked: no API calls from the browser on page load.
- **Tests:** 16 new backend tests (190 total) and 3 new marketing tests (10 total).
- **Checked end to end:** the page showed the database statuses; marking SEO Management available and hiding Reporting appeared on the next render; the proxy returned the data; with the API stopped the page still rendered (proxy 502); unknown paths returned 404.

## Step 3 — agency navigation, invite-only sign-up, portal features, homepage

- **Direction (plan revision 2, approved with recommendations A–F):** Outlogik is a digital marketing agency. Services are SEO, Social Media Management, Website Analytics & Reporting and Content Marketing. There are no public prices, the main action is "Book a free consultation", and the app is the invite-only client portal.
- **Invite-only sign-up:**
  - `SIGNUP_MODE` now defaults to `invite_only` (the test suite sets `open`, because it creates accounts that way).
  - `/api/v1/public/site` returns `signup_open`. The app's sign-in page then says "Ask your Outlogik contact for an invitation" instead of offering sign-up, and `/register` explains that accounts are by invitation. A small `SignupStatus` service, used only by those two pages, does the check.
  - New CLI command to set up organizations without public sign-up: `python -m app.cli create-organization --name "Outlogik" --owner-email … [--owner-name …]`. It creates the owner, email-verified, if needed, and is audited.
- **Portal features** replace product modules (migration `0004`): `portal_features`, seeded with seven entries.
  - Available: own client portal, websites in one place, a record of the work.
  - In development: monthly reports, analytics dashboards, social calendar approvals, SEO health checks.
  - Admin API: `/api/v1/admin/site/portal-features`, audited as `site.portal_feature_update`.
- **Settings:** `consultation_cta_label` ("Book a free consultation") replaces the old CTA labels and the early-access flag; the migration removes those keys from stored settings. Stored settings are read tolerantly, ignoring keys from older versions; writes stay strict.
- **Navigation:** Services ▾ (4) · Who we help ▾ (4) · How we work · Resources (hidden until content exists) · Pricing · Company ▾ (About, Contact). On the right: **Log in** (client portal) and **Book a free consultation**. The footer mirrors this, with contact details and social links once set. Nothing on the site links to `/register`.
- **Homepage, built from the approved mockup:**
  - hero with a real client-portal screenshot
  - the four services
  - "Why Outlogik", including "Straight answers: no one can guarantee rankings"
  - the four-step process
  - client portal features with honest status labels, from the admin area
  - Who we help, Tools we work with, how pricing works, and a closing call to action
  - **Results and testimonials are deliberately absent** until real ones exist (a test checks this).
- **Screenshots:** `frontend/scripts/capture-marketing-screenshots.mjs` seeds example data through the API and captures what a client sees in the portal. It writes 1440×720 and 2× WebP files to `projects/marketing/public/images/`. `<mk-screenshot>` shows them in a browser frame with a fixed size (no layout shift), lazy loading below the fold, and an "example data" caption.
- **Styles:** `styles/_sections.scss` holds the mockup's sections, with tablet and phone layouts (four-column cards go to two, then one; split sections stack).
- **Tests:**
  - backend: 6 new (196 total)
  - app: 2 new for invite-only (67)
  - marketing: rewritten for the agency site plus homepage tests (16), with shared helpers in `projects/marketing/src/testing/marketing.ts`
- **Checked by running it:**
  - the homepage is rendered on the server with the API
  - all 8 section headings are present, with 4 "In development" labels
  - the browser makes no API calls after load; screenshots load when scrolled into view
  - no horizontal scroll at phone or tablet width, and no console errors
- **Links to pages not built yet** (services, who we help, how we work, pricing, about, contact, book a consultation) are built in steps 4–6, before anything is released.
