import { TestBed } from '@angular/core/testing';
import { Title } from '@angular/platform-browser';

import { serverRoutes } from '../app.routes.server';
import { AUDIENCE_CONTENT } from '../config/audiences-content';
import { AUDIENCES, DEFAULT_PORTAL_FEATURES, SERVICES } from '../config/site';
import { FORBIDDEN_CLAIMS, visit } from '../../testing/marketing';

/** Step 5: Who we help, How we work, Pricing, About. */
describe('Who we help', () => {
  it('lists the four business types', async () => {
    const el = await visit('/who-we-help');
    expect(el.querySelectorAll('h1')).toHaveLength(1);
    const hrefs = [...el.querySelectorAll('.mk-card')].map((a) => a.getAttribute('href'));
    expect(hrefs).toEqual(AUDIENCES.map((a) => `/who-we-help/${a.slug}`));
  });

  for (const a of AUDIENCES) {
    describe(a.name, () => {
      const content = AUDIENCE_CONTENT[a.slug];

      it('has one h1, the challenges, how each service helps, questions and the CTA', async () => {
        const el = await visit(`/who-we-help/${a.slug}`);
        expect(el.querySelectorAll('h1')).toHaveLength(1);
        expect(el.querySelector('h1')!.textContent!.trim()).toBe(content.headline);
        expect(el.querySelectorAll('.mk-challenges li')).toHaveLength(content.challenges.length);
        const services = [...el.querySelectorAll('#how-we-help .mk-card')].map((c) => c.getAttribute('href'));
        expect(services).toEqual(content.help.map((h) => `/services/${h.service}`));
        expect(el.querySelectorAll('.mk-faq summary')).toHaveLength(content.questions.length);
        expect(el.querySelectorAll('a[href="/book-a-consultation"]').length).toBeGreaterThanOrEqual(2);
        expect(TestBed.inject(Title).getTitle()).toBe(`${a.pageTitle} · Outlogik`);
      });

      it('links to the other business types, not itself', async () => {
        const el = await visit(`/who-we-help/${a.slug}`);
        const hrefs = [...el.querySelectorAll('.mk-link-row a')].map((l) => l.getAttribute('href'));
        expect(hrefs).toHaveLength(AUDIENCES.length - 1);
        expect(hrefs).not.toContain(`/who-we-help/${a.slug}`);
      });

      it('only recommends real services, and makes no guarantees', () => {
        for (const h of content.help) expect(SERVICES.map((s) => s.slug)).toContain(h.service);
        expect(JSON.stringify(content).toLowerCase()).not.toMatch(FORBIDDEN_CLAIMS);
      });
    });
  }
});

describe('How we work', () => {
  it('explains the four steps', async () => {
    const el = await visit('/how-we-work');
    expect(el.querySelectorAll('h1')).toHaveLength(1);
    expect([...el.querySelectorAll('.mk-process h3')].map((h) => h.textContent)).toEqual(
      ['Free consultation', 'A clear proposal', 'Onboarding', 'Monthly work and reporting']);
  });

  it('labels every portal feature with its status from the admin area', async () => {
    const el = await visit('/how-we-work', [
      { slug: 'client-portal', name: 'Client portal', summary: 'a', status: 'available' },
      { slug: 'monthly-reports', name: 'Monthly reports', summary: 'b', status: 'in_development' },
    ]);
    expect([...el.querySelectorAll('.mk-features .mk-badge')].map((b) => b.textContent)).toEqual(
      ['Available', 'In development']);
  });

  it('shows the default features and two real screenshots without the API', async () => {
    const el = await visit('/how-we-work');
    expect(el.querySelectorAll('.mk-features li')).toHaveLength(DEFAULT_PORTAL_FEATURES.length);
    const shots = [...el.querySelectorAll('img')];
    expect(shots).toHaveLength(2);
    for (const img of shots) expect(img.getAttribute('alt')).toBeTruthy();
  });
});

describe('Pricing', () => {
  it('explains how pricing works, without publishing prices', async () => {
    const el = await visit('/pricing');
    expect(el.querySelectorAll('h1')).toHaveLength(1);
    expect(el.textContent).not.toMatch(/\$\s?\d|€\s?\d|£\s?\d|per month|\/mo\b/i);
    expect(el.querySelectorAll('.mk-faq summary').length).toBeGreaterThanOrEqual(4);
    expect(el.querySelectorAll('a[href="/book-a-consultation"]').length).toBeGreaterThanOrEqual(2);
  });
});

describe('About', () => {
  it('describes the approach, with no invented team, history or proof', async () => {
    const el = await visit('/about');
    expect(el.querySelectorAll('h1')).toHaveLength(1);
    const text = el.textContent!.toLowerCase();
    expect(text).not.toMatch(FORBIDDEN_CLAIMS);
    expect(text).not.toMatch(/founded in|since \d{4}|our team of|years of experience|clients served/);
    expect(el.querySelectorAll('.mk-point')).toHaveLength(4);
  });
});

describe('Server routes', () => {
  it('lists every page so only unknown addresses get a 404 status', () => {
    const paths = serverRoutes.map((r) => r.path);
    for (const p of ['', 'services', 'who-we-help', 'how-we-work', 'pricing', 'about']) expect(paths).toContain(p);
    for (const a of AUDIENCES) expect(paths).toContain(`who-we-help/${a.slug}`);
    expect(paths.filter((p) => p!.includes(':'))).toEqual([]);
    expect(serverRoutes.at(-1)).toMatchObject({ path: '**', status: 404 });
  });
});
