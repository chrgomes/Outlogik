import { IconName } from '@brand/icon/icons';

/**
 * Content for the service pages (spec §5 structure, adapted for an agency: what we do, what's
 * included, how we work, what you'll see in the portal, questions, related services, CTA).
 *
 * Copy rules (spec §19): outcomes over feature lists, no guaranteed rankings or results, no
 * invented numbers, location-neutral until a service area is set (plan revision 2, decision A).
 */

export interface Included {
  icon: IconName;
  title: string;
  text: string;
}

export interface Step {
  title: string;
  text: string;
}

export interface Question {
  q: string;
  a: string;
}

export interface ServiceContent {
  slug: string;
  /** Meta description (fuller SEO handling comes in step 11). The title is in SERVICES. */
  description: string;
  headline: string;
  lead: string;
  /** "What we do": a short explanation in plain English. */
  intro: string[];
  included: Included[];
  /** What the client gets out of it (benefits, not features). */
  outcomes: string[];
  steps: Step[];
  /** Client-portal features relevant to this service (statuses come from the admin area). */
  portalFeatures: string[];
  questions: Question[];
  related: string[];
}

export const SERVICE_CONTENT: Record<string, ServiceContent> = {
  seo: {
    slug: 'seo',
    description:
      'Technical SEO, keyword research and on-page optimisation from Outlogik, with clear monthly reporting in your own client portal.',
    headline: 'SEO that helps the right people find you.',
    lead:
      'We fix what’s holding your website back, focus on the searches that matter to your business, and report on progress every month in plain English.',
    intro: [
      'Search engine optimisation is the work of making your website easy for search engines to understand and worth showing to the people searching for what you offer.',
      'Good SEO is steady, unglamorous work: fixing technical problems, writing pages that answer real questions, and measuring what changes. That’s the work we do.',
    ],
    included: [
      { icon: 'search', title: 'Technical SEO audit', text: 'A full check of your site for problems that affect search: speed, broken links, indexing and structure.' },
      { icon: 'lightning-charge', title: 'Fixes, prioritised', text: 'We fix what we can directly and give your developer clear instructions for the rest, starting with what matters most.' },
      { icon: 'bar-chart-line', title: 'Keyword research', text: 'The searches your customers actually make, and which ones are realistic to compete for.' },
      { icon: 'pencil-square', title: 'On-page optimisation', text: 'Titles, headings, descriptions and content on your key pages, written for people and search engines.' },
      { icon: 'building', title: 'Local search', text: 'Your Google Business Profile and local listings, if customers find you by location.' },
      { icon: 'file-earmark-bar-graph', title: 'Monthly reporting', text: 'Search performance from Google Search Console, what we did, and what we recommend next.' },
    ],
    outcomes: [
      'A clear picture of how your website performs in search today',
      'Problems fixed in order of impact, not all at once',
      'Pages that answer the questions your customers are asking',
      'Progress you can follow month by month',
    ],
    steps: [
      { title: 'Audit', text: 'We review your website, your search performance and your competitors.' },
      { title: 'Plan', text: 'We agree priorities with you: the fixes and pages that will make the biggest difference.' },
      { title: 'Optimise', text: 'We make the changes, or work with your developer, and keep a record of what was done.' },
      { title: 'Measure and report', text: 'Each month we report on results and adjust the plan.' },
    ],
    portalFeatures: ['websites-overview', 'activity-history', 'seo-health', 'monthly-reports'],
    questions: [
      { q: 'How long does SEO take to work?', a: 'Usually months rather than weeks. Technical fixes can help quickly; new content and rankings take longer. We’ll give you an honest view for your site in the consultation.' },
      { q: 'Can you guarantee a first-page ranking?', a: 'No, and no one honestly can: search engines decide rankings. What we can promise is careful work, clear priorities and transparent reporting on the results.' },
      { q: 'Do you need access to my website?', a: 'Usually we need access to Google Search Console and Analytics, and to your website’s editor or your developer. We’ll list exactly what’s needed in the proposal.' },
      { q: 'Will you work with my web developer?', a: 'Yes. For changes we can’t make directly, we send clear, prioritised instructions to your developer.' },
    ],
    related: ['content-marketing', 'website-analytics-reporting'],
  },

  'social-media-management': {
    slug: 'social-media-management',
    description:
      'Planned, on-brand social media from Outlogik: strategy, content calendars, posting and community management, with monthly reporting.',
    headline: 'Social media that sounds like you, every week.',
    lead:
      'We plan your posts a month ahead, write and design them in your voice, publish them on schedule, and tell you what’s working.',
    intro: [
      'Most businesses know they should post regularly. Few have the time to do it well. We take that off your plate without losing what makes your business sound like you.',
      'You approve the plan and the posts. We handle the planning, writing, design, publishing and reporting.',
    ],
    included: [
      { icon: 'diagram-3', title: 'Strategy', text: 'Which channels matter for your customers, what to post, and how often.' },
      { icon: 'clock-history', title: 'Content calendar', text: 'A month of posts planned ahead, so you always know what’s coming.' },
      { icon: 'pencil-square', title: 'Copy and design', text: 'Posts written and designed to fit your brand, ready for your approval.' },
      { icon: 'megaphone', title: 'Scheduling and publishing', text: 'Posts go out on time, on every agreed channel.' },
      { icon: 'people', title: 'Community management', text: 'Replies to comments and messages, within the scope agreed in your proposal.' },
      { icon: 'file-earmark-bar-graph', title: 'Monthly reporting', text: 'Reach, engagement and what we learned, with recommendations for next month.' },
    ],
    outcomes: [
      'A consistent presence without spending your evenings on it',
      'Posts that sound like your business',
      'Nothing published without your approval',
      'A clear view of what your audience responds to',
    ],
    steps: [
      { title: 'Get to know you', text: 'Your customers, your voice and your goals.' },
      { title: 'Plan', text: 'A monthly calendar of posts for you to review.' },
      { title: 'Create and approve', text: 'We write and design; you approve or ask for changes.' },
      { title: 'Publish and report', text: 'We post on schedule and report on results each month.' },
    ],
    portalFeatures: ['client-portal', 'activity-history', 'social-approvals', 'monthly-reports'],
    questions: [
      { q: 'Which platforms do you manage?', a: 'The ones where your customers are, typically Facebook, Instagram and LinkedIn. We agree the channels in your proposal.' },
      { q: 'Do I approve posts before they go out?', a: 'Yes, always. Today approvals happen by email or a shared document; approving posts in your client portal is in development.' },
      { q: 'Do you run paid social ads?', a: 'Our social media service covers organic posting and community management. If you’re interested in paid ads, mention it in your consultation.' },
      { q: 'Who owns the social accounts?', a: 'You do. We work through access you grant, which you can remove at any time.' },
    ],
    related: ['content-marketing', 'website-analytics-reporting'],
  },

  'website-analytics-reporting': {
    slug: 'website-analytics-reporting',
    description:
      'Google Analytics 4 and Search Console set up properly, conversion tracking, and a monthly report from Outlogik that explains what changed and why.',
    headline: 'Know what’s working, and why.',
    lead:
      'We set up your analytics properly, track the actions that matter to your business, and send a monthly report that explains your results in plain English.',
    intro: [
      'Many websites have analytics installed but no one trusts the numbers, or no one looks at them. We fix the setup, then turn the data into decisions.',
      'Every report answers three questions: what happened, why it matters, and what we recommend next.',
    ],
    included: [
      { icon: 'graph-up', title: 'Google Analytics 4', text: 'A new setup, or an audit and fix of the one you have.' },
      { icon: 'search', title: 'Search Console and Bing', text: 'Your site verified with Google Search Console and Bing Webmaster Tools.' },
      { icon: 'lightning-charge', title: 'Conversion tracking', text: 'The actions that matter, such as enquiries, calls, bookings or purchases, tracked reliably.' },
      { icon: 'shield-check', title: 'Consent-aware tracking', text: 'Analytics configured to respect your visitors’ cookie choices.' },
      { icon: 'file-earmark-bar-graph', title: 'Monthly report', text: 'Traffic, sources, search performance and conversions, explained clearly.' },
      { icon: 'people', title: 'Review together', text: 'Time each month to go through the report and agree next steps, if you’d like it.' },
    ],
    outcomes: [
      'Numbers you can trust',
      'A monthly report you’ll actually read',
      'Decisions based on what your customers do',
      'One place to see results across your marketing',
    ],
    steps: [
      { title: 'Audit', text: 'We check what’s installed, what’s tracked and what’s missing.' },
      { title: 'Set up and fix', text: 'We configure analytics and conversion tracking properly.' },
      { title: 'Report monthly', text: 'A clear report with what changed and why.' },
      { title: 'Review and improve', text: 'We agree changes with you and measure the effect.' },
    ],
    portalFeatures: ['websites-overview', 'activity-history', 'analytics-dashboards', 'monthly-reports'],
    questions: [
      { q: 'I already have Google Analytics. Can you work with it?', a: 'Yes. We start with an audit of your existing setup and fix what’s missing or wrong, keeping your history.' },
      { q: 'What’s in a monthly report?', a: 'Visitors and where they came from, search performance, conversions, what changed since last month, and what we recommend.' },
      { q: 'Can I see reports in my client portal?', a: 'Today reports are sent to you each month. Reading them in your client portal, with live analytics dashboards, is in development.' },
      { q: 'Do I need to change my website?', a: 'Sometimes a small change is needed to add tracking. We’ll tell you exactly what and why before anything is changed.' },
    ],
    related: ['seo', 'content-marketing'],
  },

  'content-marketing': {
    slug: 'content-marketing',
    description:
      'Content strategy, articles and website copy from Outlogik, written for your customers first and search engines second.',
    headline: 'Content written for your customers first.',
    lead:
      'We plan, write and improve the articles and pages that answer your customers’ questions, so your website does more of the selling for you.',
    intro: [
      'Good content is useful before it’s promotional. It answers the questions your customers ask before they buy, and it gives search engines a reason to show your website.',
      'We plan topics from real searches, write in your voice, and measure what each piece achieves.',
    ],
    included: [
      { icon: 'diagram-3', title: 'Content strategy', text: 'What to write, for whom, and why, based on your customers and their searches.' },
      { icon: 'search', title: 'Keyword-to-content planning', text: 'Each piece planned around the questions people actually search for.' },
      { icon: 'pencil-square', title: 'Articles and blog posts', text: 'Well-researched, useful writing in your voice.' },
      { icon: 'window-stack', title: 'Website copy', text: 'Service pages, about pages and landing pages that are clear and persuasive.' },
      { icon: 'arrow-repeat', title: 'Improving what you have', text: 'Updating and optimising existing pages that are close to performing well.' },
      { icon: 'file-earmark-bar-graph', title: 'Measuring results', text: 'Which pieces bring visitors and enquiries, reported monthly.' },
    ],
    outcomes: [
      'A steady stream of useful content without writing it yourself',
      'Pages that answer real customer questions',
      'Content that supports your SEO',
      'Nothing published without your approval',
    ],
    steps: [
      { title: 'Research', text: 'Your customers, your competitors and the questions people search for.' },
      { title: 'Plan', text: 'A content calendar for you to review and approve.' },
      { title: 'Write and review', text: 'We write; you review and approve each piece.' },
      { title: 'Publish and measure', text: 'We publish (or hand over) and report on what each piece achieves.' },
    ],
    portalFeatures: ['client-portal', 'activity-history', 'monthly-reports'],
    questions: [
      { q: 'Do I get to review everything?', a: 'Yes. Nothing is published until you’ve approved it.' },
      { q: 'How much content do you write each month?', a: 'It depends on your goals and budget. We agree the amount in your proposal and can change it as we learn what works.' },
      { q: 'Will you publish it on my website?', a: 'Yes, if you’d like us to and we have access. Or we hand it over ready to publish.' },
      { q: 'Can you write about technical or specialist topics?', a: 'Yes. We research carefully and ask you to check anything specialist before it goes out.' },
    ],
    related: ['seo', 'social-media-management'],
  },
};
