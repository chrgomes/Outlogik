import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { routes } from '../app.routes';
import { AUDIENCES, DEFAULT_SETTINGS, SERVICES, SITE_URL } from '../config/site';
import { SERVICE_CONTENT } from '../config/services-content';
import { answerSite, settle, visit } from '../../testing/marketing';
import { Seo } from './seo';
import { robotsTxt, sitemapPaths, sitemapXml } from './sitemap';

const head = () => document.head;
const meta = (key: string) =>
  head().querySelector(`meta[name="${key}"], meta[property="${key}"]`)?.getAttribute('content') ?? null;
const canonical = () => head().querySelector('link[rel="canonical"]')?.getAttribute('href') ?? null;
const graph = (): Record<string, unknown>[] => {
  const script = head().querySelector('script#ol-jsonld');
  return script ? JSON.parse(script.textContent!)['@graph'] : [];
};
const types = () => graph().map((g) => g['@type']);

async function go(url: string) {
  await TestBed.inject(Router).navigateByUrl(url);
  await settle();
  TestBed.tick();
}

describe('Search and sharing metadata', () => {
  it('describes the homepage, the organization and the website', async () => {
    await visit('/');
    expect(document.title).toBe('Outlogik · Digital marketing agency');
    expect(canonical()).toBe(`${SITE_URL}/`);
    expect(meta('description')).toBe(DEFAULT_SETTINGS.seo_default_description);
    expect(meta('og:title')).toBe('Outlogik · Digital marketing agency');
    expect(meta('og:url')).toBe(`${SITE_URL}/`);
    expect(meta('og:image')).toBe(`${SITE_URL}/images/og-default.png`);
    expect(meta('twitter:card')).toBe('summary_large_image');
    expect(meta('robots')).toBeNull();
    expect(types()).toEqual(expect.arrayContaining(['Organization', 'WebSite']));
    const org = graph().find((g) => g['@type'] === 'Organization')!;
    expect(org).toMatchObject({ name: 'Outlogik', url: `${SITE_URL}/`, logo: `${SITE_URL}/images/outlogik-logo-512.png` });
  });

  it('gives service pages their description, breadcrumbs and service details', async () => {
    await visit('/services/seo');
    const content = SERVICE_CONTENT['seo'];
    expect(document.title).toBe('SEO services · Outlogik');
    expect(canonical()).toBe(`${SITE_URL}/services/seo`);
    expect(meta('description')).toBe(content.description);
    expect(meta('og:description')).toBe(content.description);
    expect(types()).toEqual(expect.arrayContaining(['Organization', 'BreadcrumbList', 'Service']));
    const crumbs = graph().find((g) => g['@type'] === 'BreadcrumbList')!['itemListElement'] as { name: string; item: string }[];
    expect(crumbs.map((c) => [c.name, c.item])).toEqual([
      ['Home', `${SITE_URL}/`], ['Services', `${SITE_URL}/services`], ['SEO', `${SITE_URL}/services/seo`],
    ]);
    expect(graph().find((g) => g['@type'] === 'Service')).toMatchObject({
      name: 'SEO', url: `${SITE_URL}/services/seo`, provider: { '@id': `${SITE_URL}/#organization` },
    });
  });

  it('clears page-specific data when moving to another page', async () => {
    await visit('/services/seo');
    await go('/pricing');
    expect(canonical()).toBe(`${SITE_URL}/pricing`);
    expect(types()).not.toContain('Service');
    expect(types()).toContain('BreadcrumbList');
    expect(meta('description')).not.toBe(SERVICE_CONTENT['seo'].description);
  });

  it('leaves query strings out of the canonical URL', async () => {
    await visit('/book-a-consultation?service=seo&utm_source=x');
    expect(canonical()).toBe(`${SITE_URL}/book-a-consultation`);
  });

  it('keeps error pages and newsletter links out of search results', async () => {
    await visit('/does-not-exist');
    expect(meta('robots')).toBe('noindex');
    expect(canonical()).toBeNull();
    expect(document.title).toBe('Page not found · Outlogik');

    await go('/newsletter/confirm?token=abc');
    expect(meta('robots')).toBe('noindex');
    expect(canonical()).toBeNull();
  });

  it('uses the title ending and default description from the site settings', async () => {
    await visit('/about');
    answerSite({ settings: { ...DEFAULT_SETTINGS, seo_title_suffix: ' | Outlogik Agency', seo_default_description: 'x' } });
    await settle();
    TestBed.tick();
    expect(document.title).toBe('About | Outlogik Agency');
  });

  it('escapes structured data so it can never close its script element', async () => {
    await visit('/');
    TestBed.inject(Seo).add('test', { '@type': 'Thing', name: '</script><script>alert(1)</script>' });
    TestBed.tick();
    const text = head().querySelector('script#ol-jsonld')!.textContent!;
    expect(text).not.toContain('</script>');
    expect(graph().find((g) => g['@type'] === 'Thing')!['name']).toBe('</script><script>alert(1)</script>');
  });
});

describe('Sitemap and robots.txt', () => {
  it('lists every public page from the routes, and nothing else', () => {
    const paths = sitemapPaths(routes);
    for (const p of ['/', '/services', '/who-we-help', '/how-we-work', '/pricing', '/about', '/contact', '/book-a-consultation']) {
      expect(paths).toContain(p);
    }
    for (const s of SERVICES) expect(paths).toContain(`/services/${s.slug}`);
    for (const a of AUDIENCES) expect(paths).toContain(`/who-we-help/${a.slug}`);
    expect(paths.some((p) => p.includes('newsletter') || p.includes('*'))).toBe(false);
    const xml = sitemapXml('https://example.com', ['/', '/a&b']);
    expect(xml).toContain('<loc>https://example.com/</loc>');
    expect(xml).toContain('<loc>https://example.com/a&amp;b</loc>');
  });

  it('points to the sitemap, and blocks everything on staging', () => {
    expect(robotsTxt('https://example.com', false)).toContain('Sitemap: https://example.com/sitemap.xml');
    expect(robotsTxt('https://example.com', false)).toContain('Disallow: /newsletter/');
    expect(robotsTxt('https://example.com', true)).toBe('User-agent: *\nDisallow: /\n');
  });
});
