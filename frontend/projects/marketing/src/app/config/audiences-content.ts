import { Question } from './services-content';

/**
 * Content for the "Who we help" pages (plan revision 2, decision B). Same copy rules as the
 * service pages: no invented statistics or results, no guarantees, location-neutral.
 */

export interface AudienceContent {
  slug: string;
  description: string;
  headline: string;
  lead: string;
  /** "Sound familiar?": problems this kind of business typically has. */
  challenges: string[];
  /** How each service helps this kind of business, in recommended order. */
  help: { service: string; text: string }[];
  /** How we approach work for this kind of business. */
  approach: { title: string; text: string }[];
  questions: Question[];
}

export const AUDIENCE_CONTENT: Record<string, AudienceContent> = {
  'small-businesses': {
    slug: 'small-businesses',
    description:
      'Digital marketing for small businesses from Outlogik: SEO, social media, content and reporting, planned around your budget.',
    headline: 'A marketing team, without hiring one.',
    lead:
      'You run the business. We run the marketing: search, social, content and reporting, planned around your goals and your budget.',
    challenges: [
      'Marketing happens when there’s time, which is rarely.',
      'You’re not sure what’s working, or whether any of it is.',
      'Hiring a full-time marketer isn’t realistic yet.',
      'Juggling separate freelancers means juggling separate plans.',
    ],
    help: [
      { service: 'seo', text: 'Make sure customers searching for what you do can find you.' },
      { service: 'social-media-management', text: 'Regular, on-brand posts, without you writing them late at night.' },
      { service: 'content-marketing', text: 'Website pages that explain clearly what you do and why to choose you.' },
      { service: 'website-analytics-reporting', text: 'A simple monthly report: what’s working, and what we’ll do next.' },
    ],
    approach: [
      { title: 'Start with what matters most', text: 'We recommend where to focus first, rather than doing everything at once.' },
      { title: 'Shaped to your budget', text: 'Your proposal covers the work that will make the most difference for what you want to spend.' },
      { title: 'One point of contact', text: 'One team for all your marketing, so there’s one plan and one person to talk to.' },
    ],
    questions: [
      { q: 'We have a small budget. Can you still help?', a: 'Often, yes. We’ll recommend where to focus first, and tell you honestly if we think your money would be better spent elsewhere.' },
      { q: 'How much of my time will it take?', a: 'A little: a consultation at the start, approving anything before it’s published, and a monthly check-in if you’d like one. We handle the rest.' },
      { q: 'Can we start with one service?', a: 'Yes. Many businesses start with one service and add others once they see how it works.' },
    ],
  },

  'local-businesses': {
    slug: 'local-businesses',
    description:
      'Local SEO, Google Business Profile, content and enquiry tracking for clinics, trades and professional services, from Outlogik.',
    headline: 'Be the obvious choice nearby.',
    lead:
      'For clinics, trades and professional services: show up when local customers search, and give them good reasons to choose you.',
    challenges: [
      'Competitors appear in local search results and you don’t.',
      'Your Google Business Profile is incomplete or out of date.',
      'Your website doesn’t say clearly what you do, and where.',
      'Calls and enquiries come in, but no one knows which marketing brought them.',
    ],
    help: [
      { service: 'seo', text: 'Local SEO and your Google Business Profile, so you appear in map and local results.' },
      { service: 'content-marketing', text: 'Service and area pages that answer what local customers ask.' },
      { service: 'website-analytics-reporting', text: 'Calls, bookings and enquiries tracked, so you know which channels bring customers.' },
      { service: 'social-media-management', text: 'Stay visible in your community with regular, local posts.' },
    ],
    approach: [
      { title: 'Local search first', text: 'Your Google Business Profile and local listings are usually the quickest place to make a difference.' },
      { title: 'Useful pages, not filler', text: 'Pages for your services and areas that help customers, not repetitive pages written for search engines.' },
      { title: 'Enquiries you can trace', text: 'We track the calls and forms that matter, so you can see where customers come from.' },
    ],
    questions: [
      { q: 'Can you help with Google reviews?', a: 'We can help you set up a simple way to ask happy customers for reviews. We never write, buy or fake reviews.' },
      { q: 'We serve several towns. Can you help in each one?', a: 'Yes. We’ll plan how to show up in each area you serve without creating thin, repetitive pages.' },
      { q: 'Our profession has advertising rules. Is that a problem?', a: 'No. We’ll ask you to check anything covered by your profession’s rules before it’s published.' },
    ],
  },

  ecommerce: {
    slug: 'ecommerce',
    description:
      'SEO, content, social media and purchase tracking for online stores, from Outlogik. Understand what sells and where buyers come from.',
    headline: 'More of the right shoppers, and a clear view of what sells.',
    lead:
      'For online stores: product and category pages that can be found, content that brings shoppers in, and analytics that connect it all to sales.',
    challenges: [
      'Product and category pages don’t show up in search.',
      'Visitors arrive, but don’t buy, and it’s not clear why.',
      'Analytics don’t record purchases properly.',
      'Social posts get likes, but not visits to your store.',
    ],
    help: [
      { service: 'seo', text: 'Technical SEO for product and category pages: structure, indexing and speed.' },
      { service: 'website-analytics-reporting', text: 'Purchase and checkout tracking in GA4, so you can see what sells and where buyers come from.' },
      { service: 'content-marketing', text: 'Buying guides and category copy that help shoppers decide.' },
      { service: 'social-media-management', text: 'Product posts and content that send shoppers to your store.' },
    ],
    approach: [
      { title: 'Tracking first', text: 'If purchases aren’t recorded properly, every other decision is guesswork. We check that early.' },
      { title: 'Categories before single products', text: 'Category pages usually reach more searches, so we often start there.' },
      { title: 'Measured in sales', text: 'Reports focus on revenue and purchases, not just visits.' },
    ],
    questions: [
      { q: 'Which e-commerce platforms do you work with?', a: 'Tell us which platform you use in the consultation, and we’ll tell you honestly how we can work with it.' },
      { q: 'Do you manage paid shopping ads?', a: 'Not as part of our services today. Our focus is organic search, social, content and analytics.' },
      { q: 'Can you write product descriptions?', a: 'Yes, as part of content marketing. We agree how many in your proposal.' },
    ],
  },

  'growing-companies': {
    slug: 'growing-companies',
    description:
      'Extra marketing capacity for in-house teams: SEO, content, analytics and social media from Outlogik, fitting in with how you work.',
    headline: 'Extra hands for your marketing team.',
    lead:
      'When your in-house team has more to do than time, we take on the work you can’t get to, and fit in with how you already work.',
    challenges: [
      'A backlog of SEO fixes no one has time for.',
      'Content plans that keep slipping.',
      'Reporting that takes a day each month.',
      'Specialist skills you need some of the time, not full-time.',
    ],
    help: [
      { service: 'seo', text: 'Technical audits and fixes, prioritised, with clear handover to your developers.' },
      { service: 'content-marketing', text: 'Extra writing capacity that follows your brand and style guides.' },
      { service: 'website-analytics-reporting', text: 'Clean tracking and a monthly report your leadership will actually read.' },
      { service: 'social-media-management', text: 'Day-to-day posting and community management, so your team can focus on strategy.' },
    ],
    approach: [
      { title: 'Fit in, don’t take over', text: 'Your team sets direction. We take on agreed work and keep you informed.' },
      { title: 'Clear handovers', text: 'Developers get prioritised instructions; writers get briefs; leaders get summaries.' },
      { title: 'A record of the work', text: 'Your client portal keeps a history of what we’ve done, for anyone on your team.' },
    ],
    questions: [
      { q: 'Can you work in our tools and processes?', a: 'Yes. We use your project tools and approval process where we can, and your client portal keeps a record of our work.' },
      { q: 'Can you follow our brand and style guides?', a: 'Yes. Send them over during onboarding and we’ll work to them.' },
      { q: 'Can you take on a single project?', a: 'Yes, such as an SEO audit or an analytics setup. Tell us about it in the consultation.' },
    ],
  },
};
