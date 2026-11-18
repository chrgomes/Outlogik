# OUTLOGIK — Master Platform Evolution & Hybrid SaaS Build Prompt

> Supplied by the product owner on 2026-11-18 as the specification for the hybrid SaaS
> platform. Kept here verbatim (formatting converted to Markdown). The assessment and phased
> plan are in [`../HYBRID_SAAS_AUDIT.md`](../HYBRID_SAAS_AUDIT.md) and
> [`../HYBRID_SAAS_PLAN.md`](../HYBRID_SAAS_PLAN.md).

- **Product:** Outlogik
- **Product category:** All-in-One Digital Marketing Intelligence, SEO & Agency Management SaaS
- **Platform model:** Hybrid Business SaaS + Agency SaaS
- **Development objective:** Evolve the existing Outlogik application into a scalable, modular, multi-tenant digital marketing platform.

---

## 1. Project objective

Transform Outlogik into a comprehensive digital marketing platform that supports two primary customer types:

1. Independent businesses and organizations that want to manage their own digital marketing activities.
2. Digital marketing agencies and consultants that need to manage multiple clients, teams, marketing campaigns, analytics and reporting from a centralized environment.

The platform must support both customer types through one unified application and shared backend infrastructure.

Do not create two separate applications.

Instead, develop a flexible account architecture that adapts the navigation, dashboards, permissions, tools and workflows based on the customer's account type and subscription entitlements.

Outlogik should become a centralized environment for:

- Search engine optimization.
- Website performance monitoring.
- Digital marketing analytics.
- Social media management.
- Paid advertising management.
- Content planning and management.
- Email marketing.
- Marketing campaign management.
- Conversion optimization.
- Competitor research.
- AI-assisted marketing recommendations.
- Client management.
- Marketing performance reporting.

The objective is to compete through usability, integration, automation, centralized reporting and affordability rather than simply attempting to replicate expensive enterprise marketing platforms.

## 2. Critical development instructions

Before modifying anything, conduct a comprehensive audit of the existing Outlogik codebase.

Existing development environment: Outlogik is currently being developed locally and will subsequently move to a staging environment for beta testing.

Requirements:

- Inspect the complete frontend and backend architecture.
- Identify all existing modules and implemented functionality.
- Review database schemas, migrations, API endpoints and authentication.
- Review the existing social media management module.
- Identify unfinished functionality, technical debt and duplicated components.
- Identify security vulnerabilities and architectural limitations.
- Review the existing branding, layouts, typography, navigation and design system.
- Preserve functioning features wherever possible.
- Do not unnecessarily rewrite working components.
- Do not remove existing functionality without justification.
- Do not introduce breaking database migrations without a migration strategy.

Produce an initial technical assessment and implementation roadmap before making significant architectural changes.

The existing Outlogik application is the starting point, not a disposable prototype.

## 3. Technology stack

Maintain the established technology direction.

**Frontend:** Angular · TypeScript · Bootstrap 5 · SCSS · Angular standalone components where appropriate · Angular Router · Reactive Forms · RxJS · Angular services and interceptors · ECharts for analytics and visualizations.

**Backend:** Python · FastAPI · SQLAlchemy · Pydantic · PostgreSQL · Redis · Celery for background processing and scheduled tasks.

**Reporting and document generation:** PDF report generation · CSV exports · Excel exports where appropriate · Automated scheduled reporting · Branded and white-label reports.

**Infrastructure and development:** Modular monolithic architecture initially · RESTful API architecture · Environment-based configuration · Database migrations using Alembic · Structured application logging · Automated testing · Background job monitoring · Secure environment variable management.

Do not introduce Docker as a requirement. The application must remain deployable in a conventional development and staging environment.

Avoid unnecessary microservices at this stage.

## 4. Hybrid account architecture

This is the most important architectural change.

Implement a flexible account structure that supports two primary workspace types.

### A. Business Workspace

Designed for individual businesses managing their own digital marketing.

Capabilities: one primary business workspace · website management · SEO monitoring · website auditing · keyword tracking · Google Analytics integration · Google Search Console integration · social media management · marketing campaign tracking · content planning · performance dashboards · AI-powered recommendations · automated reporting · marketing task management · team member invitations.

