# OUTLOGIK — PUBLIC MARKETING WEBSITE

Master Website Architecture, Design & Development Specification

> Supplied by the product owner on 2026-11-15 as the specification for Phase 1.5.
> Kept verbatim (formatting converted to Markdown). The implementation plan is
> [`../PHASE1_5_PLAN.md`](../PHASE1_5_PLAN.md).

- **Project:** Outlogik Marketing Website
- **Website Type:** SaaS Marketing & Customer Acquisition Website
- **Target Audience:** Digital Marketing Agencies, SEO Agencies, Freelancers, Consultants, Marketing Teams and Businesses
- **Brand Identity:** Minimalist, Monochromatic, Professional
- **Primary Objective:** Generate qualified leads, demonstrate product value and convert visitors into Outlogik customers.

---

## 1. PROJECT OVERVIEW

Design and develop a premium, modern, conversion-focused public marketing website for Outlogik.

Outlogik is an all-in-one digital marketing intelligence and agency management platform designed to bring SEO, website analytics, social media management, content marketing, marketing performance and client management together in one centralized workspace.

The public website must communicate Outlogik's value proposition clearly and professionally.

The website should position Outlogik as a serious SaaS product competing in the digital marketing software and agency management space.

The website must be:

- Professional and visually impressive.
- Modern and responsive.
- SEO-friendly.
- Conversion-focused.
- Fast-loading.
- Accessible.
- Easy to maintain.
- Scalable as the product grows.
- Consistent with the Outlogik brand identity.

This is a marketing and sales website, not the application dashboard itself.

Do not mix the public marketing experience with authenticated application functionality.

## 2. BRAND IDENTITY AND DESIGN SYSTEM

### Official brand

Name: Outlogik

Suggested tagline:

> Digital Marketing. Smarter. Together.

Brand positioning:

> One intelligent platform to manage, measure and grow digital marketing performance.

### Logo

Use the supplied Outlogik logo references.

The logo consists of a minimalist circular symbol and a clean Outlogik wordmark.

Maintain the established monochromatic direction.

### Brand colours

Primary:

- Black: #000000
- White: #FFFFFF

Supporting:

- Dark charcoal: #171717
- Dark grey: #333333
- Medium grey: #737373
- Light grey: #E5E5E5
- Off-white: #FAFAFA

Do not introduce coloured brand accents during the initial implementation.

Use neutral colours for backgrounds, cards, borders, typography and interface elements.

Status indicators may use conventional accessible colours where necessary, without changing the brand identity.

### Typography

Use a modern, highly readable sans-serif typeface.

Typography should have:

- Strong headline hierarchy.
- Clear body copy.
- Comfortable line spacing.
- Consistent font weights.
- Professional navigation labels.

Avoid oversized typography that compromises usability.

### Design direction

The visual language should communicate:

- Intelligence.
- Simplicity.
- Efficiency.
- Professionalism.
- Reliability.
- Technical capability.

Use:

- Generous whitespace.
- Clean grid systems.
- Strong editorial layouts.
- Subtle borders.
- Restrained shadows.
- Carefully selected product imagery.
- Elegant interface mockups.
- Minimal animations.
- Clear calls to action.

Avoid:

- Generic website templates.
- Excessive gradients.
- Bright multicolour backgrounds.
- Unnecessary decorative animations.
- Stock photography that does not communicate the product.
- Excessively rounded components.
- Cluttered layouts.

The result should feel like a premium technology company.

## 3. WEBSITE ARCHITECTURE

Build the public website with the following main navigation.

### Primary navigation

1. Home
2. Platform
3. Solutions
4. Resources
5. Pricing
6. Company

Right-side actions:

- Log In
- Get Started

Use a sticky navigation bar with a clean dropdown or mega-menu where appropriate.

On mobile, provide an accessible navigation drawer.

### Main website pages

Create the following routes:

- /
- /platform
- /platform/seo-management
- /platform/website-analytics
- /platform/social-media-management
- /platform/content-marketing
- /platform/marketing-analytics
- /platform/client-management
- /platform/reporting
- /solutions
- /solutions/marketing-agencies
- /solutions/seo-agencies
- /solutions/freelancers
- /solutions/in-house-marketing-teams
- /solutions/small-businesses
- /pricing
- /resources
- /resources/blog
- /resources/guides
- /resources/seo-glossary
- /about
- /contact
- /book-a-demo
- /get-started
- /login
- /privacy-policy
- /terms-of-service
- /cookie-policy

