import { IconName } from '@brand/icon/icons';

/**
 * Site-wide content that the header, footer and pages share. In step 2 the module statuses
 * come from the API (managed in the admin area); these are the defaults.
 */

/** Where "Log In" and "Get Started" go. Set per deployment (see env.d.ts). */
export const APP_URL = OL_APP_URL.replace(/\/$/, '');
export const SITE_URL = OL_SITE_URL.replace(/\/$/, '');
export const appLink = (path: '/login' | '/register') => `${APP_URL}${path}`;

export type ModuleStatus = 'available' | 'in-development';

export interface ProductModule {
  slug: string;
  name: string;
  summary: string;
  icon: IconName;
  status: ModuleStatus;
}

/** Spec §5. Only Client Management exists today (Phase 1); the rest are honestly labelled. */
export const MODULES: ProductModule[] = [
  { slug: 'client-management', name: 'Client Management', icon: 'briefcase', status: 'available',
    summary: 'Clients, websites, team roles and client portals in one workspace.' },
  { slug: 'seo-management', name: 'SEO Management', icon: 'search', status: 'in-development',
    summary: 'Technical audits, keywords and search visibility for every site.' },
  { slug: 'website-analytics', name: 'Website Analytics', icon: 'graph-up', status: 'in-development',
    summary: 'Google Analytics 4 and Search Console, side by side.' },
  { slug: 'social-media-management', name: 'Social Media Management', icon: 'megaphone', status: 'in-development',
    summary: 'Plan, schedule and approve posts across your clients’ channels.' },
  { slug: 'content-marketing', name: 'Content Marketing', icon: 'pencil-square', status: 'in-development',
    summary: 'Editorial calendars and keyword-to-content planning.' },
  { slug: 'marketing-analytics', name: 'Marketing Analytics', icon: 'bar-chart-line', status: 'in-development',
    summary: 'Channels, campaigns and conversions in one view.' },
  { slug: 'reporting', name: 'Reporting', icon: 'file-earmark-bar-graph', status: 'in-development',
    summary: 'Clear client reports with PDF and CSV exports.' },
];

export interface Audience {
  slug: string;
  name: string;
  summary: string;
  icon: IconName;
}

/** Spec §6 */
export const AUDIENCES: Audience[] = [
  { slug: 'marketing-agencies', name: 'Marketing agencies', icon: 'building',
    summary: 'Run every client from one workspace.' },
  { slug: 'seo-agencies', name: 'SEO agencies', icon: 'search-heart',
    summary: 'Audits, rankings and reporting, organised by client.' },
  { slug: 'freelancers', name: 'Freelancers and consultants', icon: 'person',
    summary: 'Look established without the overhead.' },
  { slug: 'in-house-marketing-teams', name: 'In-house marketing teams', icon: 'people',
    summary: 'One view across channels and colleagues.' },
  { slug: 'small-businesses', name: 'Small businesses', icon: 'shop',
    summary: 'Understand your website and marketing in plain terms.' },
];

export interface NavLink {
  label: string;
  path: string;
  description?: string;
}

/**
 * Resource sections appear only once they have published content (spec §3: no empty pages).
 * Filled from the CMS in milestone B.
 */
export const RESOURCES: NavLink[] = [];

export const COMPANY: NavLink[] = [
  { label: 'About Outlogik', path: '/about', description: 'What we’re building and why.' },
  { label: 'Contact', path: '/contact', description: 'Questions, partnerships and press.' },
  { label: 'Book a demo', path: '/book-a-demo', description: 'A walkthrough with our team.' },
];

/** Legal pages are published once the business details are provided (decision 12). */
export const LEGAL: NavLink[] = [];

export const TAGLINE = 'Digital Marketing. Smarter. Together.';
export const DESCRIPTION =
  'Outlogik brings client management, SEO, analytics and reporting together in one workspace for agencies and marketing teams.';
