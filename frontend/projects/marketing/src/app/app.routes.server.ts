import { RenderMode, ServerRoute } from '@angular/ssr';

/**
 * Pages are rendered on the server for each request, then cached briefly by the browser and
 * any cache in front of the site. Content managed in the admin area (module statuses, settings)
 * therefore shows up within about a minute, without rebuilding the site.
 */
const CACHED = {
  'Cache-Control': 'public, max-age=0, s-maxage=60, stale-while-revalidate=300',
};

export const serverRoutes: ServerRoute[] = [
  { path: '', renderMode: RenderMode.Server, headers: CACHED },
  { path: '**', renderMode: RenderMode.Server, status: 404, headers: { 'Cache-Control': 'no-store' } },
];
