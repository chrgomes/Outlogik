import { Me, Membership } from '../app/core/api.types';

export function membership(over: Partial<Membership> = {}): Membership {
  return {
    organization_id: 'org-1',
    organization_slug: 'acme',
    organization_name: 'Acme',
    organization_status: 'active',
    role_id: 'role-1',
    role_name: 'Owner',
    permissions: [],
    ...over,
  };
}

export function me(memberships: Membership[] = [membership()]): Me {
  return {
    user: {
      id: 'user-1',
      email: 'olive@acme.example.com',
      full_name: 'Olive van Owner',
      is_super_admin: false,
      email_verified_at: null,
      created_at: '2026-11-14T00:00:00Z',
    },
    memberships,
  };
}
