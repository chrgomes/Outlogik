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
| 4 | Service pages (4) and `/services` | A | ✅ Done |
| 5 | Who we help, How we work, Pricing (how it works), About | A | ✅ Done |
| 6 | Leads: consultation, contact, newsletter; attribution; notifications; old-path redirects | A | ✅ Done |
| 7 | Admin area: leads inbox, settings, portal feature statuses | A | ✅ Done |
| 8 | CMS backend and media library | B | ☐ |
| 9 | CMS admin UI | B | ☐ |
| 10 | Resources: blog, guides, glossary | B | ☐ |
| 11 | SEO (adds `ProfessionalService` schema once business details are known) | A | ✅ Done |
| 12 | Analytics and consent; legal pages | A | 🟡 Built; legal pages go live when the legal details are entered in the admin area |
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

## Step 4 — service pages and `/services`

- **Pages:**
  - `/services` lists the four services, each with what it includes, then explains how they work together.
  - `/services/seo`, `/services/social-media-management`, `/services/website-analytics-reporting` and `/services/content-marketing` each have these sections:
    - a heading with breadcrumbs
    - what we do
    - what's included (six items)
    - what you get
    - how we work (four steps)
    - what you'll see in the client portal
    - questions
    - related services
    - a closing call to action
- **Content** lives in `config/services-content.ts`, one entry per service, separate from the layout so it's easy to review and edit. It loads only with the service pages, not with the homepage. Page titles are in `SERVICES` in `config/site.ts`.
- **Honest claims:**
  - The SEO questions state plainly that no one can guarantee rankings. A test checks every service's copy for guarantee phrases.
  - The client-portal section shows only the features relevant to each service, with the statuses staff set in the admin area. "In development" features are labelled. The section disappears if none is shown.
  - Where today's process differs from the portal's future features, the answers say so: approvals happen by email or a shared document, and reports are sent each month until portal reports are ready.
- **For your review (business commitments in the copy):**
  - nothing is published without the client's approval (social media, content)
  - clients own their social accounts
  - paid ads are not part of the social media service
  - an optional monthly review call (analytics)
  - consent-aware tracking
- **Shared building blocks** for the remaining pages:
  - `<mk-page-hero>`: breadcrumbs, the single h1, lead, actions
  - `<mk-faq>`: native `<details>`, so it works before JavaScript loads
  - `<mk-cta-band>`: the closing call to action
- **Routing:**
  - Each page loads on demand.
  - Server routes are listed per service, so an unknown address such as `/services/paid-ads` shows the 404 page with a 404 status.
  - Pages are cached like the homepage (`s-maxage=60`).
- **Meta descriptions** are set per page. Canonical URLs, Open Graph and structured data come in step 11. The default description in `index.html`, and the homepage title, now describe the agency, replacing the old software-product wording.
- **Budget:** the marketing site's initial-bundle warning went from 400 kB to 450 kB (the error limit stays 600 kB). It is now 403 kB, or 106 kB compressed. Shared page styles and the router's on-demand loading added about 9 kB.
- **Tests:** 16 new marketing tests (32 total); the app's 67 still pass.
- **Checked by running it:**
  - all five pages render on the server with status 200, one h1 and the right title; `/services/paid-ads` returns 404
  - the cache header is present
  - moving between service pages in the browser works, with no console errors

## Step 5 — Who we help, How we work, Pricing, About

- **Who we help:**
  - `/who-we-help` and one page for each of the four business types (decision B).
  - Each page has these sections:
    - "Sound familiar?": common problems for that kind of business
    - how each service helps, in the order we'd recommend
    - our approach (three points)
    - questions
    - links to the other business types
    - a closing call to action
  - Copy is in `config/audiences-content.ts`.
- **How we work:**
  - The four-step process in detail.
  - The client portal with both real screenshots, labelled "example data".
  - Every portal feature with its status ("Available" or "In development", set in the admin area).
  - What we need from clients, the tools we work with, and questions.
- **Pricing:** how pricing works, with no prices published. It covers:
  - three steps to a price
  - what affects the price
  - what every proposal includes
  - one-off projects and monthly services
  - questions, including the optional budget field (decision E)
- **About:**
  - why we work this way, four values, and "what we won't do"
  - no invented team, history, numbers or results (decision C); the team and story are added once provided
