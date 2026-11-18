# OUTLOGIK MASTER BUILD PROMPT — ADDENDUM

> Received 2026-11-18 as an addendum to [`HYBRID_SAAS_SPEC.md`](HYBRID_SAAS_SPEC.md). Saved
> as written. How it fits the plan: [`../AI_SEARCH_PLAN.md`](../AI_SEARCH_PLAN.md).

**AI Search Optimization, Generative Engine Optimization (GEO) & Answer Engine Optimization (AEO)**

- Integration: Core Outlogik Platform
- Priority: High
- Implementation: Phased
- Module Name: Outlogik AI Search Intelligence

## 1. OBJECTIVE

Expand Outlogik's existing SEO capabilities by introducing a dedicated AI Search Intelligence module.

The module must support:

- Generative Engine Optimization (GEO).
- Answer Engine Optimization (AEO).
- AI search visibility monitoring.
- AI brand mention tracking.
- AI citation monitoring.
- AI competitor visibility analysis.
- AI search content optimization.
- Entity and authority analysis.

The objective is to help businesses and marketing agencies understand, measure and improve their visibility across traditional search engines and AI-powered search experiences.

This must be implemented as a native Outlogik module integrated with the existing SEO, analytics, content management, competitor intelligence and AI recommendation systems.

Do not create a separate application.

## 2. SUPPORTED AI SEARCH PLATFORMS

Design a provider-agnostic integration architecture that supports monitoring across:

- ChatGPT Search.
- Google AI Overviews.
- Google AI Mode where accessible.
- Google Gemini.
- Microsoft Copilot.
- Perplexity.
- Other supported AI-powered search providers as integrations become available.

Do not assume every provider exposes a public API for search visibility monitoring.

Use officially supported APIs, authorized integrations and permitted data collection methods.

Where direct measurement is unavailable, clearly identify the limitation and provide alternative monitoring methods.

Never fabricate AI search results, brand mentions, citations or visibility scores.

## 3. AI BRAND VISIBILITY MONITORING

Develop a monitoring system that allows users to track how their business, products and services appear in AI-generated search responses.

Features:

- Brand mention tracking.
- Product mention tracking.
- Service mention tracking.
- Business recommendation tracking.
- Competitor mention tracking.
- Brand visibility history.
- Positive, neutral and negative sentiment classification.
- Citation URL identification.
- Search query monitoring.
- Geographic and language segmentation where supported.

Allow users to create custom monitoring queries.

Support scheduled monitoring and historical comparisons.

## 4. AI CITATION TRACKING

Develop a dedicated citation analysis engine.

Track:

- Whether the business website is cited.
- Which pages are cited.
- Which external sources are cited.
- Competitor citation frequency.
- Citation source authority indicators.
- Citation trends.
- Newly discovered citation sources.
- Lost citation opportunities.

Allow users to identify pages and external publications that appear to influence AI-generated recommendations.

Distinguish between direct website citations, brand mentions without links and third-party references.

## 5. GENERATIVE ENGINE OPTIMIZATION AUDIT

Build an automated GEO website audit.

Analyze:

- Content clarity.
- Factual accuracy.
- Topical coverage.
- Author credibility.
- Business identity consistency.
- Organization information.
- Structured data.
- Schema markup.
- Internal linking.
- Crawl accessibility.
- Indexability.
- Authoritative external references.
- Content originality.
- Question-and-answer coverage.
- Product and service information.
- Entity relationships.

Generate actionable recommendations with:

- Issue description.
- Affected URL.
- Priority.
- Potential impact.
- Recommended correction.
- Implementation status.

Do not represent GEO scores as official search engine rankings or provider-certified metrics.

## 6. ANSWER ENGINE OPTIMIZATION

Develop an AEO optimization toolkit.

Features:

- Question-based keyword research.
- Conversational search query discovery.
- FAQ opportunity identification.
- Featured snippet opportunities.
- Direct-answer content analysis.
- Voice-search content opportunities.
- Structured content recommendations.
- Question-and-answer content optimization.
- Search intent classification.

Identify opportunities to make website content more useful for direct-answer and conversational search experiences.

## 7. AI CONTENT OPTIMIZATION

Integrate GEO and AEO recommendations into the existing Outlogik content management module.

Features:

- Existing content analysis.
- AI content briefs.
- Topic gap identification.
- Question coverage analysis.
- Content structure recommendations.
- Supporting source recommendations.
- Factual consistency checks.
- Entity optimization.
- Internal linking recommendations.
- Content refresh suggestions.

Allow users to optimize existing content without unnecessarily rewriting entire pages.

AI-generated recommendations must be evidence-based and clearly distinguish suggestions from verified facts.

## 8. AI COMPETITOR VISIBILITY ANALYSIS

Allow users and agencies to compare AI search visibility against competitors.

Features:

- Competitor brand mentions.
- Competitor citation frequency.
- Competitor recommendation frequency.
- Competitor visibility comparisons.
- Citation source comparisons.
- Topic-level visibility comparisons.
- Content gap analysis.
- Historical competitor trends.

Allow agencies to manage competitor monitoring independently for each client.

## 9. AI SEARCH VISIBILITY DASHBOARD

Create a dedicated dashboard accessible through the primary Outlogik navigation.

