import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

/** Shapes from /api/v1/admin (Outlogik site admins only). */

export type LeadStatus = 'new' | 'contacted' | 'qualified' | 'closed' | 'spam';
export type LeadKind = 'consultation' | 'contact';

export interface LeadListItem {
  id: string;
  kind: LeadKind;
  status: LeadStatus;
  name: string;
  email: string;
  company: string | null;
  services: string[];
  utm_source: string | null;
  note_count: number;
  created_at: string;
}

export interface LeadNote {
  id: string;
  body: string;
  author_name: string | null;
  created_at: string;
}

export interface Lead {
  id: string;
  kind: LeadKind;
  status: LeadStatus;
  name: string;
  email: string;
  company: string | null;
  website: string | null;
  phone: string | null;
  message: string | null;
  details: { services?: string[]; budget?: string | null; preferred_contact?: string | null; topic?: string };
  attribution: Partial<Record<'page' | 'landing_page' | 'referrer' | 'utm_source' | 'utm_medium'
    | 'utm_campaign' | 'utm_term' | 'utm_content', string>>;
  spam_reason: string | null;
  created_at: string;
  updated_at: string;
  notes: LeadNote[];
}

export type LeadCounts = Record<LeadStatus, number>;

export interface Subscriber {
  id: string;
  email: string;
  status: 'pending' | 'confirmed' | 'unsubscribed';
  consent_at: string;
  confirmed_at: string | null;
  unsubscribed_at: string | null;
  source_page: string | null;
}

export interface SocialLink {
  network: string;
  url: string;
}

export interface SiteSettings {
  company_description: string;
  tagline: string;
  contact_email: string | null;
  sales_email: string | null;
  phone: string | null;
  address: string | null;
  social_links: SocialLink[];
  consultation_cta_label: string;
  seo_title_suffix: string;
  seo_default_description: string;
  legal_name: string | null;
  province: string | null;
  privacy_email: string | null;
  ga4_measurement_id: string | null;
  gtm_container_id: string | null;
  clarity_project_id: string | null;
}

export interface LeadSource {
  source: string;
  consultations: number;
  messages: number;
  newsletter: number;
}

export interface PortalFeature {
  slug: string;
  name: string;
  summary: string;
  status: 'available' | 'in_development' | 'hidden';
  sort_order: number;
}

/** Labels for the values the website's forms send (see the marketing site's config/forms.ts). */
export const LEAD_STATUSES: { value: LeadStatus; label: string }[] = [
  { value: 'new', label: 'New' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'qualified', label: 'Qualified' },
  { value: 'closed', label: 'Closed' },
  { value: 'spam', label: 'Spam' },
];
export const KIND_LABELS: Record<LeadKind, string> = { consultation: 'Consultation', contact: 'Message' };
export const SERVICE_LABELS: Record<string, string> = {
  seo: 'SEO', 'social-media-management': 'Social Media Management',
  'website-analytics-reporting': 'Website Analytics & Reporting',
  'content-marketing': 'Content Marketing', 'not-sure': 'Not sure yet',
};
export const BUDGET_LABELS: Record<string, string> = {
  'under-1k': 'Under $1,000 a month', '1k-2.5k': '$1,000 to $2,500 a month',
  '2.5k-5k': '$2,500 to $5,000 a month', '5k-plus': 'Over $5,000 a month', 'not-sure': 'Not sure yet',
};
export const TOPIC_LABELS: Record<string, string> = {
  general: 'General question', 'existing-client': 'Existing client',
  partnerships: 'Partnerships', press: 'Press',
};

export const ADMIN_API = '/api/v1/admin';

/** Writes to the admin API. Lists and details are read with httpResource in the pages. */
@Injectable({ providedIn: 'root' })
export class AdminApi {
  private readonly http = inject(HttpClient);

  private send<T>(method: 'POST' | 'PATCH' | 'PUT' | 'DELETE', path: string, body?: unknown): Promise<T> {
    return firstValueFrom(this.http.request<T>(method, `${ADMIN_API}/${path}`, { body: body ?? {} }));
  }

  setLeadStatus(id: string, status: LeadStatus): Promise<Lead> {
    return this.send('PATCH', `leads/${id}`, { status });
  }

  addNote(id: string, body: string): Promise<Lead> {
    return this.send('POST', `leads/${id}/notes`, { body });
  }

  deleteLead(id: string): Promise<void> {
    return this.send('DELETE', `leads/${id}`);
  }

  deleteSubscriber(id: string): Promise<void> {
    return this.send('DELETE', `newsletter/subscribers/${id}`);
  }

  saveSettings(data: SiteSettings): Promise<{ data: SiteSettings; updated_at: string }> {
    return this.send('PUT', 'site/settings', data);
  }

  updateFeature(slug: string, change: Partial<PortalFeature>): Promise<PortalFeature> {
    return this.send('PATCH', `site/portal-features/${slug}`, change);
  }
}

/** For the governing law in the website's terms (must match the API's list). */
export const PROVINCES = [
  'Alberta', 'British Columbia', 'Manitoba', 'New Brunswick', 'Newfoundland and Labrador',
  'Northwest Territories', 'Nova Scotia', 'Nunavut', 'Ontario', 'Prince Edward Island', 'Quebec',
  'Saskatchewan', 'Yukon',
];