Additional routes may be introduced as the product develops.

Do not publish empty pages or placeholder content.

## 4. HOMEPAGE — PRIMARY CONVERSION PAGE

The homepage must immediately communicate what Outlogik is, who it serves and why someone should use it.

### Section 1 — Hero

Create a premium hero section.

Suggested headline:

> Everything You Need to Manage Digital Marketing. One Platform.

Supporting description:

> Bring SEO, social media, website analytics and client management together with Outlogik. Simplify your marketing operations, understand performance and manage your clients from one centralized workspace.

Primary CTA: Get Started

Secondary CTA: Explore the Platform

Include a professionally designed visual representation of the actual Outlogik application.

Use authentic application screenshots or carefully constructed product mockups based on real implemented functionality.

Do not represent unfinished functionality as an existing product capability.

### Section 2 — Platform overview

Headline:

> Your Digital Marketing Operations. Connected.

Introduce the major platform capabilities using a professional grid.

Feature categories:

- SEO Management
- Website Analytics
- Social Media Management
- Content Marketing
- Marketing Analytics
- Client Management
- Performance Monitoring
- Reporting and Insights

Each feature card should include:

- Icon.
- Feature name.
- Short description.
- Learn More link.

### Section 3 — Product demonstration

Headline:

> See Your Entire Marketing Operation in One Place.

Show a large dashboard preview.

Demonstrate:

- Client overview.
- SEO performance.
- Organic traffic.
- Search visibility.
- Social media performance.
- Website health.
- Recent activity.

Use authentic interface screenshots wherever possible.

Include a link to explore the platform.

### Section 4 — The problem Outlogik solves

Explain the challenges of managing marketing through disconnected tools.

Examples:

- Too many subscriptions.
- Scattered analytics.
- Disconnected client information.
- Time-consuming reporting.
- Manual SEO monitoring.
- Difficult content coordination.
- Limited visibility across marketing channels.

Position Outlogik as a centralized workspace that helps address these problems.

Avoid unsupported claims about eliminating every external tool.

### Section 5 — Feature highlights

Create dedicated visual sections highlighting the main platform capabilities.

Suggested sections:

**SEO Management** — Monitor website health, search visibility, keywords and technical SEO performance.

**Social Media Management** — Manage social accounts, content calendars, publishing and available social analytics.

**Website Analytics** — Connect Google Analytics and Search Console to understand website performance.

**Client Management** — Organize clients, projects, websites, tasks and marketing activity.

**Reporting** — Generate professional marketing reports that communicate results clearly.

**Marketing Intelligence** — Bring marketing data together to identify opportunities and understand performance.

Each section should include a relevant screenshot, a concise explanation and a CTA.

### Section 6 — Built for agencies and marketing professionals

Headline:

> Designed for the Way Modern Agencies Work.

Explain how Outlogik supports:

- Multiple clients.
- Multiple websites.
- Multiple team members.
- Centralized marketing operations.
- Client-specific dashboards.
- Reporting and collaboration.

### Section 7 — Integrations

Headline:

> Connect the Tools You Already Use.

Show supported integrations using official brand assets where permitted.

Potential integrations include:

- Google Analytics 4.
- Google Search Console.
- Bing Webmaster Tools.
- Meta.
- LinkedIn.
- TikTok.
- YouTube.
- Pinterest.
- Microsoft Clarity.

Only identify an integration as available when it has actually been implemented and verified.

For planned integrations, use an explicitly labelled roadmap or upcoming integrations section.

### Section 8 — Reporting and results

Show how Outlogik helps agencies present marketing performance to clients.

Include:

- SEO reporting.
- Website traffic.
- Search performance.
- Social media analytics.
- Website health.
- Custom reporting.

Use sample reports only when clearly labelled as demonstrations.

Never fabricate customer testimonials, business results or performance statistics.

### Section 9 — Pricing preview

Introduce available subscription plans.

Display the actual configured plans and pricing.

If pricing has not yet been established, use a transparent early-access or request-a-demo CTA rather than inventing prices.

### Section 10 — Final conversion section

Suggested headline:

> Take Control of Your Digital Marketing Operations.

Supporting text:

> Bring your marketing activities, analytics and client management together with Outlogik.

CTA: Get Started with Outlogik

Secondary CTA: Book a Demo

### Section 11 — Footer

Include:

