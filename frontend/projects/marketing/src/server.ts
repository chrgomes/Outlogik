import {
  AngularNodeAppEngine,
  createNodeRequestHandler,
  isMainModule,
  writeResponseToNodeResponse,
} from '@angular/ssr/node';
import express from 'express';
import { randomBytes } from 'node:crypto';
import { join } from 'node:path';

import { routes } from './app/app.routes';
import { SiteSettings, legalReady } from './app/config/site';
import { robotsTxt, sitemapPaths, sitemapXml } from './app/seo/sitemap';
import { addNonce, contentSecurityPolicy } from './csp';

/**
 * The marketing site's Node server: serves static files, proxies /api/public/* to the API,
 * and renders pages. Settings come from the environment:
 *   PORT               port to listen on (default 4000)
 *   API_INTERNAL_URL   where the API is reachable from this server (default http://localhost:8000)
 *   SITE_NOINDEX       set to "true" on staging sites: robots.txt blocks everything and every
 *                      response says noindex, so staging never appears in search results.
 *   TRUST_PROXY        set when a reverse proxy (e.g. Caddy or nginx) sits in front of this
 *                      server, so visitors' real IP addresses reach the API's rate limits. Takes
 *                      Express's "trust proxy" values: a hop count ("1"), or addresses.
 */
const browserDistFolder = join(import.meta.dirname, '../browser');
const API_INTERNAL_URL = (process.env['API_INTERNAL_URL'] ?? 'http://localhost:8000').replace(/\/$/, '');

const SITE_URL = OL_SITE_URL.replace(/\/$/, '');
const NOINDEX = process.env['SITE_NOINDEX'] === 'true';

const app = express();
const angularApp = new AngularNodeAppEngine();
app.disable('x-powered-by');
const trustProxy = process.env['TRUST_PROXY'];
if (trustProxy) app.set('trust proxy', /^\d+$/.test(trustProxy) ? Number(trustProxy) : trustProxy);

// Security headers for every response. Pages also get a Content-Security-Policy (below).
app.use((_req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), interest-cohort=()');
  if (NOINDEX) res.setHeader('X-Robots-Tag', 'noindex, nofollow');
  next();
});

/** Search engines: robots.txt and a sitemap built from the page routes (spec §13). */
app.get('/robots.txt', (_req, res) => {
  res.type('text/plain').setHeader('Cache-Control', 'public, max-age=3600');
  res.send(robotsTxt(SITE_URL, NOINDEX));
});
// The legal pages are listed only once they're published (their details are set in the admin
// area), so the sitemap checks the site settings, at most every five minutes.
let legalCheck = { at: 0, published: false };
async function legalPublished(): Promise<boolean> {
  if (Date.now() - legalCheck.at < 5 * 60_000) return legalCheck.published;
  try {
    const res = await fetch(`${API_INTERNAL_URL}/api/v1/public/site`, { signal: AbortSignal.timeout(3000) });
    const body = (await res.json()) as { settings: SiteSettings };
    legalCheck = { at: Date.now(), published: res.ok && legalReady(body.settings) };
  } catch {
    legalCheck = { at: Date.now(), published: false };
  }
  return legalCheck.published;
}
app.get('/sitemap.xml', async (_req, res) => {
  const paths = sitemapPaths(routes, { legalPublished: await legalPublished() });
  res.type('application/xml').setHeader('Cache-Control', 'public, max-age=3600');
  res.send(sitemapXml(SITE_URL, paths));
});

/**
 * Addresses from the earlier, software-product version of the plan, and /login, which takes
 * people to the client portal. Permanent redirects keep any old links and search results working.
 */
const REDIRECTS: [RegExp, string][] = [
  [/^\/platform(\/.*)?$/, '/services'],
  [/^\/solutions(\/.*)?$/, '/who-we-help'],
  [/^\/(book-a-demo|get-started)\/?$/, '/book-a-consultation'],
];
app.get('/{*path}', (req, res, next) => {
  if (req.path === '/login' || req.path === '/login/') {
    return res.redirect(302, `${OL_APP_URL.replace(/\/$/, '')}/login`);
  }
  const match = REDIRECTS.find(([pattern]) => pattern.test(req.path));
  if (!match) return next();
  const query = req.originalUrl.slice(req.path.length);
  res.redirect(301, match[1] + query);
});

/**
 * Same-origin proxy to the public API, so the browser never talks to the API host directly:
 * reads (settings) and the website's forms. The browser's Origin is passed on, because the API
 * only accepts form posts from this site.
 */
app.all('/api/public/{*path}', express.raw({ type: 'application/json', limit: '32kb' }), async (req, res) => {
  if (req.method !== 'GET' && req.method !== 'POST') {
    res.status(405).json({ error: { code: 'method_not_allowed', message: 'Method not allowed.', details: null } });
    return;
  }
  const upstream = API_INTERNAL_URL + req.originalUrl.replace('/api/public/', '/api/v1/public/');
  const headers: Record<string, string> = { accept: 'application/json', 'x-forwarded-for': req.ip ?? '' };
  for (const name of ['origin', 'user-agent', 'content-type']) {
    const value = req.headers[name];
    if (typeof value === 'string') headers[name] = value;
  }
  try {
    const response = await fetch(upstream, {
      method: req.method,
      headers,
      body: req.method === 'POST' && Buffer.isBuffer(req.body) ? new Uint8Array(req.body) : undefined,
      signal: AbortSignal.timeout(10000),
    });
    res.status(response.status);
    for (const header of ['content-type', 'cache-control', 'retry-after']) {
      const value = response.headers.get(header);
      if (value) res.setHeader(header, value);
    }
    res.send(Buffer.from(await response.arrayBuffer()));
  } catch {
    res.status(502).json({ error: { code: 'upstream_unavailable', message: 'Please try again shortly.', details: null } });
  }
});

/** Static files (hashed bundles can be cached for a year). */
app.use(
  express.static(browserDistFolder, {
    maxAge: '1y',
    index: false,
    redirect: false,
  }),
);

/** Everything else is rendered by Angular. */
app.use((req, res, next) => {
  angularApp
    .handle(req)
    .then(async (response) => {
      if (!response) return next();
      if (!response.headers.get('content-type')?.includes('text/html')) {
        return writeResponseToNodeResponse(response, res);
      }
      const nonce = randomBytes(16).toString('base64');
      const html = addNonce(await response.text(), nonce);
      res.status(response.status);
      response.headers.forEach((value, name) => {
        if (name !== 'content-length') res.setHeader(name, value);
      });
      res.setHeader('Content-Security-Policy', contentSecurityPolicy(nonce));
      res.send(html);
    })
    .catch(next);
});

if (isMainModule(import.meta.url) || process.env['pm_id']) {
  const port = process.env['PORT'] || 4000;
  app.listen(port, (error) => {
    if (error) {
      throw error;
    }
    console.log(`Outlogik marketing site listening on http://localhost:${port}`);
  });
}

/** Request handler used by the Angular CLI (dev server and build). */
export const reqHandler = createNodeRequestHandler(app);
