# Outlogik — Phase 1.5 Plan (Public marketing website)

Status: **Draft for approval.** No code has been written yet.
Source: [`specs/MARKETING_WEBSITE_SPEC.md`](specs/MARKETING_WEBSITE_SPEC.md) (the spec). Section
numbers below (§) refer to it.

---

## 0. What the existing app means for the website (spec Phase A)

Findings from inspecting the Phase 1 codebase:

| Area | Today | What it means for the website |
|---|---|---|
| **Product features** | Clients, websites, team, roles and permissions, client portal, invitations, dashboard, audit activity | Only **Client Management** is a real, shippable capability. See section 1. |
| **Integrations** | None (GA4, Search Console, social and the rest are Phase 2+) | The integrations section must be a clearly labelled roadmap (§4.7). |
| **Registration** | `/register` in the app; open sign-up, switchable to invite-only | "Get Started" can link straight to it. |
| **Login** | `/login` in the app; HTTP-only session cookie on the app's domain | "Log In" links to it. The website never handles passwords. |
| **Super Admin** | A flag on users, created by CLI only; no admin UI yet | Basis for the CMS and leads admin (section 6). |
| **Brand** | Albert Sans, monochrome tokens (`#050505` ink, `#121212` / `#E0DFDD` dark), logo SVGs | Close to the spec's palette but not identical (decision 3). |
| **Frontend** | Angular 22 SPA, client-side rendered, lazy pages | Not suitable for SEO pages as-is, hence a separate server-rendered site (section 3). |
| **Deployment** | Not yet decided; Docker Compose is used only for local PostgreSQL, Redis and Mailpit | Needs hosting and domains for staging (decision 13). |

---

## 1. The honesty problem, and the proposed answer

The spec describes the full product vision (SEO auditing, analytics, social media, content,
reporting), and it also says, repeatedly: *don't advertise unfinished functionality, don't
publish empty pages, use authentic screenshots, never fabricate results* (§4.1, §4.7, §19,
§20, §22.20). Today, almost everything in the vision is unbuilt.

**Proposal (decision 1):** launch as an **early-access product**, with each module's status
managed in the admin area:

| Module (spec §5) | Status at launch | What its page says |
|---|---|---|
| Client Management | **Available** | Full page with real screenshots |
| SEO Management | In development | What it will do; "In development" badge; join early access |
| Website Analytics | In development | Same |
| Social Media Management | In development | Same |
| Content Marketing | In development | Same |
| Marketing Analytics | In development | Same |
| Reporting | In development | Same |

- Status badges ("Available" / "In development") appear on every card, menu item and page
  header, so nothing reads as shipped when it isn't.
- When a module ships, an admin switches its status. The page then gets real screenshots and
  the badge goes away, with no redesign needed (§20).
- The homepage leads with the vision but shows **only real screenshots**. The product demo
  (§4.3) shows the real dashboard, clients and activity. The SEO and traffic panels appear when
  those features exist.
- Integrations (§4.7) appear as an "Upcoming integrations" roadmap, with no third-party logos
  until each integration is built and its brand guidelines allow it.
- Pricing (§7) shows an **early-access** message with no prices until plans are configured and
  published in the admin area.

---

## 2. Scope

**In Phase 1.5**

- A separate, server-rendered marketing site covering every route in §3. Pages without real
  content are hidden, not published empty.
- Shared Outlogik brand: tokens, logo, Albert Sans, components.
- Conversion: Get Started and Log In links into the app; contact, demo request, early access
  and newsletter forms; lead storage, notifications, UTM and source attribution.
- An admin area inside the app, for platform staff only:
  - leads inbox
  - CMS (articles, guides, glossary, simple pages, SEO metadata, redirects)
  - media library
  - site settings (nav, footer, contacts, social links, CTAs, SEO defaults)
  - module statuses
  - pricing configuration
- SEO: server rendering and prerendering, metadata, canonical URLs, Open Graph, JSON-LD,
  breadcrumbs, sitemap, robots, redirects, `noindex` on staging.