Business customers should not be required to understand agency terminology or multi-client management.

Their experience should be straightforward and focused on improving their own online presence.

### B. Agency Workspace

Designed for digital marketing agencies, consultants and marketing professionals.

Capabilities: multiple client accounts · multiple websites per client · multiple marketing campaigns per client · centralized client management · client-specific dashboards · agency-wide analytics · team management · role-based permissions · client onboarding · client invitations · client portals · white-label reporting · campaign approvals · task assignments · internal discussions · client communications · automated reporting · agency billing and subscription management.

Agencies must be able to switch between clients without repeatedly logging in and out.

Each client must have independently managed integrations, reporting, permissions and marketing data.

### C. Workspace and tenant architecture

Implement a secure multi-tenant architecture.

Recommended hierarchy:

- Platform
  - Tenant / Organization
    - Workspace
      - Business profile
      - Clients
      - Websites
      - Integrations
      - Campaigns
      - Analytics
      - Reports
      - Team members
      - Tasks

Support a business owner operating independently and an agency operating multiple client workspaces.

A business should also be able to grant an agency access to its workspace through an explicit invitation and permission-based relationship.

Avoid duplicating business data when an agency manages an existing business account.

Implement secure tenant-level data isolation across every database query, API endpoint, background job, report and file-access operation.

## 5. User roles and permissions

Implement granular role-based access control.

- **Platform-level roles:** Super Administrator · Platform Administrator · Support Administrator · Billing Administrator.
- **Business-level roles:** Business Owner · Business Administrator · Marketing Manager · Marketing Contributor · Reporting Viewer.
- **Agency-level roles:** Agency Owner · Agency Administrator · Account Manager · SEO Specialist · Social Media Manager · Marketing Strategist · Content Creator · Analyst · Client Viewer.

Permissions must be configurable.

Examples:

- Account managers can manage assigned clients.
- SEO specialists can access SEO tools for assigned clients.
- Social media managers can manage authorized social accounts.
- Analysts can access reporting without changing campaign settings.
- Clients can approve content and view reports without accessing internal agency information.

Implement permission checks on the backend, not just by hiding frontend navigation elements.

## 6. Platform modules

All modules should share a consistent design language, workspace structure and integration architecture.

### Module 1: SEO Management

Develop a comprehensive SEO toolkit.

Features: website SEO audits · technical SEO analysis · on-page SEO analysis · keyword research · keyword tracking · keyword ranking history · competitor keyword analysis where data is available · meta title and description analysis · heading structure analysis · broken link detection · internal linking analysis · sitemap validation · robots.txt analysis · canonical URL analysis · schema markup validation · image alt-text analysis · duplicate content identification · page speed analysis · mobile usability checks · SEO issue prioritization · historical audit comparisons · SEO recommendations.

Build an internal website crawler with configurable crawling limits, concurrency controls, rate limiting and robots.txt compliance.

Support scheduled audits and historical comparisons.

### Module 2: Website Analytics

Integrate: Google Analytics 4 · Google Search Console · Microsoft Bing Webmaster Tools · Google PageSpeed Insights · Google Tag Manager · Microsoft Clarity · Google Trends where accessible.

Features: website traffic · organic search traffic · sessions · users · landing page performance · traffic sources · conversion tracking · search impressions · click-through rates · average search position · device breakdown · geographic traffic · page performance · historical comparisons.

Provide unified analytics dashboards without misrepresenting or combining incompatible metrics.

### Module 3: Social Media Management

Preserve and expand the existing Outlogik social media module.

Do not replace functioning components with a new implementation.

Support platform integrations where approved API access is available: Facebook · Instagram · LinkedIn · YouTube · TikTok · Pinterest · X.

Features: social account connections · centralized social dashboard · content calendar · post scheduling · content drafts · media library · post approvals · publishing status · engagement analytics · audience analytics where available · campaign organization · multi-account management · AI-assisted content suggestions · hashtag suggestions · post performance reports.

Implement platform-specific publishing restrictions and API permission handling.

Never promise publishing functionality when the connected platform does not expose the required API capability.

### Module 4: Paid Advertising Management

Create a centralized advertising performance module.

Potential integrations: Google Ads · Meta Ads · LinkedIn Ads.