- **For your review (business commitments in the copy):**
  - one main point of contact per client
  - the client portal is included at no extra cost
  - clients own their accounts and work
  - the plan is reviewed regularly
  - no fixed minimum budget
  - agreement terms are set in each proposal
  - we never write, buy or fake reviews
  - no bought links
  - no paid shopping ads today (e-commerce)
- **Routing:**
  - Server routes are now generated from the page routes, so every page gets the cache headers automatically.
  - Unknown addresses, such as `/who-we-help/dentists`, still get a 404 status.
  - Meta descriptions use a small `pageDescription()` helper.
- **Tests:**
  - 19 new marketing tests (51 total), with a shared `visit()` helper that renders pages through the real routes.
  - The copy checks also cover testimonials, case studies and "trusted by".
  - The Pricing test checks that no prices appear; the About test checks there's no invented history.
- **Checked by running it:**
  - all 8 new pages render on the server with status 200, one h1 and the right title
  - unknown addresses return 404
  - no console errors, and no horizontal scrolling at phone width (390 px)
- **Still to build:** `/contact` and `/book-a-consultation` (step 6). Links to them show the 404 page until then.

## Step 6 — leads: forms, attribution, notifications, redirects

- **Backend (`app/modules/leads`, migration `0005`):**
  - `leads` holds consultation requests and contact messages. Statuses are new, contacted, qualified, closed and spam; the admin inbox comes in step 7.
  - `newsletter_subscribers` holds each subscriber's consent record.
  - Public endpoints:
    - `POST /api/v1/public/leads/consultation`
    - `POST /api/v1/public/leads/contact`
    - `POST /api/v1/public/newsletter`
    - `POST /api/v1/public/newsletter/confirm`
    - `POST /api/v1/public/newsletter/unsubscribe`
