# Implementation tracker — Phase 1.5 (public marketing website)

Plan: [`PHASE1_5_PLAN.md`](PHASE1_5_PLAN.md). Spec: [`specs/MARKETING_WEBSITE_SPEC.md`](specs/MARKETING_WEBSITE_SPEC.md).

**Milestone A** (launchable site) = steps 1–7, 11, 12, and the release checks in 14.
**Milestone B** (CMS and resources) = steps 8–10, 13, and the rest of 14.

| # | Step | Milestone | Status | Notes |
|---|---|---|---|---|
| 1 | Shared brand, palette in the app, marketing SSR app, header / menus / drawer / footer, CI | A | ✅ Done | See below |
| 2 | Platform roles, site settings, module statuses, public API surface | A | ⏳ Next | |
| 3 | Homepage, platform overview, module pages | A | ☐ | |
| 4 | Solutions pages, About | A | ☐ | |
| 5 | Pricing configuration and page | A | ☐ | |
| 6 | Leads: forms, attribution, notifications; `/get-started`, `/login` | A | ☐ | |
| 7 | Admin area: leads inbox, settings, module statuses, pricing | A | ☐ | |
| 8 | CMS backend and media library | B | ☐ | |
| 9 | CMS admin UI | B | ☐ | |
| 10 | Resources on the site: blog, guides, glossary | B | ☐ | |
| 11 | SEO: metadata, structured data, sitemap, robots, redirects | A | ☐ | |
| 12 | Analytics and consent; legal pages | A | ☐ | Legal pages wait for decision 12 |
| 13 | Content pass: copy, screenshots, glossary and guides | B | ☐ | |
| 14 | QA and release: Lighthouse, accessibility, cross-browser, security, staging guide | A + B | ☐ | Staging deployment waits for decision 13 |

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