Features: campaign monitoring · advertising spend · impressions · clicks · CPC · CPM · CTR · conversions · conversion value · ROAS · campaign comparisons · advertising performance trends · budget monitoring · campaign reporting.

Initially prioritize read-only analytics and reporting.

Campaign creation, budget adjustments and advertising account modifications should require explicit authorization and appropriate permissions.

### Module 5: Content Marketing

Develop a content planning and management system.

Features: content calendar · blog planning · article briefs · content assignments · editorial workflows · content approval · content performance tracking · SEO content recommendations · AI-assisted outlines · content optimization · content status tracking · content library.

Support content workflows across multiple client accounts for agencies.

### Module 6: Email Marketing

Develop a modular email marketing system.

Features: contact management · audience segmentation · email campaign planning · newsletter management · campaign scheduling · campaign performance · open rates where reliably measurable · click-through rates · unsubscribe tracking · campaign reporting.

Use a modular integration approach, initially considering self-hosted or open-source solutions such as Listmonk.

Support appropriate consent, unsubscribe and Canadian anti-spam compliance requirements.

### Module 7: Conversion Rate Optimization

Develop tools to identify website conversion opportunities.

Features: conversion tracking · landing page performance · funnel analysis · conversion trends · form performance · CTA analysis · website usability observations · page-level recommendations · experiment tracking · A/B testing integration readiness.

Provide recommendations based on actual available data.

Do not fabricate conversion metrics or claim an experiment produced results without sufficient evidence.

### Module 8: Competitor Intelligence

Develop a competitor research workspace.

Features: competitor website tracking · competitor SEO comparisons · keyword overlap · content comparisons · website technology identification where feasible · search visibility comparisons · competitor monitoring · historical observations.

Clearly identify estimated, externally sourced and verified metrics.

Do not present unavailable third-party ranking or traffic data as verified information.

### Module 9: Marketing Intelligence and AI

Create a centralized AI-assisted intelligence layer.

AI capabilities: SEO audit explanations · marketing performance summaries · keyword clustering · content suggestions · competitor analysis summaries · campaign recommendations · social media content assistance · marketing strategy suggestions · anomaly identification · reporting summaries · natural-language questions about connected marketing data.

Examples: Why has organic traffic declined? · Which pages have the biggest SEO opportunities? · Which campaigns are producing the best returns? · Which keywords should we prioritize? · What should we improve this month? · Which clients need attention?

AI recommendations must reference available data, explain their reasoning and distinguish observations from suggestions.

Build a provider-agnostic AI integration layer so that AI providers can be changed without redesigning the application.

Implement usage limits, token tracking, permissions and cost controls.

## 7. Agency client management

This is a core differentiator for the hybrid platform.

Create a dedicated Client Management section.

Features: create and edit clients · client business profiles · contact information · website management · client-specific integrations · client-specific permissions · client notes · client activity history · client documents · client campaigns · client reports · client onboarding · client invitations · client status tracking.

Each client should have an individual workspace.

**Client portal.** Allow agencies to invite clients into a restricted portal.

Clients should be able to: view their marketing dashboard · view SEO audit results · access performance reports · review campaign progress · approve or reject content · review assigned tasks · communicate with their account manager · download reports · manage authorized account settings.

Clients must not have access to agency-wide analytics, internal discussions, other client accounts or confidential agency information.

## 8. Marketing campaign management

Develop a centralized campaign management module.

Features: campaign creation · campaign objectives · campaign descriptions · campaign budgets · campaign timelines · assigned team members · associated clients · marketing channels · campaign status · campaign tasks · campaign milestones · campaign performance · campaign reporting.

Support campaigns involving multiple marketing channels.

For example, one campaign may include: SEO improvements · blog content · Facebook advertising · Instagram publishing · email newsletters · landing page optimization.

Provide a unified campaign overview while retaining channel-specific performance data.

## 9. Unified dashboards

Create dashboards that adapt to the workspace type.

**Business dashboard:** website overview · SEO health · organic traffic · keyword performance · social media activity · advertising performance · marketing campaigns · conversion metrics · outstanding tasks · AI recommendations.

**Agency dashboard:** total clients · active clients · websites monitored · active campaigns · client performance overview · agency-wide SEO health · outstanding client approvals · upcoming tasks · team activity · reporting schedule · client performance alerts.

