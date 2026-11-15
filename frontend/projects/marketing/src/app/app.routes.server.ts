import { RenderMode, ServerRoute } from '@angular/ssr';

import { routes } from './app.routes';

/**
 * Pages are rendered on the server for each request, then cached briefly by the browser and
 * any cache in front of the site. Content managed in the admin area (portal feature statuses,
 * settings) therefore shows up within about a minute, without rebuilding the site.
 *
 * Every page is listed by its exact path (taken from app.routes.ts), so an unknown address such
 * as /services/paid-ads falls through to the last entry and gets a 404 status.
 */
const CACHED = {
  'Cache-Control': 'public, max-age=0, s-maxage=60, stale-while-revalidate=300',
};

export const serverRoutes: ServerRoute[] = [
  ...routes
    .filter((r) => r.path !== '**')
    .map((r): ServerRoute => ({ path: r.path!, renderMode: RenderMode.Server, headers: CACHED })),
  { path: '**', renderMode: RenderMode.Server, status: 404, headers: { 'Cache-Control': 'no-store' } },
];
