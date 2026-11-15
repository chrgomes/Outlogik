import { Routes } from '@angular/router';

import { SERVICES } from './config/site';
import { Home } from './pages/home/home';
import { NotFound } from './pages/not-found/not-found';

/** Page titles follow "<page> · Outlogik"; the homepage uses the brand line. */
export const routes: Routes = [
  { path: '', component: Home, title: 'Outlogik · Digital marketing agency' },
  {
    path: 'services',
    title: 'Services · Outlogik',
    loadComponent: () => import('./pages/services/services-overview').then((m) => m.ServicesOverview),
  },
  // One route per service; any other /services/... address falls through to the 404 page.
  ...SERVICES.map((s) => ({
    path: `services/${s.slug}`,
    title: `${s.pageTitle} · Outlogik`,
    data: { slug: s.slug },
    loadComponent: () => import('./pages/services/service-page').then((m) => m.ServicePage),
  })),
  { path: '**', component: NotFound, title: 'Page not found · Outlogik' },
];