Include configurable dashboard widgets.

Allow users to customize their dashboard layouts and save preferred views.

## 10. Reporting and white-labeling

Develop a professional reporting engine.

Features: custom report builder · SEO reports · website analytics reports · social media reports · advertising reports · campaign reports · combined marketing reports · client-specific reports · scheduled reporting · PDF generation · CSV exports · Excel exports · historical comparisons.

**Agency white-labeling.** Allow eligible agency subscriptions to customize: agency logo · report branding · brand colors · footer information · company information · custom report titles · client-facing report presentation.

Provide a configurable report template system.

Reports must identify their reporting periods, data sources and any unavailable metrics.

## 11. Integration center

Create a centralized integration management environment.

Organize integrations by category: search and SEO · website analytics · social media · paid advertising · email marketing · AI providers · reporting and automation.

Each integration should support: connection status · authorization · credential management · permission visibility · last synchronization · synchronization history · error reporting · disconnect functionality · reauthorization · account selection.

Implement OAuth securely.

Store credentials encrypted and never expose access tokens through frontend responses or logs.

Use a modular integration adapter architecture so new integrations can be added without changing the core platform.

**Free-first integration strategy.** Prioritize free APIs, open-source solutions and internally developed capabilities.

Initial priorities: Google Analytics 4 · Google Search Console · Bing Webmaster Tools · Google PageSpeed Insights · Google Tag Manager · Microsoft Clarity · Lighthouse · Google Trends where available · internal SEO crawler · Listmonk.

Do not make the application dependent on paid third-party platforms.

Defer mandatory dependencies on: Semrush · Ahrefs · DataForSEO · HubSpot.

Paid integrations can be introduced later as optional enhancements when there is a clear business case.

## 12. Subscription and monetization architecture

Implement a flexible subscription and entitlement system.

Support separate subscription categories for business customers and agencies.

- **Business subscription structure.** Prepare configurable plans: Free / Starter · Professional · Business.
- **Agency subscription structure.** Prepare configurable plans: Agency Starter · Agency Professional · Agency Growth · Enterprise.

Do not hardcode plan prices or limits.

The Super Admin must be able to configure: subscription pricing · billing intervals · client limits · website limits · team member limits · SEO audit limits · keyword tracking limits · social account limits · reporting limits · AI usage limits · available integrations · advanced features · white-label availability.

Implement subscription entitlements as centralized backend policies.

A subscription upgrade must not require changing application code.

Prepare the architecture for payment gateway integration and recurring billing. Keep billing-provider dependencies modular.

## 13. Super Admin control center

Develop a comprehensive platform administration environment.

- **Platform overview:** total registered users · total organizations · business subscriptions · agency subscriptions · active clients · active websites · subscription revenue · trial accounts · account growth · platform usage · background job health.
- **User management:** view users · search users · suspend accounts · reactivate accounts · manage roles · review account status · view organization relationships · handle account support.
- **Organization management:** view business accounts · view agency accounts · inspect client relationships · manage subscription assignments · review usage · suspend organizations · manage feature access.
- **Subscription management:** create subscription plans · edit subscription plans · configure entitlements · manage trials · configure usage limits · review subscription activity.
- **Integration management:** configure available integrations · manage platform-level OAuth credentials · monitor API usage · review integration errors · disable problematic integrations.
- **Platform configuration:** feature flags · system settings · email templates · notification settings · AI provider configuration · platform announcements · maintenance mode · application logs.
- **Security and auditing:** administrative activity logs · authentication logs · failed login monitoring · permission changes · organization activity · security events.

All administrative actions must be logged and protected by appropriate permissions.

## 14. Notifications and communications

Develop a centralized notification system.

Support: in-app notifications · email notifications · task assignments · client invitations · approval requests · campaign updates · integration failures · SEO audit completion · scheduled report availability · subscription notifications · security alerts.

Implement user notification preferences and organization-level notification settings.

## 15. Tasks, approvals and workflows

Develop a centralized task management system.

Features: task creation · task assignments · due dates · priority levels · status tracking · comments · attachments · client associations · campaign associations · internal notes · approval workflows · activity history.

Support agency workflows where internal team members prepare content or campaign materials and clients approve them through their portal.