- Outlogik logo.
- Short company description.
- Platform navigation.
- Solutions.
- Resources.
- Company information.
- Contact information.
- Privacy policy.
- Terms of service.
- Cookie policy.
- Social media links where available.
- Copyright information.

## 5. PLATFORM PRODUCT PAGES

Create individual landing pages for each major platform module.

Each page should follow a consistent structure:

1. Hero headline.
2. Product explanation.
3. Key capabilities.
4. Product screenshots.
5. Benefits.
6. Example workflows.
7. Related features.
8. CTA.

**SEO Management.** Explain: technical SEO auditing; keyword management; search performance; website crawling; SEO issue tracking; indexing analysis; SEO recommendations; audit history.

**Website Analytics.** Explain: GA4 integration; Search Console integration; organic traffic; search impressions; landing pages; conversion tracking; performance comparisons.

**Social Media Management.** Explain: social account management; content creation; publishing; scheduling; content calendar; analytics; client approvals.

**Content Marketing.** Explain: content planning; editorial calendars; content optimization; AI writing assistance where implemented; keyword-to-content mapping; content performance.

**Marketing Analytics.** Explain: centralized reporting; channel comparisons; campaign tracking; traffic analysis; conversion metrics; performance trends.

**Client Management.** Explain: client workspaces; multiple websites; team permissions; client portals; tasks; collaboration; marketing activity history.

**Reporting.** Explain: custom reports; PDF exports; CSV exports; client reporting; date comparisons; branded reporting where available.

## 6. SOLUTIONS PAGES

Create audience-specific landing pages.

**Marketing agencies.** Focus on: managing multiple clients; reducing disconnected workflows; centralized analytics; client reporting; team collaboration.

**SEO agencies.** Focus on: website auditing; search performance; keyword management; technical SEO; client SEO reporting.

**Freelancers and consultants.** Focus on: managing multiple projects; organizing client information; marketing performance; simplified reporting; professional client experiences.

**In-house marketing teams.** Focus on: cross-channel visibility; marketing collaboration; analytics; campaign tracking; content coordination.

**Small businesses.** Focus on: understanding website performance; managing marketing activities; monitoring SEO; organizing social media; understanding marketing results.

Each solution page must contain messaging appropriate to its audience rather than simply duplicating the homepage.

## 7. PRICING PAGE

Build a professional pricing page with configurable subscription plans.

Potential structure: Free / Trial; Starter; Professional; Agency; Enterprise.

Do not hardcode final prices.

The pricing system must support configurable: monthly billing; annual billing; trial duration; user limits; client limits; website limits; connected account limits; feature entitlements; data retention limits; reporting functionality.

Include a feature comparison table.

Provide clear explanations of what each plan includes.

Include an FAQ section.

If the product is in beta, provide an early-access CTA.

Do not collect payment details until the payment gateway and subscription model have been configured.

## 8. RESOURCES AND CONTENT MARKETING

Create a resource centre to support organic search traffic and establish Outlogik as a knowledgeable digital marketing brand.

### Blog

Support: blog categories; author profiles; publication dates; featured articles; related articles; search; tags; reading time; social sharing.

Suggested content categories: SEO; Digital Marketing; Social Media; Analytics; Content Marketing; Agency Management; Marketing Automation.

### Guides

Create long-form educational resources. Examples: SEO fundamentals; technical SEO checklist; Google Analytics guide; Search Console guide; digital marketing agency workflow guide; social media management guide.

### SEO glossary

Create an indexed glossary of digital marketing terminology. Examples: backlinks; canonical tags; click-through rate; conversion rate; domain authority; engagement rate; impressions; indexing; organic traffic; search intent.

### Resource management

Build an administrative content management area to: create articles; edit articles; schedule publication; upload images; manage categories; manage authors; configure SEO metadata; preview pages; publish and unpublish content.

## 9. ABOUT AND COMPANY PAGES

Create a professional company page explaining: what Outlogik is; the problem it addresses; its platform philosophy; its commitment to simplifying digital marketing; its product direction.

Avoid inventing company history, team members, awards or customer numbers.

Include a contact page with: contact form; business inquiry category; name; email; company; message.

Add appropriate spam protection and input validation.

## 10. CONVERSION AND LEAD GENERATION

The marketing website must have a clear conversion strategy.

Primary conversion: start a trial or create an account.

Secondary conversions: request a demo; join the beta; contact sales; subscribe to marketing updates; download resources.

Implement: clear CTA placement; conversion-focused landing pages; lead capture forms; demo request forms; form validation; spam prevention; confirmation messages; lead source tracking; UTM attribution.

