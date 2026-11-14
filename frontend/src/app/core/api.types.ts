/** Shapes returned by the Outlogik API (mirrors backend schemas). */

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_super_admin: boolean;
  email_verified_at: string | null;
  created_at: string;
}

export interface Membership {
  organization_id: string;
  organization_slug: string;
  organization_name: string;
  organization_status: string;
  role_id: string;
  role_name: string;
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
