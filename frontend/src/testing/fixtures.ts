import { Me, Membership, User } from '../app/core/api.types';

export function membership(over: Partial<Membership> = {}): Membership {
  return {
    organization_id: 'org-1',
    organization_slug: 'acme',
    organization_name: 'Acme',
    organization_status: 'active',
    organization_kind: 'agency',
    workspace_scope: 'all',
    role_id: 'role-1',
    role_name: 'Owner',
    role_key: 'owner',
    permissions: [],
    ...over,
  };
}

export function me(memberships: Membership[] = [membership()], user: Partial<User> = {}): Me {
  return {
    user: {
      id: 'user-1',
      email: 'olive@acme.example.com',
      full_name: 'Olive van Owner',
      is_super_admin: false,
      platform_role: null,
      platform_caps: [],
      email_verified_at: null,
      created_at: '2026-11-14T00:00:00Z',
      ...user,
    },
    memberships,
  };
}
