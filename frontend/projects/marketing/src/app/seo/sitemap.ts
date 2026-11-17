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
 * Crawlers that collect pages to train AI models: blocked (decided 2026-11-17). Search engines
 * and the AI *search* tools that cite and link to the site (OAI-SearchBot, ChatGPT-User,
 * PerplexityBot, Perplexity-User, Claude-SearchBot, Claude-User) stay allowed, under "*".
 * Google-Extended and Applebot-Extended only control AI training; Google and Apple search are
 * unaffected.
 */
export const AI_TRAINING_CRAWLERS = [
  'GPTBot', // OpenAI
  'ClaudeBot', // Anthropic
  'anthropic-ai', // Anthropic (older name)
  'Google-Extended', // Google Gemini training
  'Applebot-Extended', // Apple AI training
  'meta-externalagent', // Meta AI
  'FacebookBot', // Meta (language models)
  'CCBot', // Common Crawl, widely used for training
  'Bytespider', // ByteDance
  'cohere-training-data-crawler', // Cohere
  'Diffbot',
];

/**
 * robots.txt. With `noindex` (a staging site), everything is blocked so it never appears in
 * search results.
 */
export function robotsTxt(siteUrl: string, noindex: boolean): string {
  if (noindex) return 'User-agent: *\nDisallow: /\n';
  return [
    '# Search engines and AI search tools are welcome.',
    'User-agent: *',
    'Allow: /',
    'Disallow: /api/',
    'Disallow: /newsletter/',
    '',
    '# Crawlers that collect content to train AI models are not.',
    ...AI_TRAINING_CRAWLERS.map((bot) => `User-agent: ${bot}`),
    'Disallow: /',
    '',
    `Sitemap: ${siteUrl}/sitemap.xml`,
    '',
  ].join('\n');
}
