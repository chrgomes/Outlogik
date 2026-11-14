import { IconName } from '../shared/icon/icons';

export interface NavItem {
  label: string;
  icon: IconName;
  /** Path below /o/:orgSlug */
  path: string;
  permission: string;
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
      { label: 'Clients', icon: 'briefcase', path: 'clients', permission: 'clients.read' },
      { label: 'Websites', icon: 'globe2', path: 'websites', permission: 'websites.read' },
    ],
  },
  {
    label: 'Settings',
    items: [
      { label: 'Organization', icon: 'building', path: 'settings/organization',
        permission: 'organization.update' },
      { label: 'Team', icon: 'people', path: 'settings/members', permission: 'members.read' },
      { label: 'Roles', icon: 'shield-lock', path: 'settings/roles', permission: 'roles.read' },
    ],
  },
];
