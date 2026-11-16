import { Routes } from '@angular/router';

/**
 * Paths for sitemap.xml: every page in the route table except the 404 page, pages marked noindex
 * (the newsletter links), and the legal pages until they're published. Built from the routes, so
 * new pages are included automatically.
 */
export function sitemapPaths(routes: Routes, { legalPublished = false } = {}): string[] {
  return routes
    .filter((r) => r.path !== undefined && r.path !== '**' && !r.redirectTo && r.data?.['noindex'] !== true)
    .filter((r) => legalPublished || r.data?.['legal'] !== true)
    .map((r) => '/' + r.path);
}

const escapeXml = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

export function sitemapXml(siteUrl: string, paths: string[]): string {
  const urls = paths.map((p) => `  <url><loc>${escapeXml(siteUrl + p)}</loc></url>`).join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`;
}

/**
 * robots.txt. With `noindex` (a staging site), everything is blocked so it never appears in
 * search results.
 */
export function robotsTxt(siteUrl: string, noindex: boolean): string {
  if (noindex) return 'User-agent: *\nDisallow: /\n';
  return [
    'User-agent: *',
    'Allow: /',
    'Disallow: /api/',
    'Disallow: /newsletter/',
    '',
    `Sitemap: ${siteUrl}/sitemap.xml`,
    '',
  ].join('\n');
}