## 16. Database and backend architecture

Design the database around a scalable multi-tenant model.

Core entities should include: users · organizations · organization memberships · workspaces · business profiles · agency profiles · clients · client relationships · websites · domains · integrations · OAuth credentials · subscription plans · subscriptions · entitlements · usage records · campaigns · campaign channels · tasks · approvals · social accounts · social posts · SEO audits · SEO audit results · keywords · keyword rankings · analytics snapshots · reports · report templates · notifications · activity logs · AI requests · AI usage records · background jobs.

Requirements: proper foreign keys · appropriate indexes · referential integrity · database migrations · tenant ownership enforcement · soft deletion where appropriate · audit history · efficient query patterns · historical reporting support.

Implement tenant isolation using a consistent organization/workspace scoping strategy, with PostgreSQL row-level security where appropriate.

Never rely exclusively on frontend filtering for data security.

## 17. User experience and design system

Preserve the established Outlogik visual identity.

Design direction: professional · modern · minimalist · technology-oriented · clean dashboard layouts · monochromatic branding · strong typography · consistent spacing · clear data visualization · responsive layouts.

Avoid unnecessary visual clutter, excessive gradients, oversized decorative elements and inconsistent component styling.

Create a reusable design system covering: navigation · sidebar · header · dashboard cards · tables · filters · forms · modals · dropdowns · notifications · charts · data visualization · empty states · loading states · error states.

The application must be responsive across desktop, tablet and mobile.

**Navigation structure.** Adapt navigation according to workspace type and user permissions.

- Suggested business navigation: Overview · SEO · Website Analytics · Social Media · Advertising · Content · Email Marketing · Campaigns · Reports · Integrations · Settings.
- Suggested agency navigation: Agency Overview · Clients · Websites · SEO · Social Media · Advertising · Content · Campaigns · Tasks & Approvals · Reports · Team · Integrations · Agency Settings.

Include a workspace switcher where a user has access to multiple workspaces.

## 18. Security, privacy and compliance

Implement security as a core architectural requirement.

Requirements: secure authentication · password hashing · optional multi-factor authentication · role-based access control · tenant-level data isolation · secure OAuth · encrypted credentials · session management · rate limiting · API request validation · CSRF protection where applicable · secure file uploads · audit logging · backup and recovery procedures · secure error handling · protection against SQL injection · protection against cross-site scripting · secure password reset workflows.

Consider Canadian privacy requirements, including applicable PIPEDA obligations, and CASL requirements for email marketing.

Provide account data export and deletion workflows.

## 19. Automation and background processing

Use Redis and Celery for asynchronous processing.

Automate: scheduled SEO audits · website crawling · analytics synchronization · Search Console synchronization · keyword updates · social publishing where supported · report generation · scheduled email campaigns · notifications · data aggregation · integration health checks.

Implement: retry mechanisms · job failure handling · job monitoring · execution history · duplicate job prevention · rate limiting · API quota management.

Long-running processes must never block normal user interactions.

## 20. Performance and scalability

Design Outlogik for future growth.

Requirements: efficient database queries · pagination · caching · background processing · API response optimization · database indexing · frontend lazy loading · reusable components · modular services · efficient analytics aggregation.

Avoid unnecessary complexity during the initial implementation.

The architecture should support increasing numbers of businesses, agencies, clients, websites and integrations without requiring a complete rebuild.

## 21. Testing and quality assurance

Implement a comprehensive testing strategy.

- **Backend testing:** authentication · authorization · tenant isolation · organization relationships · API endpoints · subscription entitlements · integration connections · background jobs · report generation.
- **Frontend testing:** navigation · workspace switching · dashboard rendering · forms · tables · permissions · responsive layouts · loading and error states.
- **Critical security tests.** Verify that:
  - One business cannot access another business's data.
  - One agency cannot access another agency's clients.
  - Clients cannot access agency-only information.
  - Team members cannot exceed assigned permissions.
  - Suspended accounts cannot access protected resources.
  - Subscription limits are enforced by backend services.
  - Background jobs cannot leak information across tenants.

Do not mark a feature as complete simply because its interface has been implemented.

A completed feature must have functioning backend logic, database persistence, permission enforcement, error handling and appropriate tests.

## 22. Implementation roadmap

