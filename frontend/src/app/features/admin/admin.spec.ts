import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, provideRouter, Router, RouterStateSnapshot, UrlTree } from '@angular/router';

import { me, membership } from '../../../testing/fixtures';
import { flushPending, page } from '../../../testing/org-setup';
import { AuthService } from '../../core/auth.service';
import { CurrentOrgService } from '../../core/current-org.service';
import { homeRedirect, siteAdminGuard } from '../../core/guards';
import { Sidebar } from '../../layout/sidebar/sidebar';
import { Topbar } from '../../layout/topbar/topbar';
import { LeadDetail } from './lead-detail';
import { LeadsList } from './leads-list';
import { PortalFeatures } from './portal-features';
import { SiteSettingsPage } from './site-settings';

function setup(role: 'site_admin' | 'content_editor' | null = 'site_admin', memberships = [membership()]) {
  TestBed.configureTestingModule({
    providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
  });
  TestBed.inject(AuthService).me.set(me(memberships, { platform_role: role }));
  return TestBed.inject(HttpTestingController);
}

const lead = {
  id: 'l1', kind: 'consultation', status: 'new', name: 'Casey Client', email: 'casey@example.com',
  company: 'Harbour Bakery', website: 'harbourbakery.example.com', phone: null,
  message: 'More local customers, please.',
  details: { services: ['seo', 'content-marketing'], budget: '1k-2.5k', preferred_contact: 'Mornings' },
  attribution: { page: '/book-a-consultation', landing_page: '/?utm_source=linkedin', utm_source: 'linkedin', utm_campaign: 'launch' },
  spam_reason: null, created_at: '2026-11-15T10:00:00Z', updated_at: '2026-11-15T10:00:00Z', notes: [],
};

describe('Website admin access', () => {
  const run = <T>(fn: () => T) => TestBed.runInInjectionContext(fn);
  const url = (tree: unknown) => TestBed.inject(Router).serializeUrl(tree as UrlTree);
  /** Runs a guard, answering its /me request with the user set up by setup(). */
  async function check(fn: () => unknown) {
    const user = TestBed.inject(AuthService).me();
    const result = run(fn);
    TestBed.inject(HttpTestingController).expectOne('/api/v1/auth/me').flush(user);
    return result;
  }
  const guard = () => check(() => siteAdminGuard({} as ActivatedRouteSnapshot, { url: '/admin' } as RouterStateSnapshot));

  it('lets site admins in and switches the app to the admin area', async () => {
    setup('site_admin');
    expect(await guard()).toBe(true);
    expect(TestBed.inject(CurrentOrgService).area()).toBe('admin');
  });

  it.each([null, 'content_editor'] as const)('shows "not found" to everyone else (%s)', async (role) => {
    setup(role);
    expect(url(await guard())).toBe('/not-found');
    expect(TestBed.inject(CurrentOrgService).area()).toBe('org');
  });

  it('sends staff with no organization to the admin area', async () => {
    setup('site_admin', []);
    const tree = await check(() => homeRedirect({} as ActivatedRouteSnapshot, { url: '/' } as RouterStateSnapshot));
    expect(url(tree)).toBe('/admin');
  });

  it('shows the admin navigation in the sidebar', () => {
    setup();
    TestBed.inject(CurrentOrgService).area.set('admin');
    const fixture = TestBed.createComponent(Sidebar);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    const links = [...el.querySelectorAll('nav a')].map((a) => [a.textContent!.trim(), a.getAttribute('href')]);
    expect(links).toEqual([
      ['Inbox', '/admin/leads'], ['Newsletter', '/admin/newsletter'],
      ['Settings', '/admin/settings'], ['Portal features', '/admin/portal-features'],
    ]);
    expect(el.textContent).toContain('Website admin');
  });

  it('offers the admin area in the workspace menu to site admins only', () => {
    for (const role of ['site_admin', null] as const) {
      TestBed.resetTestingModule();
      setup(role);
      TestBed.inject(CurrentOrgService).slug.set('acme');
      const fixture = TestBed.createComponent(Topbar);
      fixture.detectChanges();
      (fixture.nativeElement.querySelector('.org-switcher') as HTMLButtonElement).click();
      fixture.detectChanges();
      const items = [...document.querySelectorAll('.ol-menu [role="menuitemradio"]')].map((i) => i.textContent!.trim());
      expect(items.some((t) => t.includes('Website admin'))).toBe(role === 'site_admin');
      fixture.destroy();
    }
  });
});

