/**
 * Choices offered on the website's forms. The API accepts exactly these values; keep them in
 * step with backend/app/modules/leads/schemas.py and service.py (a backend test checks this).
 */

export interface Option {
  value: string;
  label: string;
}

export const SERVICE_OPTIONS: Option[] = [
  { value: 'seo', label: 'SEO' },
  { value: 'social-media-management', label: 'Social Media Management' },
  { value: 'website-analytics-reporting', label: 'Website Analytics & Reporting' },
  { value: 'content-marketing', label: 'Content Marketing' },
  { value: 'not-sure', label: 'Not sure yet' },
];

/** Optional budget range (plan revision 2, decision E). */
export const BUDGET_OPTIONS: Option[] = [
  { value: 'under-1k', label: 'Under $1,000 a month' },
  { value: '1k-2.5k', label: '$1,000 to $2,500 a month' },
  { value: '2.5k-5k', label: '$2,500 to $5,000 a month' },
  { value: '5k-plus', label: 'Over $5,000 a month' },
  { value: 'not-sure', label: 'Not sure yet' },
];

export const CONTACT_TOPICS: Option[] = [
  { value: 'general', label: 'General question' },
  { value: 'existing-client', label: 'I’m an existing client' },
  { value: 'partnerships', label: 'Partnerships' },
  { value: 'press', label: 'Press' },
];

/** Shown beside the newsletter checkbox and stored as the consent record (CASL). */
export const NEWSLETTER_CONSENT_TEXT =
  "Yes, email me Outlogik's newsletter with marketing tips and news about our services. " +
  'I can unsubscribe at any time.';
