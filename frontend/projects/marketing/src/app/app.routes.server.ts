import { RenderMode, ServerRoute } from '@angular/ssr';

/**
 * How each route is rendered on the server.
 * - Prerender: turned into static HTML at build time (marketing pages).
 * - Server: rendered per request (CMS content in milestone B, and the 404 page).
 */
export const serverRoutes: ServerRoute[] = [
  { path: '', renderMode: RenderMode.Prerender },
  { path: '**', renderMode: RenderMode.Server, status: 404 },
];
