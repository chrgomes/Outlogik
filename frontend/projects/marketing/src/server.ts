import {
  AngularNodeAppEngine,
  createNodeRequestHandler,
  isMainModule,
  writeResponseToNodeResponse,
} from '@angular/ssr/node';
import express from 'express';
import { join } from 'node:path';

/**
 * The marketing site's Node server: serves static files, proxies /api/public/* to the API,
 * and renders pages. Settings come from the environment:
 *   PORT               port to listen on (default 4000)
 *   API_INTERNAL_URL   where the API is reachable from this server (default http://localhost:8000)
 */
const browserDistFolder = join(import.meta.dirname, '../browser');
const API_INTERNAL_URL = (process.env['API_INTERNAL_URL'] ?? 'http://localhost:8000').replace(/\/$/, '');

const app = express();
const angularApp = new AngularNodeAppEngine();
app.disable('x-powered-by');

// Security headers for every response. The Content-Security-Policy is added with analytics and
// consent in step 12, once the full list of allowed sources is known.
app.use((_req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), interest-cohort=()');
  next();
});

/**
 * Same-origin proxy to the public API, so the browser never talks to the API host directly.
 * Read-only for now; form submissions (POST) are added with the forms in step 6.
 */
app.get('/api/public/{*path}', async (req, res) => {
  const upstream = API_INTERNAL_URL + req.originalUrl.replace('/api/public/', '/api/v1/public/');
  try {
    const response = await fetch(upstream, {
      headers: { accept: 'application/json', 'x-forwarded-for': req.ip ?? '' },
      signal: AbortSignal.timeout(5000),
    });
    res.status(response.status);
    for (const header of ['content-type', 'cache-control']) {
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
    .then((response) => (response ? writeResponseToNodeResponse(response, res) : next()))
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