Forms should be connected to a configurable backend endpoint.

Store leads securely and provide an administrative interface for reviewing and managing submissions.

Do not create non-functional buttons or forms.

## 11. USER AUTHENTICATION AND APPLICATION CONNECTION

The public marketing website must connect cleanly to the actual Outlogik application.

Use a clear domain structure:

- Public website: primary domain.
- Application: app subdomain.
- Staging application: separate staging subdomain.

The actual domain values must be configurable.

Navigation actions:

- **Get Started** — direct users to the registration workflow in the application.
- **Log In** — direct users to the application login page.
- **Book a Demo** — direct users to the demo request workflow.
- **Explore Platform** — navigate to the relevant marketing pages.

The public website should not expose private application routes or internal administrative functionality.

## 12. ADMINISTRATIVE CONTENT MANAGEMENT

Build a secure CMS or administrative content management interface.

Administrators should be able to manage:

- **Website pages:** create pages; edit content; publish and unpublish; configure metadata; configure page slugs; preview pages.
- **Blog:** create and edit posts; schedule publication; manage categories; manage authors; upload media; configure SEO information.
- **Leads:** view inquiries; view demo requests; track lead status; add internal notes; export authorized lead records.
- **Website configuration:** navigation; footer; social links; contact details; pricing configuration; CTA settings; SEO defaults.
- **Media library:** upload images; organize assets; manage image metadata; generate optimized image variants; reuse media across pages.

Restrict CMS access to authorized administrators.

## 13. SEARCH ENGINE OPTIMIZATION

SEO must be incorporated into the marketing website from the beginning.

Implement: server-side rendering or static pre-rendering where appropriate; search-engine-friendly URLs; custom page titles; meta descriptions; canonical URLs; XML sitemap; robots.txt; Open Graph metadata; social sharing metadata; structured data; breadcrumbs; internal linking; image alt attributes; optimized image formats; proper heading hierarchy; indexation controls; redirect management.

Implement appropriate schema types where justified: Organization; SoftwareApplication; WebSite; Article; BreadcrumbList; FAQPage only when the page genuinely qualifies under current search engine guidelines.

Avoid keyword stuffing and duplicate landing-page content.

Build the website so every public page can be independently indexed.

## 14. ANALYTICS AND CONVERSION TRACKING

Integrate configurable marketing analytics.

Potential services: Google Analytics 4; Google Tag Manager; Microsoft Clarity.

Track: page views; CTA clicks; registration clicks; demo requests; form submissions; pricing interactions; resource downloads; conversion sources.

Support UTM tracking.

Implement privacy-conscious analytics consent controls and applicable privacy requirements.

Do not load non-essential tracking technologies before consent where consent is required.

## 15. TECHNICAL ARCHITECTURE

Prefer the existing Outlogik technology stack where practical.

Preferred technologies:

- Frontend: Angular; TypeScript; Bootstrap 5; HTML5; SCSS.
- Backend: Python; FastAPI; SQLAlchemy.
- Database: PostgreSQL.

Additional requirements: reusable components; responsive layouts; centralized API service; content management integration; form validation; image optimization; secure authentication for administration; environment-based configuration.

For public SEO pages, prioritize server-side rendering or static pre-rendering.

If the existing Angular application is not suitable for efficient public-page rendering, evaluate a separate marketing frontend rather than compromising SEO performance.

Keep the marketing website independently deployable from the application.

Do not introduce Docker unless specifically approved.

## 16. PERFORMANCE AND ACCESSIBILITY

Performance targets should include: fast initial page rendering; optimized images; lazy loading below-the-fold media; minimal JavaScript; efficient font loading; caching; compression; avoidance of layout shifts.

Use Core Web Vitals as performance indicators.

Target strong Lighthouse results, aiming for 90+ where practical in Performance, Accessibility, Best Practices and SEO.

Implement: keyboard navigation; visible focus states; accessible form labels; appropriate colour contrast; semantic HTML; screen-reader-friendly components; reduced-motion support.

Aim for WCAG 2.2 AA accessibility.

## 17. SECURITY AND PRIVACY

Implement: HTTPS; secure administrative authentication; protected CMS routes; server-side input validation; CSRF protection where applicable; secure session management; rate limiting; spam protection; secure file uploads; database access controls; environment-based secrets; audit logging for sensitive administrative actions.

Create: privacy policy; terms of service; cookie policy.