Suggested navigation:

SEO Management

- SEO Overview
- Website Audits
- Keyword Research
- Keyword Tracking
- Technical SEO

AI Search Intelligence

- AI Visibility Overview
- Brand Mentions
- Citation Tracking
- GEO Audits
- AEO Optimization
- Competitor AI Visibility
- AI Content Opportunities
- Monitoring Settings

Dashboard metrics:

- AI visibility.
- Brand mentions.
- Citation frequency.
- Share of voice.
- Competitor visibility.
- Sentiment distribution.
- Top cited pages.
- Top citation sources.
- Monitoring history.
- Recommended actions.

All dashboard metrics must be derived from actual collected data.

Clearly identify the measurement methodology, provider, query set, geographic scope and reporting period.

## 10. AI SEARCH RECOMMENDATION ENGINE

Connect GEO and AEO findings to Outlogik's existing AI intelligence engine.

Provide recommendations such as:

- Improve content coverage for a specific topic.
- Add missing business information.
- Improve organization schema.
- Expand relevant FAQ content.
- Improve author attribution.
- Strengthen internal linking.
- Improve technical accessibility.
- Address competitor content gaps.
- Update outdated information.

Prioritize recommendations based on potential impact, implementation effort and supporting evidence.

Allow users to convert recommendations into tasks.

## 11. DATABASE ARCHITECTURE

Introduce the following entities where appropriate:

- AI search providers.
- AI monitoring configurations.
- AI monitoring queries.
- AI search executions.
- AI search responses.
- Brand mentions.
- Competitor mentions.
- Citation records.
- Citation sources.
- GEO audit records.
- GEO audit findings.
- AEO opportunities.
- AI visibility snapshots.
- Competitor visibility snapshots.
- AI optimization recommendations.

Every record must be associated with the appropriate organization, workspace and client where applicable.

Implement historical data retention policies, tenant isolation and efficient indexing.

## 12. API ARCHITECTURE

Develop modular FastAPI endpoints for:

- Provider configuration.
- Monitoring query management.
- Monitoring execution history.
- Brand mention retrieval.
- Citation retrieval.
- GEO audits.
- AEO opportunities.
- Competitor comparisons.
- Visibility reporting.
- Recommendation management.

Use asynchronous background processing for scheduled monitoring and analysis.

Implement provider-specific adapters behind a common interface.

## 13. SUBSCRIPTION AND USAGE MANAGEMENT

Integrate AI Search Intelligence with Outlogik's existing subscription entitlement system.

Allow Super Admin to configure:

- Number of monitored brands.
- Number of competitors.
- Number of monitoring queries.
- Monitoring frequency.
- Supported providers.
- Historical data retention.
- GEO audit limits.
- AI analysis limits.
- Advanced reporting access.

Do not hardcode subscription limits.

Monitor API usage and associated costs.

Provide appropriate usage notifications and configurable limits.

## 14. AGENCY AND CLIENT SUPPORT

Make AI Search Intelligence available across both Business and Agency workspaces.

Business customers must be able to monitor their own brand.

Agency customers must be able to:

- Monitor multiple clients.
- Configure client-specific queries.
- Compare competitors for each client.
- Generate client-specific GEO reports.
- Schedule monitoring.
- Assign optimization tasks.
- Track GEO improvement over time.
- Produce white-label AI visibility reports.

Client permissions must be respected throughout the module.

## 15. IMPLEMENTATION ROADMAP

**Phase 1 — Foundation**

- GEO and AEO database architecture.
- AI provider adapter framework.
- Technical GEO auditing.
- Entity analysis.
- Structured data analysis.
- AI crawler accessibility checks.

**Phase 1.5 — Monitoring**

- Brand visibility monitoring.
- Custom search queries.
- AI mention tracking.
- Citation tracking.
- Basic GEO dashboard.
- Historical monitoring.

**Phase 2 — Intelligence**

- Competitor AI visibility.
- Content gap analysis.
- Advanced AEO recommendations.
- AI-assisted content optimization.
- Automated GEO recommendations.

**Phase 3 — Agency Expansion**

- Multi-client GEO management.
- White-label GEO reports.
- Advanced monitoring schedules.
- Historical comparisons.
- Advanced AI search analytics.
- Expanded provider integrations.

## 16. DEVELOPMENT REQUIREMENTS

- Integrate with the existing Outlogik codebase.
- Reuse existing authentication and tenant architecture.
- Reuse the existing AI provider abstraction where possible.
- Preserve existing SEO functionality.
- Avoid duplicate services.
- Use modular API architecture.
- Implement comprehensive tests.
- Enforce tenant isolation.
- Document data collection and measurement methodology.
- Do not use unauthorized scraping methods.
- Do not fabricate metrics.
- Do not promise guaranteed AI search placement.

## FINAL OBJECTIVE

Establish Outlogik as a comprehensive SEO, GEO and AEO intelligence platform.

The module must help businesses and agencies understand their visibility across traditional search engines and AI-powered answer engines.

Outlogik should not merely report search visibility. It should identify opportunities, recommend improvements, support implementation and measure changes over time.

Make AI Search Intelligence a first-class product capability rather than an optional extension of traditional SEO.
