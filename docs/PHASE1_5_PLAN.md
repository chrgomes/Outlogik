# Outlogik — Phase 1.5 Plan (Public website) — revision 2: agency direction

Status: **Revision 2 approved 2026-11-15, with every recommendation in section 6 (A–F).**
Revision 1 (Outlogik as a software product sold to agencies) was approved and steps 1–2 were
built under it; it's in git history if needed.
Source: [`specs/MARKETING_WEBSITE_SPEC.md`](specs/MARKETING_WEBSITE_SPEC.md) (the spec), with the
deviations listed in section 1. Section numbers (§) refer to the spec.
Progress: [`IMPLEMENTATION_TRACKER_1_5.md`](IMPLEMENTATION_TRACKER_1_5.md).

---

## 1. The new direction, and how it differs from the spec

**Outlogik is a digital marketing agency.** The website sells Outlogik's services to
businesses. The Outlogik app is how the agency delivers and reports its work: each client gets
a **client portal** (already built in Phase 1).

Decided 2026-11-15:

| Topic | Decision |
|---|---|
| Services offered | **SEO**, **Social Media Management**, **Website Analytics & Reporting**, **Content Marketing** |
| Pricing | **No public prices.** Every service leads to a free consultation or proposal |
| Main action | **Book a free consultation** |
| App sign-up | **Invite-only.** Outlogik creates client portals and invites clients; "Log in" is for existing clients and staff |

Deviations from the spec (it was written for a software product):

| Spec | Revision 2 |
|---|---|
| §1 positioning: software platform for agencies | A digital marketing agency for businesses, with a client portal as its differentiator |
| §3 nav: Platform, Solutions, Resources, Pricing, Company | **Services, Who we help, How we work, Resources, Pricing, Company** |
| §3 routes `/platform/*`, `/solutions/*`, `/book-a-demo`, `/get-started` | `/services/*`, `/who-we-help/*`, `/how-we-work`, `/book-a-consultation`; old paths redirect (section 4) |
| §4 homepage built around software modules | Built around services, process, the client portal, and a consultation (section 4) |
| §5 module pages | **Service pages** with the same structure: what we do, what's included, how we work, what you see in the portal, FAQ, call to action |
| §6 audience pages (agencies, freelancers…) | **Who we help:** business types (decision B) |
| §7 configurable subscription plans | A pricing page explaining how proposals and pricing work, with FAQ. No plan configuration (dropped from step 5) |
| §10 primary conversion: start a trial | Book a free consultation; secondary: contact, newsletter, resource downloads |
| §11 "Get Started" → app registration | "Book a free consultation" → `/book-a-consultation`. "Log in" → client portal |
| §4.7 integrations section | Shown as the **tools we work with** (GA4, Search Console and so on), not as product integrations, and only tools the team actually uses (decision D) |

**Honesty rules still apply** (§4.1, §19, §22.20), with one important difference: services
can be sold **today**, because the team delivers them even where the software doesn't automate
them yet. "In development" labels now apply only to **client-portal features**, such as online
reports and analytics dashboards. No invented case studies, client logos, results, team members
or statistics; those sections stay hidden until real ones exist.

---

## 2. What carries over from steps 1–2

- **Kept as-is:**
  - the brand, palette and logo; the Angular SSR marketing app with its header and footer
  - render-on-request with caching; the server-side forwarding route
  - staff roles, site settings, the public and admin APIs, CI, security headers
- **Adjusted in step 3:**
  - Header and footer menus switch to the new navigation.
  - The `product_modules` list becomes **client portal features**, with honest statuses, shown on *How we work*:
    - client portal, websites overview, activity history: **available**
    - monthly reports, analytics dashboards, social calendar approvals, SEO health: **in development**
  - Settings gain the consultation button label; the early-access flag is removed.
- **App change:** sign-up becomes **invite-only** (`SIGNUP_MODE=invite_only`). The app's register page and the "Create an account" links are replaced by "Ask your Outlogik contact for an invitation". The marketing site links only to **Log in**.

---

## 3. Scope

**In Phase 1.5**

- The agency website: home, four service pages, Who we help, How we work, Pricing, About,
  Contact, Book a consultation, legal pages. Resources (blog, guides, glossary) come in
  milestone B.
- Conversion:
  - consultation booking form (primary), contact form, newsletter sign-up
  - lead storage, notifications, UTM and source attribution, spam protection
- An admin area inside the app, for staff:
  - leads inbox (status, notes, export)
  - site settings
  - portal feature statuses
  - CMS and media library (milestone B)
- SEO: server rendering, metadata, canonical URLs, Open Graph, structured data, sitemap, robots, redirects. `ProfessionalService` / `LocalBusiness` schema can be added once the business details are provided (decision 12).
- Analytics with consent, legal pages, and QA, as in revision 1.

**Not in Phase 1.5**

- Booking calendar integrations (e.g. picking a time slot). The consultation form collects
  preferred times and the team replies. A self-hosted scheduler can come later.
- Client onboarding automation, proposals and contracts, billing.
- The client-portal features marked "in development" (those are Phase 2+).

