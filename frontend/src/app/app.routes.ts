import { Routes } from '@angular/router';

import { NoAccess, NoOrganization, NotFound } from './features/system/system-pages';
import {
  agencyGuard, authGuard, guestGuard, homeRedirect, orgGuard, permissionGuard, siteAdminGuard,
} from './core/guards';
import { CenteredLayout } from './layout/centered/centered';
import { Shell } from './layout/shell/shell';

export const routes: Routes = [
  { path: '', pathMatch: 'full', canActivate: [homeRedirect], children: [] },
  {
    path: '',
    component: CenteredLayout,
    children: [
      {
        path: 'login',
        canActivate: [guestGuard],
        title: 'Sign in · Outlogik',
        loadComponent: () => import('./features/auth/login').then((m) => m.Login),
      },
      {
        path: 'register',
        canActivate: [guestGuard],
        title: 'Create account · Outlogik',
        loadComponent: () => import('./features/auth/register').then((m) => m.Register),
      },
      {
        path: 'forgot-password',
        title: 'Reset password · Outlogik',
        loadComponent: () =>
          import('./features/auth/forgot-password').then((m) => m.ForgotPassword),
      },
      {
        path: 'reset-password',
        title: 'Choose a new password · Outlogik',
        loadComponent: () =>
          import('./features/auth/reset-password').then((m) => m.ResetPassword),
      },
      {
        path: 'verify-email',
        title: 'Confirm email · Outlogik',
        loadComponent: () => import('./features/auth/verify-email').then((m) => m.VerifyEmail),
      },
      {
        path: 'accept-invite',
        title: 'Accept invitation · Outlogik',
        loadComponent: () => import('./features/auth/accept-invite').then((m) => m.AcceptInvite),
      },
      { path: 'not-found', component: NotFound, title: 'Not found · Outlogik' },
      {
        path: 'no-organization',
        component: NoOrganization,
        canActivate: [authGuard],
        title: 'No organization · Outlogik',
      },
    ],
  },
  {
    path: 'o/:orgSlug',
    component: Shell,
    canActivate: [authGuard, orgGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        canActivate: [permissionGuard],
        data: { permission: 'dashboard.read' },
        title: 'Dashboard · Outlogik',
        loadComponent: () => import('./features/dashboard/dashboard').then((m) => m.Dashboard),
      },
      {
        path: 'clients',
        canActivate: [agencyGuard, permissionGuard],
        data: { permission: 'clients.read' },
        title: 'Clients · Outlogik',
        loadComponent: () => import('./features/clients/clients-list').then((m) => m.ClientsList),
      },
      {
        path: 'clients/:clientId',
        canActivate: [agencyGuard, permissionGuard],
        data: { permission: 'clients.read' },
        title: 'Client · Outlogik',
        loadComponent: () => import('./features/clients/client-detail').then((m) => m.ClientDetail),
      },
      {
        path: 'websites',
        canActivate: [permissionGuard],
        data: { permission: 'websites.read' },
        title: 'Websites · Outlogik',
        loadComponent: () => import('./features/websites/websites-list').then((m) => m.WebsitesList),
      },
      {
        path: 'settings/organization',
        canActivate: [permissionGuard],
        data: { permission: 'organization.read' },
        title: 'Organization · Outlogik',
        loadComponent: () =>
          import('./features/settings/organization-settings').then((m) => m.OrganizationSettings),
      },
      {
        path: 'settings/members',
        canActivate: [permissionGuard],
        data: { permission: 'members.read' },
        title: 'Team · Outlogik',
        loadComponent: () => import('./features/settings/team').then((m) => m.Team),
      },
      {
        path: 'settings/roles',
        canActivate: [permissionGuard],
        data: { permission: 'roles.read' },
        title: 'Roles · Outlogik',
        loadComponent: () => import('./features/settings/roles').then((m) => m.Roles),
      },
      { path: 'no-access', component: NoAccess, title: 'No access · Outlogik' },
    ],
  },
  {
    // Outlogik's website admin: leads, newsletter, website settings (site admins only).
    path: 'admin',
    component: Shell,
    canActivate: [siteAdminGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'leads' },
      {
        path: 'leads',
        title: 'Leads · Website admin · Outlogik',
        loadComponent: () => import('./features/admin/leads-list').then((m) => m.LeadsList),
      },
      {
        path: 'leads/:leadId',
        title: 'Lead · Website admin · Outlogik',
        loadComponent: () => import('./features/admin/lead-detail').then((m) => m.LeadDetail),
      },
      {
        path: 'newsletter',
        title: 'Newsletter · Website admin · Outlogik',
        loadComponent: () => import('./features/admin/subscribers').then((m) => m.Subscribers),
      },
      {
        path: 'settings',
        title: 'Website settings · Website admin · Outlogik',
        loadComponent: () => import('./features/admin/site-settings').then((m) => m.SiteSettingsPage),
      },
      {
        path: 'portal-features',
        title: 'Portal features · Website admin · Outlogik',
        loadComponent: () => import('./features/admin/portal-features').then((m) => m.PortalFeatures),
      },
    ],
  },
  { path: '**', redirectTo: 'not-found' },
];
