import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Title } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { provideIcons } from '@brand/icon/icon';
import { MARKETING_ICONS } from '@brand/icon/icons-marketing';
import { routes } from '../../app.routes';
import { serverRoutes } from '../../app.routes.server';
import { SERVICE_CONTENT } from '../../config/services-content';
import { DEFAULT_SETTINGS, SERVICES } from '../../config/site';

describe('Service pages', () => {
  async function visit(url: string, features?: object[]) {
    TestBed.configureTestingModule({
      providers: [
        provideRouter(routes),
        provideIcons(MARKETING_ICONS),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    const harness = await RouterTestingHarness.create(url);
    if (features) {
      TestBed.inject(HttpTestingController).expectOne('/api/public/site').flush({
        settings: DEFAULT_SETTINGS, portal_features: features, signup_open: false,
      });
      await new Promise((r) => setTimeout(r));
      harness.detectChanges();
    }
    return harness.routeNativeElement as HTMLElement;
  }

  it('lists the four services on /services', async () => {
    const el = await visit('/services');
    expect(el.querySelectorAll('h1')).toHaveLength(1);
    const hrefs = [...el.querySelectorAll('.mk-service-row h2 a')].map((a) => a.getAttribute('href'));
    expect(hrefs).toEqual(SERVICES.map((s) => `/services/${s.slug}`));
    expect(TestBed.inject(Title).getTitle()).toBe('Services · Outlogik');
  });

  for (const s of SERVICES) {
    describe(s.name, () => {
      const content = SERVICE_CONTENT[s.slug];

      it('has one h1, everything included, the FAQ and the consultation CTA', async () => {
        const el = await visit(`/services/${s.slug}`);
        expect(el.querySelectorAll('h1')).toHaveLength(1);
        expect(el.querySelector('h1')!.textContent!.trim()).toBe(content.headline);
        expect(el.querySelectorAll('.mk-included li')).toHaveLength(content.included.length);
        expect(el.querySelectorAll('.mk-faq summary')).toHaveLength(content.questions.length);
        expect(el.querySelectorAll('a[href="/book-a-consultation"]').length).toBeGreaterThanOrEqual(2);
        expect(el.querySelector('[aria-current="page"]')!.textContent).toBe(s.name);
        expect(TestBed.inject(Title).getTitle()).toBe(`${s.pageTitle} · Outlogik`);
      });

      it('links to related services, never to itself', async () => {
        const el = await visit(`/services/${s.slug}`);
        const hrefs = [...el.querySelectorAll('.mk-cards a')].map((a) => a.getAttribute('href'));
        expect(hrefs).toEqual(content.related.map((r) => `/services/${r}`));
        expect(hrefs).not.toContain(`/services/${s.slug}`);
      });

      it('makes no guarantees', () => {
        const text = JSON.stringify(content).toLowerCase();
        expect(text).not.toMatch(/we guarantee|guaranteed|#1|number one|first place|top of google/);
      });
    });
  }

  it('shows only the portal features relevant to the service, with honest labels', async () => {
    const el = await visit('/services/seo', [
      { slug: 'client-portal', name: 'Client portal', summary: 'a', status: 'available' },
      { slug: 'websites-overview', name: 'Websites overview', summary: 'b', status: 'available' },
      { slug: 'seo-health', name: 'SEO health', summary: 'c', status: 'in_development' },
    ]);
    const items = [...el.querySelectorAll('.mk-features li')];
    expect(items.map((li) => li.querySelector('strong')!.textContent)).toEqual(['Websites overview', 'SEO health']);
    expect(items.map((li) => li.querySelector('.mk-badge')?.textContent ?? null)).toEqual([null, 'In development']);
  });

  it('hides the portal section when no relevant feature is shown', async () => {
    const el = await visit('/services/content-marketing', []);
    expect(el.querySelector('#portal-title')).toBeNull();
  });

  it('sends unknown services to the 404 page, with a 404 status on the server', async () => {
    const el = await visit('/services/paid-ads');
    expect(el.querySelector('h1')!.textContent).toContain('couldn’t find');
    const paths = serverRoutes.map((r) => r.path);
    expect(paths).not.toContain('services/:slug');
    for (const s of SERVICES) expect(paths).toContain(`services/${s.slug}`);
  });
});
