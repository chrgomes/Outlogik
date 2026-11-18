# AI Search Intelligence: how the addendum fits the plan

Covers the addendum [`specs/AI_SEARCH_ADDENDUM.md`](specs/AI_SEARCH_ADDENDUM.md) (GEO, AEO and
AI search visibility), received 2026-11-18. The main plan is
[`HYBRID_SAAS_PLAN.md`](HYBRID_SAAS_PLAN.md). Provider facts were checked on 2026-11-18; they
change often and are checked again before each part is built.

**Status:** approved 2026-11-18 (A1–A4 as recommended). D8, the AI model, stays open until H2.

---

## 1. What the addendum assumes that doesn't exist yet

The addendum talks about "existing" parts of Outlogik that aren't built:

| It says "existing…" | Reality | Where it comes from |
|---|---|---|
| SEO capabilities, website audits | Not built (no crawler yet) | H1-6 |
| Analytics | Not built | H1-7 (GA4, Search Console) |
| AI provider abstraction, AI recommendation engine | Not built; the AI provider isn't chosen (decision D8) | H1-5 adapters; AI in H2 |
| Content management module | Not built | H2 (campaigns and content) |
| Competitor intelligence | Not built | H2 |
| Tasks | Not built | H1.5 |
| Subscription entitlements | Not built | H1-4 |

So AI Search Intelligence is built **on top of** those, in step with them. Nothing in it
starts as a separate application.

## 2. What can actually be measured (checked 2026-11-18)

The addendum rightly says not every provider has an API. This is what's officially available.

| Source | What it gives | Cost and limits | Use in Outlogik |
|---|---|---|---|
| **Bing Webmaster Tools, AI Performance** | Real counts of how often Copilot and Bing's AI answers **cite the site's pages**, with the grounding queries | Free, official, in preview since Feb 2026. CSV export. API export was reported in June 2026 but isn't confirmed in Microsoft's docs | Main source for Copilot. Use the API if confirmed, otherwise a CSV upload |
| **Google Search Console, generative AI report** | Impressions in AI Overviews and AI Mode | Free, official, since June 2026. Reported as UI-only, impressions only (no clicks, queries or citation position) | Pull it if Google's API exposes it. Otherwise show the limit plainly and link to it |
| **Google Analytics 4 referrals** | Real visits from chatgpt.com, perplexity.ai, gemini.google.com, copilot.microsoft.com | Free, through the H1-7 GA4 connection | An "AI referral traffic" view. Actual visitors, not estimates |
| **OpenAI API with web search** | Answers to the user's monitoring queries, with the URLs cited | Paid per call. Official. Cited links must be shown clickable. **Not the same as the ChatGPT app** (no personalization, may use different sources) | Sampled probes, labelled "OpenAI API with web search", never "ChatGPT" |
| **Perplexity API** | Answers with citations | Paid per call. Official. The API was reportedly reorganized in Sept 2026; to verify | Sampled probes, labelled as such |
| **Gemini API with Google Search grounding** | Answers with sources | Paid. **Its terms appear to forbid storing grounded results or using them for analysis**, which is exactly what monitoring does | Left out unless a review of the current terms allows it |
| **Google AI Overviews / AI Mode answers** | The actual answers shown in Google | **No official API.** Third-party SERP vendors sell this data by scraping Google | Left out: it would break the addendum's own "no unauthorized scraping" rule |

**How results stay honest:**
- AI answers change from run to run and from person to person. Each query is run several
  times per check, and results read like "mentioned in 3 of 5 runs on 18 Nov, OpenAI API with
  web search, Canada, English", never as a ranking.
- Every number on screen says its source, method, query set, location and period, as the
  addendum asks. Any score (e.g. "AI visibility") has its formula shown next to it.
- Mentions are found by matching the brand and product names the user gives, so they can be
  checked. Sentiment and recommendation detection need an AI model; those labels are marked as
  AI-classified and can be corrected.