describe('Leads inbox', () => {
  it('lists leads and exports with the same filters', async () => {
    const http = setup();
    const fixture = TestBed.createComponent(LeadsList);
    fixture.detectChanges();
    await flushPending();
    http.expectOne('/api/v1/admin/leads/counts').flush({ new: 1, contacted: 0, qualified: 0, closed: 0, spam: 2 });
    http.expectOne('/api/v1/admin/leads/sources').flush([
      { source: 'linkedin', consultations: 2, messages: 0, newsletter: 1 },
    ]);
    const req = http.expectOne((r) => r.url === '/api/v1/admin/leads');
    expect(req.request.params.has('status')).toBe(false);
    req.flush(page([{ ...lead, services: lead.details.services, utm_source: 'linkedin', note_count: 2 }]));
    await flushPending();
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    const row = el.querySelector('tbody tr')!;
    expect(row.querySelector('a')!.getAttribute('href')).toBe('/l1');
    expect(row.textContent).toContain('SEO, Content Marketing');
    expect(row.textContent).toContain('linkedin');
    expect(row.textContent).toContain('2 notes');
    expect(el.querySelector('select option[value="spam"]')!.textContent).toContain('Spam (2)');
    const sources = el.querySelector('[aria-labelledby="sources-title"] tbody tr')!;
    expect([...sources.querySelectorAll('td')].map((td) => td.textContent!.trim())).toEqual(['linkedin', '2', '0', '1']);

    const status = el.querySelector<HTMLSelectElement>('select[aria-label="Status"]')!;
    status.value = 'new';
    status.dispatchEvent(new Event('change'));
    await flushPending();
    fixture.detectChanges();
    expect(el.querySelector('a[download]')!.getAttribute('href')).toBe('/api/v1/admin/leads/export.csv?status=new');
    expect(http.expectOne((r) => r.url === '/api/v1/admin/leads').request.params.get('status')).toBe('new');
  });

  it('explains an empty inbox', async () => {
    const http = setup();
    const fixture = TestBed.createComponent(LeadsList);
    fixture.detectChanges();
    await flushPending();
    http.expectOne('/api/v1/admin/leads/counts').flush({});
    http.expectOne('/api/v1/admin/leads/sources').flush([]);
    http.expectOne((r) => r.url === '/api/v1/admin/leads').flush(page([]));
    await flushPending();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('No leads yet');
  });
});

describe('Lead detail', () => {
  async function render() {
    const http = setup();
    const fixture = TestBed.createComponent(LeadDetail);
    fixture.componentRef.setInput('leadId', 'l1');
    fixture.detectChanges();
    await flushPending();
    http.expectOne('/api/v1/admin/leads/l1').flush(lead);
    await flushPending();
    fixture.detectChanges();
    return { http, fixture, el: fixture.nativeElement as HTMLElement };
  }

  it('shows the request, contact details and where they came from', async () => {
    const { el } = await render();
    expect(el.querySelector('h1')!.textContent).toContain('Casey Client');
    for (const text of ['SEO, Content Marketing', '$1,000 to $2,500 a month', 'Mornings',
      'More local customers', '/?utm_source=linkedin', 'source: linkedin · campaign: launch']) {
      expect(el.textContent).toContain(text);
    }
    expect(el.querySelector('a[target="_blank"]')!.getAttribute('href')).toBe('https://harbourbakery.example.com');
    expect(el.querySelector('a.btn-primary')!.getAttribute('href')).toContain('mailto:casey@example.com?subject=');
  });

  it('changes the status and adds notes', async () => {
    const { http, fixture, el } = await render();
    const select = el.querySelector<HTMLSelectElement>('#lead-status')!;
    select.value = 'contacted';
    select.dispatchEvent(new Event('change'));
    const patch = http.expectOne('/api/v1/admin/leads/l1');
    expect(patch.request.method).toBe('PATCH');
    expect(patch.request.body).toEqual({ status: 'contacted' });
    patch.flush({ ...lead, status: 'contacted' });
    await flushPending();

    const note = el.querySelector<HTMLTextAreaElement>('#note')!;
    note.value = 'Called; booked for Tuesday.';
    note.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    el.querySelector<HTMLFormElement>('form')!.dispatchEvent(new Event('submit'));
    const post = http.expectOne('/api/v1/admin/leads/l1/notes');
    expect(post.request.body).toEqual({ body: 'Called; booked for Tuesday.' });
    post.flush({ ...lead, status: 'contacted', notes: [
      { id: 'n1', body: 'Called; booked for Tuesday.', author_name: 'Ada Admin', created_at: '2026-11-15T11:00:00Z' }] });
    await flushPending();
    fixture.detectChanges();
    expect(el.querySelector('.note')!.textContent).toContain('Ada Admin');
    expect(note.value).toBe('');
  });
});

