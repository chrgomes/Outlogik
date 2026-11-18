/** Shapes returned by the Outlogik API (mirrors backend schemas). */

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_super_admin: boolean;
  /** Outlogik staff role for the website admin area (super admins report 'site_admin'). */
  platform_role: 'content_editor' | 'site_admin' | null;
  email_verified_at: string | null;
  created_at: string;
}

/** business: markets itself (one workspace, no clients). agency: also works for clients. */
export type AccountType = 'business' | 'agency';

export interface Membership {
  organization_id: string;
  organization_slug: string;
  organization_name: string;
  organization_status: string;
  organization_kind: AccountType;
  role_id: string;
  role_name: string;
  /** Built-in role key ('owner', 'admin', 'member', 'client'), or null for custom roles. */
  role_key: string | null;
  permissions: string[];
}

export interface Me {
  user: User;
  memberships: Membership[];
}

export interface ApiError {
  error: { code: string; message: string; details: unknown };
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface InvitePreview {
  email: string;
  organization_name: string;
  organization_slug: string;
  role_name: string;
  client_name: string | null;
  invited_by: string | null;
  account_exists: boolean;
  expires_at: string;
}

export interface Client {
  id: string;
  name: string;
  contact_email: string | null;
  status: 'active' | 'archived';
  notes: string | null;
  website_count: number;
  portal_user_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface ClientUser {
  user_id: string;
  member_id: string;
  email: string;
  full_name: string;
  linked_at: string;
}

/**
 * Where marketing data lives: the organization's own workspace, or one per agency client.
 */
export interface Workspace {
  id: string;
  kind: 'own' | 'client';
  name: string;
  client_id: string | null;
  client_status: 'active' | 'archived' | null;
  website_count: number;
  created_at: string;
}

export interface Website {
  id: string;
  workspace_id: string;
  workspace_name: string;
  /** Null for websites in the organization's own workspace. */
  client_id: string | null;
  client_name: string | null;
  name: string;
  url: string;
  domain: string;
  status: 'active' | 'paused' | 'archived';
  created_at: string;
  updated_at: string;
}

export interface RoleRef {
  id: string;
  name: string;
  system_key: string | null;
}

export interface Member {
  id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: RoleRef;
  status: 'active' | 'disabled';
  joined_at: string;
  is_you: boolean;
}

export interface Invitation {
  id: string;
  email: string;
  role: RoleRef;
  client_id: string | null;
  client_name: string | null;
  invited_by: string | null;
  status: 'pending' | 'expired';
  expires_at: string;
  created_at: string;
}

export interface Role {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  system_key: string | null;
  permissions: string[];
  member_count: number;
  created_at: string;
}

export interface PermissionInfo {
  code: string;
  description: string;
  group: string;
}

export interface OrganizationDetail {
  id: string;
  name: string;
  slug: string;
  status: string;
  kind: AccountType;
  created_at: string;
  your_role: string;
  your_permissions: string[];
}