- **Protection** (details in [`SECURITY.md`](SECURITY.md#website-forms)):
  - an Origin check instead of CSRF (public endpoints only)
  - a honeypot and a minimum fill time; spam is kept for review but never emailed
  - rate limits per IP address and per email
  - strict validation
- **Newsletter (CASL):** an unticked consent box, the exact wording stored, double opt-in, and an unsubscribe link. Confirming or unsubscribing needs a button click on the website, so email link scanners can't do it.
- **Notifications:**
  - Each new lead is emailed to `LEAD_NOTIFICATION_EMAILS`. This is **empty until decision 15**, so nothing is sent yet; leads are still stored.
  - The person who sent the form gets a short confirmation email.
- **Attribution:**
  - The first page of each visit, its referrer and UTM tags are kept in `sessionStorage`. There are no cookies.
  - They're sent with any form, along with the page it was sent from.
  - The team notification lists them.
- **Website:**
  - `/book-a-consultation` has:
    - name, email, company, website, phone, best time to reach you
    - the services, at least one ("Not sure yet" counts)
    - an optional budget range (decision E)
    - a message
    - "What happens next"
  - Service pages pre-select their service (`?service=seo`).
  - `/contact` has a topic and a message, plus contact details from the site settings once they're set.
  - The footer newsletter form loads when the footer scrolls into view, so it adds nothing to the first page load.
  - `/newsletter/confirm` and `/newsletter/unsubscribe` are hidden from search engines.
  - The form options live in `config/forms.ts`. A backend test checks they match what the API accepts, and that the consent wording is identical.
- **Redirects** (website server):
  - `/platform*` → `/services`
  - `/solutions*` → `/who-we-help`
  - `/book-a-demo` and `/get-started` → `/book-a-consultation` (301, keeping query strings)
  - `/login` → the client portal's login (302)
- **Proxy:** forwards GET and POST to the API, with the browser's Origin and user agent, a 32 kB body limit and `Retry-After`. `TRUST_PROXY` passes visitors' real IP addresses through a reverse proxy.
- **For your review:**
  - The budget ranges are in dollars per month: under $1,000; $1,000–2,500; $2,500–5,000; over $5,000; not sure. Change them if they don't fit your pricing.
  - The newsletter wording
  - The confirmation emails' text
- **Tests:**
  - backend: 27 new (223 total)
  - website: 12 new (63 total)
  - app: 67, unchanged
- **Checked by running it** (API, server-rendered site, real browser):
  - A visit arriving from a LinkedIn campaign link went from homepage to SEO page to "Book a free consultation" (SEO pre-ticked). The request was stored with the services, budget, landing page and UTM tags, and the acknowledgement email was sent.
  - Newsletter sign-up from the footer sent a confirmation email; its link confirmed the subscription.
  - Without the website's Origin, the API refused the form (403).
  - Old addresses redirected, `/login` went to the app, PUT to the proxy was refused (405), and there were no console errors.
- **Size:** initial load 427 kB (114 kB compressed), under the 450 kB warning.

## Step 7 — website admin area (in the app)

- **Where:** `/admin` in the Outlogik app, for **site admins** only.
  - Staff open it from the workspace menu (top left), under "Outlogik staff", and go back to an organization the same way.
  - It uses the same sidebar and top bar as the app, with a "Website admin" label and its own menu: Inbox, Newsletter, Settings, Portal features.
  - Everyone else gets "not found", matching the API, which answers 404 to non-staff.
  - Staff with no organization go straight to `/admin` after signing in.
  - Content editors get no admin pages until the CMS (milestone B).
- **Leads inbox** (`/admin/leads`):
  - newest first, with the services asked about, the campaign source and the note count
  - filters by status (with counts) and type, and search by name, email or company
  - Spam stays out of view unless the Spam filter is chosen.
  - **Export CSV** uses the current filters. Cells a spreadsheet would run as formulas are neutralised, and each export is audited.
- **Lead detail:**
  - the request (services, budget, best time, topic, message) and contact details; the website link opens safely in a new tab
  - "Where they came from": the page the form was sent from, the first page of the visit, the referrer and the campaign
  - a status menu (new, contacted, qualified, closed, spam), audited
  - notes with author and time
  - **Reply** opens an email to the person
  - **Delete**, for privacy requests or junk. It asks first, and the audit entry holds no personal details.
  - If a lead was caught as spam, the page says why.
- **Newsletter** (`/admin/newsletter`):
  - subscribers with their status and the dates of consent and confirmation
  - **Export confirmed** downloads the email addresses with their consent wording, for an email service; audited
  - Delete, for privacy requests
  - The page notes that sending newsletters isn't built into Outlogik.
- **Website settings** (`/admin/settings`): tagline, short description, contact and sales email, phone, address, social links, the main button's wording, and search defaults. Empty fields are hidden on the website. Changes reach the website within about a minute.
- **Portal features** (`/admin/portal-features`): set each feature to Available, In development or Hidden.
- **API:**
  - `GET /admin/leads` (filters, search, paging)
  - `GET /admin/leads/counts`
  - `GET /admin/leads/export.csv`
  - `GET`, `PATCH` and `DELETE /admin/leads/{id}`
  - `POST /admin/leads/{id}/notes`
  - `GET /admin/newsletter/subscribers`, `…/export.csv`, `DELETE …/{id}`
  - Migration `0006` adds `lead_notes`.
- **Fixed along the way:** the new admin guard asked Angular for a service after waiting for the user, which Angular doesn't allow. A test caught it, and it's fixed.
- **Tests:**
  - backend: 10 new (233 total), including that every admin route requires a staff role
  - app: 12 new (79)
  - website: 63, unchanged
- **Checked in a real browser** with the development API and example enquiries sent through the website form endpoint:
  - signed in as a site admin and switched to Website admin from the workspace menu
  - the inbox showed 4 enquiries; the bot message was hidden and appeared under the Spam filter
  - the CSV export had 4 rows
  - on Marco's consultation: marked Contacted, added a note, and checked his campaign source (Google, paid)
  - saved a contact email, which the website's public settings returned straight away
  - Portal features and Newsletter pages loaded with no errors

## Step 11 — search engines and link previews

- **Every page, rendered on the server** (search engines and link previews see it without running JavaScript):
  - **title:** the page name plus the ending from the site settings (" · Outlogik", editable in the admin area); the homepage has its own full title
  - **description:** the page's own, or the default from the site settings
  - **canonical URL** (the page's main address, without query strings such as `?service=seo` or campaign tags)
  - **link previews:** Open Graph and Twitter card tags, with a share image
  - Error pages and newsletter links get `noindex` and no canonical URL.
- **Structured data (JSON-LD):**
  - **Organization** on every page: name, logo, description, tagline, and the contact email, phone and social links once they're set in the admin area
  - **WebSite** on the homepage
  - **BreadcrumbList** on every inner page, from the visible breadcrumbs
  - **Service** on each service page
  - `ProfessionalService` with an address and service area is added once those are decided (decisions 12 and A).
  - The data is escaped so visitor-editable text can never break out of its script tag.
- **`/robots.txt` and `/sitemap.xml`** are served by the website's server. The sitemap is built from the page routes: 16 pages now, and new pages are added automatically. The robots file points to the sitemap and blocks `/api/` and `/newsletter/`.
- **Staging:** `SITE_NOINDEX=true` blocks everything in robots.txt and adds `X-Robots-Tag: noindex` to every response, so a staging site never appears in search results.
- **Share image and logo:**
  - `og-default.png` (1200×630, black, with the logo and "Digital marketing, handled. And always in view.")
  - `outlogik-logo-512.png` for search engines
  - Both are rendered from the brand files and the bundled font by `scripts/build-share-images.mjs`. No third-party services.
- **How it works:** `seo/seo.ts` holds one `Seo` service. The router's title strategy passes in the route's title and path; pages add a description (`pageDescription()`) and structured data (`structuredData()`) while they're open. One effect writes all the tags whenever these or the site settings change, so moving between pages never leaves stale tags.
- **Removed:** `og:locale`, which would have signalled Canada before the service area is decided.
- **Tests:**
  - website: 9 new (72 total), covering titles, descriptions, canonical URLs, structured data, clean-up between pages, noindex, settings-driven titles, escaping, the sitemap and robots.txt
  - CI's server-rendering check now also confirms the canonical URL, the share image, the Service data, robots.txt and the sitemap.
- **Checked by running it:**
  - the server-rendered SEO page has every tag, with one description tag (no duplicates)
  - after loading in a browser and moving between pages, the title, canonical URL and structured data update and stay single
  - the staging switch blocks robots and adds the header
  - no console errors
- **To do at launch (step 14):**
  - build with the real domain (`OL_SITE_URL`), so canonical URLs, the sitemap and share links use it
  - submit the sitemap to Google Search Console and Bing Webmaster Tools

## Step 12 (part 1) — analytics, cookie banner, Content-Security-Policy

Legal pages (privacy, terms, cookies) are the second part. They wait for the business details (decision 12).

- **Optional analytics tools:** Google Analytics 4, Google Tag Manager and Microsoft Clarity.
  - Each is switched on by entering its ID in the admin area (Website settings → Analytics). All are **off by default**, and the IDs are checked against each tool's format.
  - With none set, the website sets **no tracking cookies and shows no banner**: there's nothing to ask about.
- **Cookie banner** (`consent/`):
  - It appears only when a tool is switched on and the visitor hasn't chosen yet.
  - It names the tools in use and says plainly what they do.
  - **Accept analytics** and **Reject analytics** look identical, so neither is nudged.
  - The banner is never in the server-rendered HTML, so visitors who have already chosen never see it flash.
  - The choice is kept for a year in one first-party cookie, `ol_consent` (strictly necessary: it only remembers the choice).
  - **"Cookie settings"** in the footer (shown only when a tool is on) reopens the banner and says which choice is current.
  - Withdrawing deletes the tools' cookies (`_ga*`, `_clck` and the like) and reloads the page, so their code stops running.
- **Tools load only after Accept:**
  - Google Analytics sends a page view for every page, including moves within the site (one per address, no duplicates).
  - Form submissions are reported as conversions: `generate_lead` for consultations and messages, `sign_up` for the newsletter.
- **Cookie-free conversion tracking:**
  - The leads inbox now has **"Where leads came from"**: the last 90 days of consultations, messages and confirmed newsletter sign-ups, grouped by campaign tag or referring site.
  - It's built from the website's own records, so it works with or without analytics and needs no consent (`GET /api/v1/admin/leads/sources`).
- **Content-Security-Policy** on every page:
  - Each response gets a fresh random nonce, added to every script tag by the website's server.
  - Only those scripts, and what they load (`strict-dynamic`), may run. That covers the site's own lazy-loaded code, and the analytics tools after consent.
  - Also: `object-src 'none'`, `base-uri 'self'`, `form-action 'self'`, `frame-ancestors 'none'`.
  - Inline styles stay allowed, because Angular's component styles need them and styles can't run code.
  - The analytics hosts are listed so the tools work once switched on; nothing contacts them without consent.
  - The CSP helpers are in `projects/marketing/src/csp.ts`.
- **Tests:**
  - backend: 2 new (235 total): analytics ID validation and public exposure, and the lead sources report
  - website: 7 new (79): the banner, consent, loading, conversions and the CSP
  - app: 1 new (80): checking analytics ID formats in settings
  - CI checks the CSP header and that every script carries the nonce.
- **Checked in a real browser:**
  - With no tool switched on: no banner, no "Cookie settings" link, and no CSP violations on pages, client-side navigation, the deferred newsletter form or a form submission.
  - With test IDs for GA4 and Clarity, and requests to Google and Microsoft answered by a stub so nothing left the machine:
    - before a choice: banner shown, **no requests to those hosts, no cookies**
    - after Accept: both tools loaded, one page view per page, and the contact form reported as `generate_lead`
    - after reopening "Cookie settings" and choosing Reject: `_ga` deleted, page reloaded, no requests to those hosts, and only `ol_consent=denied` left
  - The test IDs were removed afterwards.
- **Note:** with the short shared cache (`s-maxage=60`), a cache in front of the site may serve the same page (and its nonce) to several visitors for up to a minute. Each page's HTML and CSP header always match, so pages work. Reusing the nonce only matters if an attacker can already inject markup, which the policy and Angular's escaping guard against.

## Step 12 (part 2) — privacy policy and terms and conditions

- **Pages:** `/privacy-policy` and `/terms` (Terms and conditions). Both are written from what the website and client portal actually collect and do (spec §17), considering PIPEDA and CASL.
- **Published from the admin area, never as placeholders:**
  - Website settings has a new **Legal details** section: legal business name, province or territory, and privacy contact email. The existing Address field is also required.
  - Until all four are set, both pages answer **404**, carry `noindex`, are left out of the sitemap, and aren't linked anywhere.
  - Once saved, they go live within about a minute, with links in the footer, under both forms, under the newsletter sign-up and in the cookie banner.
  - The settings page says whether the pages are published.
  - Decision 12 can be completed by entering the details there; no release is needed.
- **The privacy policy:**
  - what's collected: forms, the newsletter's consent record, the client portal, and visit details kept in the browser and sent only with a form
  - IP address and browser for spam and security
  - how it's used; consent and withdrawing it
  - **cookies:** `ol_consent`, the portal's sign-in and security cookies, and the analytics tools **actually switched on** (or "none at present")
  - who it's shared with, storage outside the province and Canada, retention, safeguards, breach notification
  - rights to access, correct and delete, with a reply within 30 days
  - complaints to the Office of the Privacy Commissioner of Canada, plus the provincial commissioner for Quebec, British Columbia or Alberta when that's the province set
  - children, changes, and contact details
- **The terms:**
  - services are governed by each client's proposal or agreement, with **no guaranteed results**
  - acceptable use of the website; portal accounts by invitation
  - intellectual property, links, "as is" availability, limitation of liability
  - governing law: the province set in the admin area
- **For review before launch, ideally by a lawyer:**
  - retention is stated generally ("as long as we need it"), not as fixed periods
  - service providers aren't named, because hosting isn't decided
  - **Quebec:** if Quebec is chosen, Law 25 adds duties, such as naming a person in charge of personal information and assessing transfers outside Quebec, and French-language requirements may apply
- **Bug fixed along the way:** with `<base href="/">`, links like `href="#included"` loaded the homepage instead of scrolling. This affected:
  - "What's included" on service pages, "How we help", and "See the client portal"
  - the "Skip to content" links in both the website and the app
  - Section links now use the router with a fragment; skip links move focus to the main content.
  - CI now fails if a plain `href="#…"` link is added.
- **Tests:**
  - backend: 2 new (237 total): legal detail validation, and the app's province list matching the API's
  - website: 7 new (86): hidden until complete, 404 with noindex, business details, analytics tools named, provincial regulator, governing law, and the sitemap
  - app: 1 new (81): the Legal details section
- **Checked by running it:**
  - Without details: both pages returned 404 and weren't in the sitemap.
  - With example details: both returned 200, appeared in the sitemap, and were linked from the footer and the forms.
  - The example details were then removed.
  - All section links and the skip links work in the browser.
