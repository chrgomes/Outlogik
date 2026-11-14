import { Routes } from '@angular/router';

import { ComingSoon } from './features/placeholder/coming-soon';
import { NoAccess, NoOrganization, NotFound } from './features/system/system-pages';
import { authGuard, guestGuard, homeRedirect, orgGuard, permissionGuard } from './core/guards';
import { CenteredLayout } from './layout/centered/centered';
import { Shell } from './layout/shell/shell';

const page = (title: string, step: number, permission: string, extra: object = {}) => ({
  component: ComingSoon,
  canActivate: [permissionGuard],
  title: `${title} · Outlogik`,
  data: { title, step, permission, ...extra },
});

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
      { path: 'dashboard', ...page('Dashboard', 10, 'dashboard.read', { icon: 'grid-1x2',
        description: 'An overview of your clients, websites and team.' }) },
      { path: 'clients', ...page('Clients', 9, 'clients.read', { icon: 'briefcase' }) },
      { path: 'websites', ...page('Websites', 9, 'websites.read', { icon: 'globe2' }) },
      { path: 'settings/organization',
        ...page('Organization', 9, 'organization.update', { icon: 'building' }) },
      { path: 'settings/members', ...page('Team', 9, 'members.read', { icon: 'people' }) },
      { path: 'settings/roles', ...page('Roles', 9, 'roles.read', { icon: 'shield-lock' }) },
      { path: 'no-access', component: NoAccess, title: 'No access · Outlogik' },
    ],
  },
  { path: '**', redirectTo: 'not-found' },
];
