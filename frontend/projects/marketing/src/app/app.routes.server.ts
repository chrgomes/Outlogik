import { RenderMode, ServerRoute } from '@angular/ssr';

import { SERVICES } from './config/site';

/**
 * Pages are rendered on the server for each request, then cached briefly by the browser and
 * any cache in front of the site. Content managed in the admin area (portal feature statuses, settings)
 * therefore shows up within about a minute, without rebuilding the site.
 */
const CACHED = {
  'Cache-Control': 'public, max-age=0, s-maxage=60, stale-while-revalidate=300',
};

export const serverRoutes: ServerRoute[] = [
  { path: '', renderMode: RenderMode.Server, headers: CACHED },
  { path: 'services', renderMode: RenderMode.Server, headers: CACHED },
  // Listed one by one so an unknown /services/... address still gets a 404 status.
  ...SERVICES.map((s): ServerRoute => ({ path: `services/${s.slug}`, renderMode: RenderMode.Server, headers: CACHED })),
  { path: '**', renderMode: RenderMode.Server, status: 404, headers: { 'Cache-Control': 'no-store' } },
];