- Analytics: privacy-friendly first-party conversion tracking, a consent banner, and optional
  GA4 / GTM / Clarity loaded only after consent (decision 9).
- Legal pages, drafted from Outlogik's actual data practices (decision 12).
- QA: Lighthouse 90+ targets, WCAG 2.2 AA review, cross-browser testing, security review,
  staging deployment guide.

**Not in Phase 1.5**

- The product features themselves (SEO, analytics, social…): Phase 2 and later.
- Billing, payment collection, trials enforced by plan limits. The pricing *configuration* is
  built; enforcing plan limits in the app comes with billing.
- Sending newsletter campaigns. Subscribers are collected with consent and can be exported.
- Third-party logos and testimonials (none exist yet).

---

## 3. Architecture

```
                        ┌───────────────────────────────┐
 visitors ──https──▶    │  outlogik.com  (marketing)    │  Angular 22 SSR + prerender (Node)
                        │  /, /platform/…, /pricing,    │  proxies /api/public/* ─────┐
                        │  /resources/…, forms          │                              │
                        └───────────────────────────────┘                              ▼
 customers ──https──▶   ┌───────────────────────────────┐    ┌──────────────────────────────┐
                        │  app.outlogik.com  (app)      │───▶│  FastAPI  /api/v1/…          │
                        │  existing Angular SPA         │    │  + /api/v1/public/… (new)    │
                        │  + /admin (platform staff)    │    │  + /api/v1/admin/… (new)     │
                        └───────────────────────────────┘    └──────────────┬───────────────┘
                                                                            ▼
                                                              PostgreSQL · Redis · media storage
```

- **A separate marketing app** (`marketing/` in this repo), Angular 22 with `@angular/ssr`,
  deployable on its own (§15).
  - Static pages (home, platform, solutions, pricing, about, legal) are **prerendered at build
    time** to plain HTML: the fastest option and best for SEO.
  - CMS content (blog, guides, glossary, simple pages) is **server-rendered on request** and
    cached for a short time, so publishing doesn't need a rebuild.
  - Minimal JavaScript: pages work without it. Interactive parts (navigation drawer, forms,
    consent) hydrate only when needed.
- **One API, three surfaces:**
  - `/api/v1/…` stays as it is for the app.
  - `/api/v1/public/…` (new) serves published content, settings and form submissions. It needs
    no login and is rate-limited.
  - `/api/v1/admin/…` (new) is for platform staff.
- **Forms stay on the website's own domain.** The marketing server forwards `/api/public/*` to
  FastAPI, so there's no cross-site setup and no third-party form service.
- **Shared brand:** a top-level `brand/` folder (tokens, fonts, logo SVGs) used by both
  Angular apps, so they can't drift apart.
- **Domains are configurable** through environment variables: `SITE_URL`, `APP_URL`,
  `API_URL`, plus staging equivalents (§11).

---

## 4. Pages and navigation

**Header** (sticky): Logo · Platform ▾ · Solutions ▾ · Resources ▾ · Pricing · Company ▾ ·
**Log In** · **Get Started**. Platform and Solutions use a two-column mega-menu with module
status badges. On mobile there's an accessible slide-out drawer with focus trap, Escape to
close and grouped sections.

