import { IconName } from '@brand/icon/icons';

/**
 * Site-wide content shared by the header, footer and pages. Outlogik is a digital marketing
 * agency (Phase 1.5 plan, revision 2). Settings and client-portal feature statuses come from the
 * API (`SiteData`); the defaults below are used if the API can't be reached.
 */

/** Where "Log in" goes: the client portal (the Outlogik app). Set per deployment (env.d.ts). */
export const APP_URL = OL_APP_URL.replace(/\/$/, '');
export const SITE_URL = OL_SITE_URL.replace(/\/$/, '');
export const LOGIN_URL = `${APP_URL}/login`;

/** The main call to action on every page. */
export const CONSULTATION_PATH = '/book-a-consultation';

export interface Service {
  slug: string;
  name: string;
  short: string;
  summary: string;
  icon: IconName;
  /** The page's <title>, before " · Outlogik". */
  pageTitle: string;
}

/** Services Outlogik offers (decided 2026-11-15). Each has a page under /services. */
export const SERVICES: Service[] = [
  { slug: 'seo', pageTitle: 'SEO services', name: 'SEO', short: 'Search engine optimisation', icon: 'search',
    summary: 'Get found by the people searching for what you offer: technical fixes, keyword research and on-page optimisation.' },
  { slug: 'social-media-management', pageTitle: 'Social media management', name: 'Social Media Management', short: 'Planned, consistent posting', icon: 'megaphone',
    summary: 'Consistent, on-brand posts across your channels, planned ahead and approved by you.' },
  { slug: 'website-analytics-reporting', pageTitle: 'Website analytics and reporting', name: 'Website Analytics & Reporting', short: 'Know what’s working', icon: 'graph-up',
    summary: 'Analytics set up properly, and a monthly report that explains what changed and why.' },
  { slug: 'content-marketing', pageTitle: 'Content marketing', name: 'Content Marketing', short: 'Articles and website copy', icon: 'pencil-square',
    summary: 'Articles and website copy written for your customers first, and for search engines too.' },
];

export interface Audience {
  slug: string;
  name: string;
  summary: string;
  icon: IconName;
}

/** Who we help (plan revision 2, decision B). Each has a page under /who-we-help. */
export const AUDIENCES: Audience[] = [
  { slug: 'small-businesses', name: 'Small businesses', icon: 'shop',
    summary: 'A marketing team without hiring one.' },
  { slug: 'local-businesses', name: 'Local and service businesses', icon: 'building',
    summary: 'Clinics, trades and professional services that need local customers.' },
  { slug: 'ecommerce', name: 'E-commerce', icon: 'window-stack',
    summary: 'Online stores that need more of the right traffic.' },
  { slug: 'growing-companies', name: 'Growing companies', icon: 'people',
    summary: 'Extra hands for in-house teams with more to do than time.' },
];

/** Tools the team works with (decision D). Shown as tools we use, not as product integrations. */
export const TOOLS = [
  'Google Analytics 4', 'Google Search Console', 'Google Business Profile',
  'Bing Webmaster Tools', 'Meta Business Suite', 'LinkedIn',
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
  { label: 'About Outlogik', path: '/about', description: 'Who we are and how we work.' },
  { label: 'Contact', path: '/contact', description: 'Questions, partnerships and press.' },
];

/** Legal pages are published once the business details are provided (decision 12). */
export const LEGAL: NavLink[] = [];

export type FeatureStatus = 'available' | 'in_development';

/** A client-portal capability, with its honest status (managed in the admin area). */
export interface PortalFeature {
  slug: string;
  name: string;
  summary: string;
  status: FeatureStatus;
}

export const DEFAULT_PORTAL_FEATURES: PortalFeature[] = [
  { slug: 'client-portal', name: 'Your own client portal', status: 'available',
    summary: 'A private sign-in for your business, separate from every other client.' },
  { slug: 'websites-overview', name: 'Your websites in one place', status: 'available',
    summary: 'Every website we look after for you, with its status.' },
  { slug: 'activity-history', name: 'A record of the work', status: 'available',
    summary: 'Changes to your account and websites, with who made them and when.' },
  { slug: 'monthly-reports', name: 'Monthly reports', status: 'in_development',
    summary: 'Your monthly results, ready to read online or download as PDF.' },
  { slug: 'analytics-dashboards', name: 'Analytics dashboards', status: 'in_development',
    summary: 'Traffic and search performance from Google Analytics and Search Console.' },
  { slug: 'social-approvals', name: 'Social calendar approvals', status: 'in_development',
    summary: 'Review and approve social posts before they go out.' },
  { slug: 'seo-health', name: 'SEO health checks', status: 'in_development',
    summary: 'Technical issues found on your sites, and when they were fixed.' },
];

/** Mirrors the API's SiteSettingsData. Empty values mean "not shown". */
export interface SiteSettings {
  company_description: string;
  tagline: string;
  contact_email: string | null;
  sales_email: string | null;
  phone: string | null;
  address: string | null;
  social_links: { network: string; url: string }[];
  consultation_cta_label: string;
  seo_title_suffix: string;
  seo_default_description: string;
}

export const DEFAULT_SETTINGS: SiteSettings = {
  company_description:
    'Outlogik is a digital marketing agency for SEO, social media, content and analytics, with a client portal that shows you exactly what we’re doing.',
  tagline: 'Digital Marketing. Smarter. Together.',
  contact_email: null,
  sales_email: null,
  phone: null,
  address: null,
  social_links: [],
  consultation_cta_label: 'Book a free consultation',
  seo_title_suffix: ' · Outlogik',
  seo_default_description:
    'Outlogik is a digital marketing agency: SEO, social media management, content marketing and analytics, with clear reporting in your own client portal.',
};

export const SOCIAL_LABELS: Record<string, string> = {
  linkedin: 'LinkedIn', x: 'X', facebook: 'Facebook', instagram: 'Instagram',
  youtube: 'YouTube', tiktok: 'TikTok', github: 'GitHub',
};
