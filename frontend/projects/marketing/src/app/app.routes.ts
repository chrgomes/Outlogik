import { Routes } from '@angular/router';

import { AUDIENCES, SERVICES } from './config/site';
import { Home } from './pages/home/home';
import { NotFound } from './pages/not-found/not-found';

/**
 * Page titles follow "<page> · Outlogik"; the homepage uses the brand line. Pages other than the
 * homepage load on demand. Any address not listed here, such as /services/paid-ads, gets the 404
 * page (and app.routes.server.ts gives it a 404 status).
 */
export const routes: Routes = [
  { path: '', component: Home, title: 'Outlogik · Digital marketing agency' },
  {
    path: 'services',
    title: 'Services · Outlogik',
    loadComponent: () => import('./pages/services/services-overview').then((m) => m.ServicesOverview),
  },
  ...SERVICES.map((s) => ({
    path: `services/${s.slug}`,
    title: `${s.pageTitle} · Outlogik`,
    data: { slug: s.slug },
    loadComponent: () => import('./pages/services/service-page').then((m) => m.ServicePage),
  })),
  {
    path: 'who-we-help',
    title: 'Who we help · Outlogik',
    loadComponent: () => import('./pages/who-we-help/who-we-help').then((m) => m.WhoWeHelp),
  },
  ...AUDIENCES.map((a) => ({
    path: `who-we-help/${a.slug}`,
    title: `${a.pageTitle} · Outlogik`,
    data: { slug: a.slug },
    loadComponent: () => import('./pages/who-we-help/audience-page').then((m) => m.AudiencePage),
  })),
  {
    path: 'how-we-work',
    title: 'How we work · Outlogik',
    loadComponent: () => import('./pages/how-we-work/how-we-work').then((m) => m.HowWeWork),
  },
  {
    path: 'pricing',
    title: 'Pricing · Outlogik',
    loadComponent: () => import('./pages/pricing/pricing').then((m) => m.Pricing),
  },
  {
    path: 'about',
    title: 'About · Outlogik',
    loadComponent: () => import('./pages/about/about').then((m) => m.About),
  },
  {
    path: 'book-a-consultation',
    title: 'Book a free consultation · Outlogik',
    loadComponent: () => import('./pages/book-a-consultation/book-a-consultation').then((m) => m.BookAConsultation),
  },
  {
    path: 'contact',
    title: 'Contact · Outlogik',
    loadComponent: () => import('./pages/contact/contact').then((m) => m.Contact),
  },
  // Linked from newsletter emails only; not indexed.
  ...(['confirm', 'unsubscribe'] as const).map((action) => ({
    path: `newsletter/${action}`,
    title: `${action === 'confirm' ? 'Confirm your subscription' : 'Unsubscribe'} · Outlogik`,
    data: { action },
    loadComponent: () => import('./pages/newsletter/newsletter-link').then((m) => m.NewsletterLink),
  })),
  { path: '**', component: NotFound, title: 'Page not found · Outlogik' },
];
