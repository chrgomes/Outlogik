import { IconName } from '@brand/icon/icons';

export interface NavItem {
  label: string;
  icon: IconName;
  /** Path below /o/:orgSlug */
  path: string;
  permission: string;
  /** Shown to one account type only (businesses have no clients; agencies share nothing). */
  agencyOnly?: boolean;
  businessOnly?: boolean;
  /** Not in the client portal: clients see their own dashboard, audits and reports (§7). */
  staffOnly?: boolean;
}

export interface NavSection {
  label?: string;
  items: NavItem[];
}

/** Sidebar navigation. Items the user lacks the permission for are hidden. */
export const NAV: NavSection[] = [
  {
    items: [
      { label: 'Dashboard', icon: 'grid-1x2', path: 'dashboard', permission: 'dashboard.read' },
      { label: 'Clients', icon: 'briefcase', path: 'clients', permission: 'clients.read',
        agencyOnly: true, staffOnly: true },
      { label: 'Websites', icon: 'globe2', path: 'websites', permission: 'websites.read',
        staffOnly: true },
      { label: 'Audits', icon: 'heart-pulse', path: 'audits', permission: 'audits.read' },
      { label: 'Reports', icon: 'file-earmark-bar-graph', path: 'reports', permission: 'reports.read' },
      { label: 'Integrations', icon: 'plug', path: 'integrations', permission: 'integrations.read' },
    ],
  },
  {
    label: 'Settings',
    items: [
      { label: 'Organization', icon: 'building', path: 'settings/organization',
        permission: 'organization.read', staffOnly: true },
      { label: 'Team', icon: 'people', path: 'settings/members', permission: 'members.read' },
      { label: 'Roles', icon: 'shield-lock', path: 'settings/roles', permission: 'roles.read' },
      { label: 'Plan', icon: 'speedometer2', path: 'settings/plan', permission: 'plan.read' },
      { label: 'Agency access', icon: 'people', path: 'settings/agency-access',
        permission: 'access_grants.manage', businessOnly: true },
      { label: 'Linked businesses', icon: 'link-45deg', path: 'settings/linked-businesses',
        permission: 'linked_accounts.manage', agencyOnly: true },
    ],
  },
];

export interface AdminNavItem {
  label: string;
  icon: IconName;
  /** Path below /admin */
  path: string;
  /** Platform capability needed; without one, the item is for site admins (the website). */
  cap?: string;
}

/** Sidebar navigation in the staff area (/admin): the platform, then the website. */
export const ADMIN_NAV: { label?: string; items: AdminNavItem[] }[] = [
  {
    label: 'Platform',
    items: [
      { label: 'Overview', icon: 'speedometer2', path: 'platform', cap: 'platform.read' },
      { label: 'Organizations', icon: 'building', path: 'platform/organizations', cap: 'platform.read' },
      { label: 'Users', icon: 'people', path: 'platform/users', cap: 'platform.read' },
      { label: 'Invitation codes', icon: 'envelope', path: 'platform/codes', cap: 'signup_codes.manage' },
    ],
  },
  {
    label: 'Leads',
    items: [
      { label: 'Inbox', icon: 'inbox', path: 'leads' },
      { label: 'Newsletter', icon: 'envelope', path: 'newsletter' },
    ],
  },
  {
    label: 'Website',
    items: [
      { label: 'Settings', icon: 'sliders', path: 'settings' },
      { label: 'Portal features', icon: 'window-stack', path: 'portal-features' },
    ],
  },
];
