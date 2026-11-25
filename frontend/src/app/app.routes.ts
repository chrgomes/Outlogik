import { Routes } from '@angular/router';

import { NoAccess, NoOrganization, NotFound } from './features/system/system-pages';
import {
  agencyGuard, authGuard, businessGuard, guestGuard, homeRedirect, orgGuard, permissionGuard, staffGuard,
  adminHomeRedirect,
  platformGuard,
  staffAreaGuard,
  websiteAdminGuard,
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
      {
        // From a business's email: accept access to its workspace into one of your agencies.
        path: 'agency-access',
        canActivate: [authGuard],
        title: 'Accept agency access · Outlogik',
        loadComponent: () => import('./features/access/accept-access').then((m) => m.AcceptAccess),
      },
      { path: 'not-found', component: NotFound, title: 'Not found · Outlogik' },
      {
        path: 'suspended/:orgSlug',
        canActivate: [authGuard],
        title: 'Suspended · Outlogik',
        loadComponent: () => import('./features/system/suspended').then((m) => m.SuspendedPage),
      },
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
        canActivate: [agencyGuard, permissionGuard, staffGuard],
        data: { permission: 'clients.read' },
        title: 'Clients · Outlogik',
        loadComponent: () => import('./features/clients/clients-list').then((m) => m.ClientsList),
      },
      {
        path: 'clients/:clientId',
        canActivate: [agencyGuard, permissionGuard, staffGuard],
        data: { permission: 'clients.read' },
        title: 'Client · Outlogik',
        loadComponent: () => import('./features/clients/client-detail').then((m) => m.ClientDetail),
      },
      {
        path: 'websites',
        canActivate: [permissionGuard, staffGuard],
        data: { permission: 'websites.read' },
        title: 'Websites · Outlogik',
        loadComponent: () => import('./features/websites/websites-list').then((m) => m.WebsitesList),
      },
      {
        path: 'settings/organization',
        canActivate: [permissionGuard, staffGuard],
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
      {
        path: 'audits',
        canActivate: [permissionGuard],
        data: { permission: 'audits.read' },
        title: 'Audits · Outlogik',
        loadComponent: () => import('./features/audits/audits-list').then((m) => m.AuditsList),
      },
      {
        path: 'reports',
        canActivate: [permissionGuard],
        data: { permission: 'reports.read' },
        title: 'Reports · Outlogik',
        loadComponent: () => import('./features/reports/reports-list').then((m) => m.ReportsList),
      },
      {
        path: 'integrations',
        canActivate: [permissionGuard],
        data: { permission: 'integrations.read' },
        title: 'Integrations · Outlogik',
        loadComponent: () => import('./features/integrations/integrations').then((m) => m.IntegrationsPage),
      },
      {
        path: 'audits/:workspaceId/:auditId',
        canActivate: [permissionGuard],
        data: { permission: 'audits.read' },
        title: 'Audit · Outlogik',
        loadComponent: () => import('./features/audits/audit-detail').then((m) => m.AuditDetailPage),
      },
      {
        path: 'settings/plan',
        canActivate: [permissionGuard],
        data: { permission: 'plan.read' },
        title: 'Plan · Outlogik',
        loadComponent: () => import('./features/settings/plan').then((m) => m.Plan),
      },
      {
        path: 'settings/agency-access',
        canActivate: [businessGuard, permissionGuard],
        data: { permission: 'access_grants.manage' },
        title: 'Agency access · Outlogik',
        loadComponent: () => import('./features/access/agency-access').then((m) => m.AgencyAccess),
      },
      {
        path: 'settings/linked-businesses',
        canActivate: [agencyGuard, permissionGuard],
        data: { permission: 'linked_accounts.manage' },
        title: 'Linked businesses · Outlogik',
        loadComponent: () =>
          import('./features/access/linked-businesses').then((m) => m.LinkedBusinesses),
      },
      {
        path: 'account',
        title: 'Your account · Outlogik',
        loadComponent: () => import('./features/account/account').then((m) => m.AccountPage),
      },
      { path: 'no-access', component: NoAccess, title: 'No access · Outlogik' },
    ],
  },
  {
    // Outlogik staff: the platform (Super Admin) area, and the website admin (site admins).
    path: 'admin',
    component: Shell,
    canActivate: [staffAreaGuard],
    children: [
      { path: '', pathMatch: 'full', canActivate: [adminHomeRedirect], children: [] },
      {
        path: 'platform',
        canActivate: [platformGuard],
        title: 'Overview · Platform · Outlogik',
        loadComponent: () => import('./features/platform/overview').then((m) => m.PlatformOverview),
      },
      {
        path: 'platform/organizations',
        canActivate: [platformGuard],
        title: 'Organizations · Platform · Outlogik',
        loadComponent: () => import('./features/platform/organizations').then((m) => m.PlatformOrganizations),
      },
      {
        path: 'platform/organizations/:orgId',
        canActivate: [platformGuard],
        title: 'Organization · Platform · Outlogik',
        loadComponent: () => import('./features/platform/organization').then((m) => m.PlatformOrganization),
      },
      {
        path: 'platform/users',
        canActivate: [platformGuard],
        title: 'Users · Platform · Outlogik',
        loadComponent: () => import('./features/platform/users').then((m) => m.PlatformUsers),
      },
      {
        path: 'platform/users/:userId',
        canActivate: [platformGuard],
        title: 'User · Platform · Outlogik',
        loadComponent: () => import('./features/platform/user').then((m) => m.PlatformUser),
      },
      {
        path: 'platform/codes',
        canActivate: [platformGuard],
        data: { cap: 'signup_codes.manage' },
        title: 'Invitation codes · Platform · Outlogik',
        loadComponent: () => import('./features/platform/codes').then((m) => m.PlatformCodes),
      },
      {
        path: 'leads',
        canActivate: [websiteAdminGuard],
        title: 'Leads · Website admin · Outlogik',
        loadComponent: () => import('./features/admin/leads-list').then((m) => m.LeadsList),
      },
      {
        path: 'leads/:leadId',
        canActivate: [websiteAdminGuard],
        title: 'Lead · Website admin · Outlogik',
        loadComponent: () => import('./features/admin/lead-detail').then((m) => m.LeadDetail),
      },
      {
        path: 'newsletter',
        canActivate: [websiteAdminGuard],
        title: 'Newsletter · Website admin · Outlogik',
        loadComponent: () => import('./features/admin/subscribers').then((m) => m.Subscribers),
      },
      {
        path: 'settings',
        canActivate: [websiteAdminGuard],
        title: 'Website settings · Website admin · Outlogik',
        loadComponent: () => import('./features/admin/site-settings').then((m) => m.SiteSettingsPage),
      },
      {
        path: 'portal-features',
        canActivate: [websiteAdminGuard],
        title: 'Portal features · Website admin · Outlogik',
        loadComponent: () => import('./features/admin/portal-features').then((m) => m.PortalFeatures),
      },
    ],
  },
  { path: '**', redirectTo: 'not-found' },
];