- "Factual accuracy" can't be verified automatically. The audit checks **consistency**:
  the same name, address, phone, hours and prices across the site, its structured data and the
  business profile. It points out contradictions; it doesn't claim to know which is true.
- Nothing promises placement in AI answers, on the website or in the app.

## 3. Where each part goes

| Part of the addendum | Needs | Goes into |
|---|---|---|
| **GEO technical audit:** AI crawler access in robots.txt (search bots vs training bots, like Outlogik's own site), structured data (Organization, LocalBusiness, Product, FAQ, Article and author), business identity consistency, indexability, internal links, question-and-answer coverage, product and service information | The crawler | **H1-6**, as checks in the same website audit, with its own "AI search readiness" section. Free; no new services |
| AI referral traffic (GA4); Bing AI citations; Google AI impressions where available | The integration framework | **H1-7** |
| Question-style queries from the site's own Search Console data (free, real) | Search Console | H1-7 / H1-8 |
| **Monitoring:** queries, scheduled runs, mentions, citations, history, a basic AI Visibility page | Celery (H1-5), entitlements and cost tracking (H1-4), paid provider keys, an AI model for sentiment (D8) | **First H2 module** (proposed, decision A1) |
| Competitor AI visibility, content gaps, AEO recommendations, recommendations → tasks | Monitoring, tasks (H1.5), content module | H2, after monitoring |
| AI content briefs and content optimization | Content module, AI model | H2, with the content module |
| White-label GEO reports, more providers | White-label (H3) | H3 |

The addendum's own phases map onto this: its Phase 1 → H1-6/H1-7, Phase 1.5 → first H2
module, Phase 2 → later H2, Phase 3 → H3.

**Agencies and businesses:** everything is per workspace, so a business monitors its own
brand and an agency monitors each client separately, with the client's competitors and
queries. Client Viewers see their own workspace's results only.

**Google Business Profile** (decided 2026-11-18): its details (name, address, phone,
hours, reviews) feed local results and AI answers, so it's part of the business identity
consistency checks once Google approves API access. See `HYBRID_SAAS_PLAN.md`, H2.

**Paid keyword research** (search volumes) stays out, as before: question-style queries
come from the site's own Search Console data instead.

## 4. Data model (when monitoring is built)

Following the addendum's list, every row carries `organization_id` and `workspace_id`:

- `ai_providers` (catalogue in code, enabled per plan) and `ai_monitoring_configs` (brand
  names, products, competitors, location, language, frequency)
- `ai_monitoring_queries`, `ai_search_runs`, `ai_search_responses`
- `ai_mentions` (brand, product, competitor; matched text; sentiment with its source),
  `ai_citations` and `citation_sources` (domain, first and last seen)
- `ai_visibility_snapshots` (daily roll-ups, so dashboards don't scan raw responses)
- GEO audit findings live with the H1-6 audit findings (one table, an `area` column), so
  there's one list of issues per site, not two
- `recommendations`, shared with the rest of the platform

Raw responses are kept for the plan's retention period, then deleted; snapshots stay.
Provider keys are encrypted, as in the integration framework.

## 5. Decisions (approved 2026-11-18)

| # | Question | Decision |
|---|---|---|
| A1 | When does monitoring come? | **First H2 module, before social media.** Social media waits on Meta and LinkedIn app reviews anyway; monitoring needs no reviews. The free GEO audit and AI traffic views come earlier, in H1-6 and H1-7 |
| A2 | Which sources? | **Official ones only** (section 2). Leave out Google AI Overview scraping vendors and, unless the terms allow it, Gemini grounding. Say so in the app |
| A3 | Who pays for the paid AI calls? | **Outlogik's own keys, with limits per plan** and cost tracking for Super Admin. Customers don't have to set up keys. (Alternative: customers bring their own keys.) |
| A4 | Navigation | **One "AI Search" item** in the sidebar with tabs inside (Overview, Mentions, Citations, Audit, Settings), appearing only once it works. Not the addendum's 13 menu entries |
| D8 | AI model (still open) | Needed by the start of H2 for sentiment and recommendations; decide then |