| Route | Content | Rendering |
|---|---|---|
| `/` | Homepage, the 11 sections of §4 (adapted per section 1) | Prerender |
| `/platform` | Overview of all modules with status | Prerender |
| `/platform/{7 modules}` | The §5 structure: hero, explanation, capabilities, screenshots (real only), benefits, workflows, related, CTA | Prerender |
| `/solutions` + `/solutions/{5 audiences}` | Audience-specific copy (§6); each shows the features relevant *today* and what's coming | Prerender |
| `/pricing` | Early access, or published plans with comparison table, plus FAQ | Prerender, rebuilt on change |
| `/resources` | Hub: latest guides, glossary, blog. Sections with no published content are hidden. | SSR |
| `/resources/blog`, `/…/blog/{slug}`, `/…/blog/category/{slug}`, `/…/blog/tag/{slug}` | Article list, article (reading time, author, related, share links), categories, tags, search | SSR |
| `/resources/guides`, `/…/guides/{slug}` | Long-form guides with a table of contents | SSR |
| `/resources/seo-glossary`, `/…/seo-glossary/{term}` | A–Z index; one page per term | SSR |
| `/about` | What Outlogik is, the problem, philosophy, direction (no invented history or numbers) | Prerender |
| `/contact` | Contact form (category, name, email, company, message) | Prerender |
| `/book-a-demo` | Demo request form | Prerender |
| `/get-started` | Early-access explainer with "Create your account" (to the app's `/register`) and "Book a demo" | Prerender |
| `/login` | Redirects (302) to the app's `/login` | Server |
| `/privacy-policy`, `/terms-of-service`, `/cookie-policy` | Legal (CMS-editable) | SSR |
| `/sitemap.xml`, `/robots.txt` | Generated | Server |

**Footer:** logo, short description, Platform / Solutions / Resources / Company columns,
contact details, legal links, "Cookie settings", social links (only if configured),
copyright.

**Every CTA has a real destination:**

| CTA | Goes to |
|---|---|
| Get Started | App `/register?ref=…`, with UTM parameters carried through |
| Log In | App `/login` |
| Book a Demo | `/book-a-demo` |
| Explore the Platform | `/platform` |
| Join early access | Early-access form |

---

## 5. Design system

- **Palette:** the spec's palette (§2), adopted across the website *and* the app (decision 3).

  | Spec colour | Value | Used for |
  |---|---|---|
  | Black | `#000000` | Logo, primary buttons |
  | Dark charcoal | `#171717` | Body text |
  | Dark grey | `#333333` | Secondary text |
  | Medium grey | `#737373` | Muted text (4.7:1 on white, passes AA) |
  | Light grey | `#E5E5E5` | Borders |
  | Off-white | `#FAFAFA` | Alternate section backgrounds |

  Colour is used only for status: Available and In development badges, form errors.
- **Typography:** Albert Sans 400/500/600, self-hosted. A modular type scale with display
  sizes for heroes, kept within readable limits (§2: "avoid oversized typography"). The text
  column stays around 68 characters wide.
- **Visual language:**
  - an editorial 12-column grid, generous whitespace, 1px borders, restrained shadows and
    small corner radii (4–8px)
  - black "feature bands" for contrast
  - product screenshots in a minimal browser frame
  - small, functional animations that respect reduced motion
- **Components** (shared where they make sense):
  - header, mega-menu, mobile drawer, footer
  - hero, section heading, feature card, feature split (text plus screenshot), screenshot
    frame
  - status badge, CTA band, pricing card, comparison table, FAQ (native `<details>`)
  - forms with inline validation, breadcrumbs
  - article layout with table of contents, glossary A–Z index, consent banner
- **Screenshots** come from the *real* app with fictional example data, captured by a
  committed script, so they stay authentic and can be refreshed as features ship. They're
  captioned "Example data".

---

## 6. Backend integrations (FastAPI)

New modules, following the Phase 1 conventions (audit logging, rate limits, tests):

| Module | Tables | Endpoints |
|---|---|---|
| `site` | `site_settings` (nav, footer, contacts, social links, CTAs, SEO defaults), `modules` (status per product module), `redirects` | public: settings, modules · admin: CRUD |
| `leads` | `leads` (type: contact / demo / early access / newsletter; fields; status; notes; source, UTM, referrer, landing page; consent records), `lead_notes` | public: submit · admin: list, filter, status, notes, CSV export |
| `content` | `content_items` (article / guide / glossary term / page; Markdown body; status; scheduled publish time; SEO fields), `categories`, `tags`, `authors`, `revisions` | public: published content, search · admin: CRUD, preview, schedule |
| `media` | `media_assets` (original plus resized WebP variants, alt text, dimensions) | admin: upload, list, edit, delete · public: served files |
| `pricing` | `plans`, `plan_limits`, `plan_features` (monthly and annual price, trial days, limits, entitlements, published flag) | public: published plans · admin: CRUD |
| `events` | `conversion_events` (CTA clicks, form submits, sign-up clicks; no personal data) | public: record · admin: summary |

Key rules:

- **Admin access:** a new *platform role* on users: `content_editor` (CMS and media) or
  `site_admin` (everything, including leads and pricing). It's granted by the CLI or by a
  Super Admin. It's separate from organization roles; agencies never see the admin area.
- **Public endpoints** carry no session cookie, so CSRF doesn't apply. They're protected by:
  - an `Origin` check against `SITE_URL`
  - a honeypot field and a minimum time to fill the form
  - per-IP and per-email rate limits
  - strict validation
- **Newsletter (CASL):** an unticked consent box, double opt-in by email, an unsubscribe link,
  and a stored consent record with the date and wording shown.
- **Uploads:**
  - JPEG, PNG and WebP only (no SVG); 10 MB maximum
  - checked by content rather than file name, re-encoded, metadata (EXIF) stripped
  - resized variants at 480, 960 and 1600px
  - stored in a local folder in development, S3-compatible storage in production (configurable)
- **Markdown is sanitised** server-side to a safe list of HTML tags before it's served.
- **Lead emails:** a notification to a configurable sales address, and a confirmation to the
  person who submitted.

---

## 7. Technical plan details

- **SEO:**
  - per-page title, description and canonical URL (overridable in the CMS)
  - Open Graph and Twitter cards with a generated default share image
  - JSON-LD: `Organization` and `WebSite` site-wide; `SoftwareApplication` on platform pages;
    `Article` on posts and guides; `BreadcrumbList` everywhere
  - `FAQPage` is left out: in 2023 Google limited FAQ rich results to authoritative
    government and health sites, so it isn't justified here (§13). This gets re-checked
    against Google's current guidelines in step 11.
  - sitemap built from prerendered routes plus published content
  - `robots.txt`; staging always sends `noindex`
  - redirects managed in the CMS and served as 301s by the marketing server
- **Analytics** (decision 9):
  - first-party, cookieless conversion events and UTM attribution, stored with leads
  - optional GA4, GTM or Clarity IDs set in admin, off by default
  - loaded only after "Accept analytics" in the consent banner, with Accept, Reject and
    Customise given equal weight
  - consent stored in a first-party cookie, and "Cookie settings" in the footer reopens it
- **Performance:**
  - prerendered HTML and self-hosted, subset fonts with `font-display: swap`
  - images as responsive `srcset` WebP with explicit sizes (no layout shift) and lazy loading
    below the fold
  - per-route JavaScript budgets; caching and compression handled by the web server
- **Accessibility:** semantic landmarks, one `h1` per page, skip link, visible focus, labelled
  forms with announced errors, sufficient contrast, reduced motion. Checked with axe in CI and
  by hand with a keyboard.
- **Testing:**
  - backend unit and integration tests (public, admin and isolation)
  - frontend unit tests
  - Playwright end-to-end tests for every form and every CTA destination, in Chromium,
    Firefox and WebKit, at phone, tablet and desktop widths
  - Lighthouse CI on key pages
- **Deployment** (no Docker in production, per §15):
  - nginx in front of two services: the marketing SSR server (Node) and FastAPI (uvicorn)
  - the app as static files
  - systemd units and a written runbook for staging and production
  - the existing Docker Compose stays a local-development convenience only (approved in
    Phase 1, decision 2)

---

## 8. Build order (small, runnable steps)

| # | Step | Spec phase |
|---|---|---|
| 1 | Shared `brand/` folder; palette update in the app; `marketing/` Angular SSR app; header, mega-menu, drawer, footer; CI job | B |
| 2 | Backend: platform roles, `site` settings, module statuses, public API surface (origin check, rate limits) | A–B |
| 3 | Homepage; `/platform` overview; Client Management page; the other six module pages with status | C |
| 4 | Solutions (hub and 5 audiences); About | C |
| 5 | Pricing configuration (backend) and pricing page (early-access mode, comparison table, FAQ) | C |
| 6 | Leads backend; contact, demo, early-access and newsletter forms; `/get-started`; `/login`; notifications; UTM and source attribution | D |
| 7 | Admin area in the app: leads inbox (status, notes, CSV export), site settings, module statuses, pricing | D, E |
| 8 | CMS backend: content items, categories, tags, authors, revisions, scheduling, redirects; media library with image variants | E |
| 9 | CMS admin UI: Markdown editor with live preview, media picker, SEO fields, scheduling, publish and unpublish | E |
| 10 | Resources on the site: blog (list, article, category, tag, search, related, share), guides, glossary; hidden while empty | E |
| 11 | SEO: metadata, canonical URLs, Open Graph images, JSON-LD, breadcrumbs, sitemap, robots, redirects, staging `noindex` | F |
| 12 | Analytics and consent; legal pages | F |
| 13 | Content pass: final copy, screenshot script, glossary terms and guides (drafts for your review) | C, E |
| 14 | QA and release: Lighthouse, accessibility, cross-browser, security review, staging guide (and deployment, if hosting is ready), acceptance checklist (§22) | G |

Each step ends with tests passing, a browser check, a commit and a push. Steps 1–7 plus 11–12
make a **launchable site** (milestone A); steps 8–10 add the CMS and resources (milestone B).
See decision 16.

---

## 9. Decisions needed

Each has a recommendation; reply with any you'd change.

1. **Unbuilt modules:** publish their pages labelled "In development", with status managed
   in admin (recommended), or hide them until they're built.
2. **Sign-up at launch:** keep open sign-up, presented as *"Free during early access"*
   (recommended), or switch to invite-only with an early-access waitlist.
3. **Palette:** adopt the spec's values everywhere, including the app, with the logo in pure
   `#000` / `#FFF` (recommended), or keep the current sampled colours.
4. **Website theme:** light, with black feature bands (recommended; one design to perfect),
   or light and dark following the visitor's system setting, like the app.
5. **Architecture:** a separate Angular 22 SSR marketing app in this repo, with Node SSR in
   production (recommended).
6. **Admin location:** inside the existing app at `/admin`, for new platform roles
   (recommended), rather than a separate admin app.
7. **Editing format:** Markdown with live preview (recommended: simple, safe, portable), or a
   rich-text block editor.
8. **Page editing scope:** core marketing pages are designed in code; the CMS edits articles,
   guides, glossary, legal and simple pages, plus SEO metadata, navigation, footer, CTAs and
   pricing everywhere (recommended). A fully CMS-built page builder is much bigger.
9. **Analytics:** first-party cookieless conversion tracking by default; GA4, GTM and Clarity
   optional, off by default, and only after consent (recommended). This is the one allowed
   exception to the no-third-party-scripts rule, and only after the visitor consents.
10. **Spam protection:** honeypot, timing and rate limits, with no third-party CAPTCHA
    (recommended, for privacy). A CAPTCHA can be added later if spam gets through.
11. **Copy:** I write all page copy and draft about 30 glossary terms and 3 guides, all
    honest and feature-specific. You review before anything is published. The blog stays
    hidden until its first post. Tagline: the spec's *"Digital Marketing. Smarter. Together."*
12. **Legal pages:** I draft privacy, terms and cookie policies from what Outlogik actually
    collects, considering PIPEDA and CASL. **I need:** the legal business name, address,
    province, and contact emails for sales and privacy. A lawyer should review before launch.
13. **Domains and hosting:** I need the domain (e.g. `outlogik.com`), and a decision on
    staging hosting: a Linux VPS with nginx and systemd (recommended, no Docker) or a
    platform service. Until then I'll build and test locally and write the deployment guide.
14. **Newsletter:** collect subscribers with CASL-compliant double opt-in and allow export
    (recommended). Sending campaigns is out of scope.
15. **Lead notifications:** which email address(es) should new leads go to?
16. **Delivery:** two milestones, each merged when done (recommended). Milestone A is a
    launchable site with forms, leads and admin (steps 1–7, 11, 12, 14 partly). Milestone B
    adds the CMS, resources and content (steps 8–10, 13, 14). The alternative is one large
    merge at the end.