---

## 4. Pages and navigation

**Header:** Logo · Services ▾ · Who we help ▾ · How we work · Resources ▾ (once content exists) ·
Pricing · Company ▾ · **Log in** (client portal) · **Book a free consultation**.

| Route | Content |
|---|---|
| `/` | Homepage (below) |
| `/services` | Overview of the four services |
| `/services/seo` | SEO: audits, technical fixes, keyword research, on-page optimisation, monthly reporting |
| `/services/social-media-management` | Social: strategy, content calendars, posting, community management, reporting |
| `/services/website-analytics-reporting` | GA4 and Search Console setup, tracking, monthly performance reports |
| `/services/content-marketing` | Content strategy, blog posts, website copy, keyword-to-content planning |
| `/who-we-help` + one page per business type | Messaging for each type of client (decision B) |
| `/how-we-work` | The process (consultation → proposal → onboarding → monthly work and reporting), the client portal with real screenshots, and portal features with status labels |
| `/pricing` | How pricing works: custom proposals, what affects price, what's included; FAQ; "Book a free consultation" |
| `/about` | Who Outlogik is, the approach and values (from your input; nothing invented) |
| `/contact` | Contact form, plus contact details once provided |
| `/book-a-consultation` | Consultation form: name, email, company, website, services of interest, budget range (optional), message, preferred contact time |
| `/login` | Redirects to the app's login |
| `/privacy-policy`, `/terms-of-service`, `/cookie-policy` | Legal (decision 12) |
| Redirects | `/platform*` → `/services`, `/solutions*` → `/who-we-help`, `/book-a-demo` and `/get-started` → `/book-a-consultation` |

**Homepage sections:**
1. **Hero:** what Outlogik does and for whom, "Book a free consultation", "See our services", and a real client-portal screenshot.
2. **Services:** four cards linking to the service pages.
3. **Why Outlogik:** one agency for SEO, social, content and analytics; one portal for everything; clear reporting. Honest claims only.
4. **How we work:** four steps from consultation to monthly reporting.
5. **Your client portal:** real screenshots of what clients see, with portal features labelled honestly.
6. **Who we help:** cards for each business type.
7. **Tools we work with:** text tiles (decision D).
8. **Pricing:** "Every business is different", with a proposal after a free consultation.
9. **Results and testimonials:** **hidden until real ones exist.**
10. **Final call to action:** book a consultation.
11. **Footer.**

---

## 5. Build order (revised)

| # | Step | Status |
|---|---|---|
| 1 | Brand, palette, marketing app shell, CI | ✅ Done (carries over) |
| 2 | Staff roles, site settings, statuses, public API | ✅ Done (carries over) |
| 3 | Agency navigation; invite-only sign-up in the app; portal features list; homepage | Next |
| 4 | Service pages (4) and `/services` | |
| 5 | Who we help, How we work, Pricing (how it works), About | |
| 6 | Leads: consultation, contact and newsletter forms; attribution; notifications; redirects for old paths | |
| 7 | Admin area: leads inbox, settings, portal feature statuses | |
| 8–10 | CMS, media library, resources (milestone B, unchanged) | |
| 11 | SEO (adds `ProfessionalService` schema once business details are known) | |
| 12 | Analytics and consent; legal pages | |
| 13 | Content pass (milestone B) | |
| 14 | QA and release | |

Milestone A = steps 1–7, 11, 12, plus the release checks in 14. Milestone B = 8–10, 13, plus the rest of 14.

---

## 6. Decisions (revision 2, approved with the recommendations)

Already decided: services, pricing approach, main action, invite-only sign-up (section 1).
Still on hold from revision 1: legal details (12), domain and hosting (13), lead emails (15).
All other revision-1 decisions still apply: palette, light theme, architecture, admin
location, Markdown editing, analytics with consent, spam protection, newsletter double
opt-in, two milestones.

New ones, each with a recommendation:

- **A. Service area.** Who can hire Outlogik: anywhere online, Canada-wide, or a specific city or region? This affects copy, local SEO and structured data. *Recommendation (approved): location-neutral copy until you tell me.*
- **B. Who we help.** Which business types to target? *Recommendation:* **Small businesses**, **Local and service businesses** (clinics, trades, professional services), **E-commerce**, **Growing companies** (in-house teams that need extra hands). Change or add any.
- **C. About page.** Founding story, team and values come from you; nothing is invented. *Recommendation: I draft a short, honest About page from what you tell me, marked for your review. Until then it focuses on the approach, not the history.*
- **D. Tools we work with.** List only tools the team really uses. *Recommendation: Google Analytics 4, Google Search Console, Google Business Profile, Bing Webmaster Tools, Meta Business Suite, LinkedIn. Confirm or edit.*
- **E. Budget question on the consultation form.** *Recommendation: an optional budget range field.* It helps qualify leads; leave it out if you'd rather not ask.
- **F. Copy.** *Recommendation: I write all copy in a clear, confident agency voice, with no guarantees of rankings or results (§19), for your review before launch.*