Build in controlled phases.

Do not attempt to implement every module simultaneously.

**Phase 1 — Hybrid SaaS Foundation.** Priority: core application and customer functionality.

- Existing codebase audit.
- Multi-tenant architecture.
- Business and agency account types.
- Organization and workspace management.
- Authentication and permissions.
- Subscription entitlement foundation.
- Business dashboard.
- Agency dashboard.
- Client management.
- Website management.
- SEO tools and website crawler.
- GA4 integration.
- Search Console integration.
- Existing social media module integration.
- Basic reporting.
- Client portal foundation.

**Phase 1.5 — Operational Readiness.** Priority: make the application usable for real businesses and agencies.

- Guided onboarding.
- Centralized integration center.
- Workspace switcher.
- Dashboard customization.
- Historical audit records.
- SEO monitoring.
- Alerts and notifications.
- Client invitations.
- Task management.
- Content approval workflows.
- Scheduled reporting.
- White-label report foundation.
- Team management.
- Activity logs.
- Super Admin dashboard.
- Subscription entitlement management.
- Feature flags.
- Background job monitoring.
- Integration error monitoring.
- Security and tenant-isolation testing.

**Phase 2 — Advanced Marketing Intelligence.** Paid advertising analytics · advanced social analytics · content marketing management · email marketing · competitor intelligence · conversion optimization · advanced AI recommendations · advanced reporting · automated workflows · advanced agency collaboration.

**Phase 3 — Commercial Expansion.** Full subscription billing · advanced white-labeling · custom agency branding · advanced client portal · expanded integration marketplace · additional AI providers · enterprise permissions · advanced automation · API access for customers · enterprise-level reporting.

## 23. Definition of done

The hybrid platform must not be considered complete until the following conditions are satisfied:

1. A business can register, create its workspace and manage its own marketing activities.
2. An agency can register and create an agency workspace.
3. An agency can onboard multiple clients.
4. Business customers can authorize an agency to access their workspace.
5. Agencies can switch between authorized client accounts.
6. Each client has independently managed marketing data and permissions.
7. The same underlying SEO and analytics tools work across both account types.
8. Clients can securely access their own portal.
9. Reports can be generated for individual businesses and agency clients.
10. Subscription entitlements are enforced through backend authorization.
11. Super Admin can manage organizations, users, subscriptions and platform configuration.
12. Existing social media functionality remains operational.
13. Integrations have reliable connection and synchronization handling.
14. Background jobs operate reliably.
15. Cross-tenant access tests pass.
16. The application is ready for staging deployment and controlled beta testing.

## 24. Development execution rules

Follow these rules throughout implementation:

- Audit before modifying.
- Reuse existing components and services.
- Preserve existing functionality.
- Avoid unnecessary dependencies.
- Prioritize free and open-source integrations.
- Avoid hardcoded subscription rules.
- Avoid hardcoded tenant identifiers.
- Avoid duplicating business and agency functionality.
- Maintain consistent API contracts.
- Use database migrations for schema changes.
- Keep sensitive credentials out of source control.
- Do not expose private data through API responses.
- Do not create nonfunctional placeholder buttons or mock features presented as completed functionality.
- Document new modules and architectural decisions.
- Provide meaningful error handling.
- Maintain a working development environment.

After each implementation phase:

1. Summarize what was completed.
2. Identify modified files and components.
3. Document database changes.
4. Report tests performed and their results.
5. Identify unfinished functionality.
6. Identify potential security concerns.
7. Recommend the next implementation milestone.

Do not proceed with destructive architectural changes without explaining their impact.

---

## Final development directive

The objective is to turn Outlogik into a commercially viable hybrid digital marketing SaaS platform.

It should provide independent businesses with accessible, self-service marketing tools while giving agencies a comprehensive environment to manage multiple clients, campaigns, teams and marketing operations.

The platform must share a common technology foundation, use secure multi-tenant architecture and offer modular functionality that can grow over time.

Build for usability, reliability, affordability, scalability and commercial viability.

Do not sacrifice functional quality for feature quantity.

Prioritize a cohesive, working platform over a collection of disconnected marketing tools.

Begin with the existing codebase audit, document the current architecture, identify required changes and present a phased implementation plan before beginning significant development.
