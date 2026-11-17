import { Routes } from '@angular/router';

import { AUDIENCES, SERVICES } from './config/site';
import { Home } from './pages/home/home';
import { NotFound } from './pages/not-found/not-found';

/**
 * Route titles are page names; the ending (" · Outlogik") comes from the site settings and is
 * added by SeoTitleStrategy. The homepage has a full title of its own. Pages other than the
 * homepage load on demand. Any address not listed here, such as /services/paid-ads, gets the 404
 * page (and app.routes.server.ts gives it a 404 status).
 */
export const routes: Routes = [
  {
    path: '', component: Home, title: 'Home',
    data: { fullTitle: 'Outlogik · Digital marketing agency' },
  },
  {
    path: 'services',
    title: 'Services',
    loadComponent: () => import('./pages/services/services-overview').then((m) => m.ServicesOverview),
  },
  ...SERVICES.map((s) => ({
    path: `services/${s.slug}`,
    title: s.pageTitle,
    data: { slug: s.slug },
    loadComponent: () => import('./pages/services/service-page').then((m) => m.ServicePage),
  })),
  {
    path: 'who-we-help',
    title: 'Who we help',
    loadComponent: () => import('./pages/who-we-help/who-we-help').then((m) => m.WhoWeHelp),
  },
  ...AUDIENCES.map((a) => ({
    path: `who-we-help/${a.slug}`,
    title: a.pageTitle,
    data: { slug: a.slug },
    loadComponent: () => import('./pages/who-we-help/audience-page').then((m) => m.AudiencePage),
  })),
  {
    path: 'how-we-work',
    title: 'How we work',
    loadComponent: () => import('./pages/how-we-work/how-we-work').then((m) => m.HowWeWork),
  },
  {
    path: 'pricing',
    title: 'Pricing',
    loadComponent: () => import('./pages/pricing/pricing').then((m) => m.Pricing),
  },
  {
    path: 'about',
    title: 'About',
    loadComponent: () => import('./pages/about/about').then((m) => m.About),
  },
  {
    path: 'book-a-consultation',
    title: 'Book a free consultation',
    loadComponent: () => import('./pages/book-a-consultation/book-a-consultation').then((m) => m.BookAConsultation),
  },
  {
    path: 'contact',
    title: 'Contact',
    loadComponent: () => import('./pages/contact/contact').then((m) => m.Contact),
  },
  // Legal pages: published once the legal details are set in the admin area (404 until then).
  {
    path: 'privacy-policy',
    title: 'Privacy policy',
    data: { legal: true },
    loadComponent: () => import('./pages/legal/privacy-policy').then((m) => m.PrivacyPolicy),
  },
  {
    path: 'terms',
    title: 'Terms and conditions',
    data: { legal: true },
    loadComponent: () => import('./pages/legal/terms').then((m) => m.Terms),
  },
  {
    path: 'payment-policy',
    title: 'Payment and subscription policy',
    data: { legal: true },
    loadComponent: () => import('./pages/legal/payment-policy').then((m) => m.PaymentPolicy),
  },
  // Linked from newsletter emails only; not indexed.
  ...(['confirm', 'unsubscribe'] as const).map((action) => ({
    path: `newsletter/${action}`,
    title: action === 'confirm' ? 'Confirm your subscription' : 'Unsubscribe',
    data: { action, noindex: true },
    loadComponent: () => import('./pages/newsletter/newsletter-link').then((m) => m.NewsletterLink),
  })),
  { path: '**', component: NotFound, title: 'Page not found' },
];