Ensure the policies accurately reflect actual data collection and product functionality.

Consider applicable Canadian privacy requirements, including PIPEDA where relevant, and applicable anti-spam requirements.

## 18. RESPONSIVE DESIGN

The marketing website must work across desktop computers, laptops, tablets and mobile phones.

Prioritize mobile usability.

Ensure: navigation functions correctly; hero content is readable; CTAs remain accessible; pricing tables adapt to smaller screens; product screenshots scale correctly; forms are easy to complete; no horizontal overflow occurs.

## 19. CONTENT AND COPYWRITING REQUIREMENTS

Write professional, clear and persuasive website content.

The messaging should emphasize outcomes rather than just lists of features.

Core messaging themes: centralized digital marketing management; better client visibility; simplified agency workflows; SEO and website performance; connected marketing analytics; efficient client management; professional reporting.

Use concise headlines and strong calls to action.

Avoid: generic marketing jargon; unsupported claims; fake testimonials; fake customer logos; invented usage statistics; guaranteed SEO ranking promises; unverified integration claims.

Use honest, feature-specific descriptions.

## 20. FUTURE EXPANSION

Architect the marketing website so new product capabilities can be introduced without restructuring the entire site.

Future marketing pages may cover: Competitor Intelligence; Local SEO; Reputation Management; Marketing Attribution; AI Marketing Intelligence; Website Monitoring; White-Label Reporting; Marketing Automation; Agency Business Management.

These pages should only be published as available product capabilities when the corresponding functionality has been implemented.

## 21. DEVELOPMENT PHASES

- **Phase A — Discovery and architecture:** inspect existing Outlogik codebase; review existing application branding; identify current domain and deployment configuration; establish public website architecture; define navigation and page hierarchy.
- **Phase B — Brand and design system:** implement logo; establish typography; define monochromatic palette; build reusable components; develop responsive navigation; create design tokens.
- **Phase C — Core marketing website:** homepage; platform pages; solutions pages; pricing page; about page; contact page; footer.
- **Phase D — Conversion functionality:** registration integration; login integration; demo forms; lead management; CTA tracking; UTM attribution.
- **Phase E — Resources and CMS:** blog; guides; glossary; CMS; media library; SEO metadata management.
- **Phase F — SEO and optimization:** SSR or static rendering; structured data; XML sitemap; robots.txt; performance optimization; accessibility testing.
- **Phase G — Testing and deployment:** responsive testing; browser testing; form testing; security review; SEO validation; performance review; staging deployment; production readiness.

## 22. FINAL ACCEPTANCE CRITERIA

The marketing website is ready for release when:

1. The Outlogik brand is consistently implemented.
2. All primary pages are complete.
3. Navigation works across desktop and mobile.
4. Product pages explain real functionality.
5. CTAs navigate to the correct destinations.
6. Registration and login connections work.
7. Demo and contact forms work.
8. Leads are securely stored and manageable.
9. CMS functionality works.
10. Blog and resource pages are publishable.
11. Public pages have appropriate SEO metadata.
12. XML sitemap and robots.txt are configured.
13. Structured data is validated.
14. Analytics and consent controls work.
15. The website is responsive.
16. Accessibility has been reviewed.
17. Performance has been optimized.
18. Security checks pass.
19. Staging deployment is documented.
20. No unfinished functionality is falsely advertised.

## 23. FINAL DEVELOPMENT INSTRUCTIONS

Act as a senior SaaS product designer, frontend architect, backend developer, SEO specialist, conversion optimization specialist and application security engineer.

The goal is to create a polished public marketing website that makes Outlogik look like a credible, established SaaS product.

The design must feel intentional, premium, clean and technically sophisticated.

Prioritize clarity, performance, credibility and conversions.

Do not simply generate a collection of generic landing pages.

Create a cohesive website with consistent visual language, purposeful navigation, strong content hierarchy and a clear customer acquisition strategy.

Before development, inspect the existing Outlogik application and identify how the marketing website should integrate with its authentication, registration, domain structure and backend.

Preserve existing application functionality.

Build the public marketing website independently while maintaining consistent Outlogik branding.

Begin by presenting:

1. Proposed website architecture.
2. Page and navigation structure.
3. Design system.
4. Technical implementation plan.
5. Required backend integrations.
6. Development phases.

Then proceed with implementation in manageable stages.

The final result should make a prospective agency customer understand what Outlogik does, why it is valuable, how it works and how to become a customer.
