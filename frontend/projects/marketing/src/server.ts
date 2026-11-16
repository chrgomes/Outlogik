import {
  AngularNodeAppEngine,
  createNodeRequestHandler,
  isMainModule,
  writeResponseToNodeResponse,
} from '@angular/ssr/node';
import compression from 'compression';
import express from 'express';
import { randomBytes } from 'node:crypto';
import { join } from 'node:path';

import { routes } from './app/app.routes';
import { DEFAULT_SETTINGS, SiteSettings, legalReady } from './app/config/site';
import { robotsTxt, sitemapPaths, sitemapXml } from './app/seo/sitemap';
import { addNonce, contentSecurityPolicy } from './csp';

/**
 * The marketing site's Node server: serves static files, proxies /api/public/* to the API,
 * and renders pages. Settings come from the environment:
 *   PORT               port to listen on (default 4000)
 *   API_INTERNAL_URL   where the API is reachable from this server (default http://localhost:8000)
 *   SITE_NOINDEX       set to "true" on staging sites: robots.txt blocks everything and every
 *                      response says noindex, so staging never appears in search results.
 *   CLIENT_IP_HEADER   a header the hosting platform sets to the visitor's IP, e.g.
 *                      "do-connecting-ip" on DigitalOcean App Platform.
 *   SITE_PROXY_SECRET  shared with the API: forwarded form posts carry the visitor's IP with it,
 *                      so the API's rate limits see real visitors (same value as the API's).
 *   CANONICAL_HOST     the site's main host name (e.g. outlogik.com): requests for any other
 *                      host, such as www.outlogik.com, are redirected to it permanently.
 *   TRUST_PROXY        set when a reverse proxy (e.g. Caddy or nginx) sits in front of this
 *                      server, so visitors' real IP addresses reach the API's rate limits. Takes
 *                      Express's "trust proxy" values: a hop count ("1"), or addresses.
 */
const browserDistFolder = join(import.meta.dirname, '../browser');
const API_INTERNAL_URL = (process.env['API_INTERNAL_URL'] ?? 'http://localhost:8000').replace(/\/$/, '');

const SITE_URL = OL_SITE_URL.replace(/\/$/, '');
const CLIENT_IP_HEADER = process.env['CLIENT_IP_HEADER']?.toLowerCase();
const SITE_PROXY_SECRET = process.env['SITE_PROXY_SECRET'];
const CANONICAL_HOST = process.env['CANONICAL_HOST']?.toLowerCase();

/** The visitor's IP: the platform's header if configured, otherwise Express's view. */
function visitorIp(req: express.Request): string {
  const header = CLIENT_IP_HEADER ? req.headers[CLIENT_IP_HEADER] : undefined;
  const value = Array.isArray(header) ? header[0] : header;
  return (value?.split(',')[0].trim() || req.ip || '').slice(0, 64);
}
const NOINDEX = process.env['SITE_NOINDEX'] === 'true';

const app = express();
const angularApp = new AngularNodeAppEngine();
app.disable('x-powered-by');
// Compress pages, scripts and styles (about 70% smaller): most of the time to first paint on a
// slow phone connection was spent downloading uncompressed files.
app.use(compression());
const trustProxy = process.env['TRUST_PROXY'];
if (trustProxy) app.set('trust proxy', /^\d+$/.test(trustProxy) ? Number(trustProxy) : trustProxy);

// Security headers for every response. Pages also get a Content-Security-Policy (below).
app.use((_req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), interest-cohort=()');
  // HTTPS only from now on (browsers ignore this over plain HTTP, e.g. local development).
  res.setHeader('Strict-Transport-Security', 'max-age=31536000');
  if (NOINDEX) res.setHeader('X-Robots-Tag', 'noindex, nofollow');
  next();
});

/** Health check for the hosting platform (answered for any host name, never redirected). */
app.get('/healthz', (_req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  res.type('text/plain').send('ok');
});

/** One address for the site: www.outlogik.com (or the platform's own address) → outlogik.com. */
if (CANONICAL_HOST) {
  app.use((req, res, next) => {
    const host = (req.headers.host ?? '').split(':')[0].toLowerCase();
    if (!host || host === CANONICAL_HOST) return next();
    res.redirect(301, `https://${CANONICAL_HOST}${req.originalUrl}`);
  });
}

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
    // Same fallback as the pages themselves: the built-in settings.
    legalCheck = { at: Date.now(), published: legalReady(DEFAULT_SETTINGS) };
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
  const headers: Record<string, string> = { accept: 'application/json', 'x-forwarded-for': visitorIp(req) };
  if (SITE_PROXY_SECRET) {
    headers['x-site-proxy-key'] = SITE_PROXY_SECRET;
    headers['x-site-client-ip'] = visitorIp(req);
  }
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