describe('Website settings', () => {
  it('saves empty contact fields as "not shown"', async () => {
    const http = setup();
    const fixture = TestBed.createComponent(SiteSettingsPage);
    fixture.detectChanges();
    await flushPending();
    http.expectOne('/api/v1/admin/site/settings').flush({ updated_at: '2026-11-15T00:00:00Z', data: {
      company_description: 'An agency.', tagline: 'Digital Marketing. Smarter. Together.',
      contact_email: 'hello@example.com', sales_email: null, phone: null, address: null,
      social_links: [{ network: 'linkedin', url: 'https://linkedin.com/company/x' }],
      consultation_cta_label: 'Book a free consultation', seo_title_suffix: ' · Outlogik',
      seo_default_description: 'Default.',
      legal_name: null, province: null, privacy_email: null,
      ga4_measurement_id: null, gtm_container_id: null, clarity_project_id: null,
    } });
    await flushPending();
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    const email = el.querySelector<HTMLInputElement>('#s-email')!;
    expect(email.value).toBe('hello@example.com');
    email.value = '';
    email.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    el.querySelector<HTMLFormElement>('form')!.dispatchEvent(new Event('submit'));
    const put = http.expectOne('/api/v1/admin/site/settings');
    expect(put.request.method).toBe('PUT');
    expect(put.request.body).toMatchObject({
      contact_email: null, phone: null, ga4_measurement_id: null,
      social_links: [{ network: 'linkedin', url: 'https://linkedin.com/company/x' }],
    });
  });
});

describe('Portal features', () => {
  it('changes how a feature is shown on the website', async () => {
    const http = setup();
    const fixture = TestBed.createComponent(PortalFeatures);
    fixture.detectChanges();
    await flushPending();
    http.expectOne('/api/v1/admin/site/portal-features').flush([
      { slug: 'monthly-reports', name: 'Monthly reports', summary: 's', status: 'in_development', sort_order: 1 },
    ]);
    await flushPending();
    fixture.detectChanges();
    const select = fixture.nativeElement.querySelector('select') as HTMLSelectElement;
    expect(select.value).toBe('in_development');
    select.value = 'available';
    select.dispatchEvent(new Event('change'));
    const req = http.expectOne('/api/v1/admin/site/portal-features/monthly-reports');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ status: 'available' });
  });
});

describe('Website settings: analytics', () => {
  it('checks the format of analytics IDs before saving', async () => {
    const http = setup();
    const fixture = TestBed.createComponent(SiteSettingsPage);
    fixture.detectChanges();
    await flushPending();
    http.expectOne('/api/v1/admin/site/settings').flush({ updated_at: '2026-11-15T00:00:00Z', data: {
      company_description: 'An agency.', tagline: 'Tagline', contact_email: null, sales_email: null,
      phone: null, address: null, social_links: [], consultation_cta_label: 'Book', seo_title_suffix: '',
      seo_default_description: '', legal_name: null, province: null, privacy_email: null,
      ga4_measurement_id: null, gtm_container_id: null, clarity_project_id: null,
    } });
    await flushPending();
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    const ga4 = el.querySelector<HTMLInputElement>('#s-ga4')!;
    ga4.value = 'UA-1234-5';
    ga4.dispatchEvent(new Event('input'));
    el.querySelector<HTMLFormElement>('form')!.dispatchEvent(new Event('submit'));
    fixture.detectChanges();
    http.expectNone('/api/v1/admin/site/settings');
    expect(el.textContent).toContain('Check the format');

    ga4.value = 'G-ABC123XYZ';
    ga4.dispatchEvent(new Event('input'));
    el.querySelector<HTMLFormElement>('form')!.dispatchEvent(new Event('submit'));
    expect(http.expectOne('/api/v1/admin/site/settings').request.body.ga4_measurement_id).toBe('G-ABC123XYZ');
  });
});

describe('Website settings: legal details', () => {
  it('says whether the legal pages are published, and saves the details', async () => {
    const http = setup();
    const fixture = TestBed.createComponent(SiteSettingsPage);
    fixture.detectChanges();
    await flushPending();
    http.expectOne('/api/v1/admin/site/settings').flush({ updated_at: '2026-11-16T00:00:00Z', data: {
      company_description: 'An agency.', tagline: 'Tagline', contact_email: null, sales_email: null,
      phone: null, address: '1 Example Street', social_links: [], consultation_cta_label: 'Book',
      seo_title_suffix: '', seo_default_description: '', legal_name: null, province: null,
      privacy_email: null, ga4_measurement_id: null, gtm_container_id: null, clarity_project_id: null,
    } });
    await flushPending();
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Not complete: the privacy policy and terms are not published yet.');
    const set = (sel: string, value: string, event = 'input') => {
      const input = el.querySelector<HTMLInputElement | HTMLSelectElement>(sel)!;
      input.value = value;
      input.dispatchEvent(new Event(event));
    };
    set('#s-legal-name', 'Outlogik Inc.');
    set('#s-province', 'Ontario', 'change');
    set('#s-privacy', 'privacy@outlogik.example.com');
    el.querySelector<HTMLFormElement>('form')!.dispatchEvent(new Event('submit'));
    const put = http.expectOne('/api/v1/admin/site/settings');
    expect(put.request.body).toMatchObject({
      legal_name: 'Outlogik Inc.', province: 'Ontario', privacy_email: 'privacy@outlogik.example.com',
    });
    put.flush({ updated_at: '2026-11-16T00:01:00Z', data: put.request.body });
    await flushPending();
    fixture.detectChanges();
    expect(el.textContent).toContain('Complete: the privacy policy and terms are published.');
  });
});
