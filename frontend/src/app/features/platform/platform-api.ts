import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

export const PLATFORM_API = '/api/v1/admin/platform';

export interface Overview {
  users: { total: number; active: number; suspended: number; unverified: number; new_30_days: number };
  organizations: { business: number; agency: number; suspended: number; new_30_days: number };
  subscriptions: { trialing: number; trial_ended: number; active: number; past_due: number; cancelled: number };
  clients_active: number;
  websites_active: number;
  signup_codes_active: number;
  jobs: { queued: number; running: number; failed_24h: number; dead_24h: number; oldest_queued_minutes: number | null };
}

export interface OrgRow {
  id: string; name: string; slug: string; kind: 'business' | 'agency'; status: string;
  plan: string | null; subscription_status: string | null; trial_ends_at: string | null;
  members: number; clients: number; websites: number; created_at: string;
}

export interface AdminAction { action: string; actor: string | null; meta: Record<string, unknown>; created_at: string; }

export interface OrgDetail extends OrgRow {
  suspended_reason: string | null;
  signup_code: string | null;
  billing_interval: string | null;
  limits: { key: string; label: string; limit: number | null; used: number | null }[];
  members_list: { user_id: string; name: string; email: string; role: string; status: string; user_active: boolean }[];
  history: AdminAction[];
}

export interface UserRow {
  id: string; name: string; email: string; active: boolean; verified: boolean;
  staff_role: string | null; super_admin: boolean; organizations: number;
  last_login_at: string | null; created_at: string;
}

export interface UserDetail extends UserRow {
  suspended_reason: string | null;
  memberships: { organization_id: string; organization_name: string; organization_slug: string;
    organization_status: string; role: string; status: string }[];
  history: AdminAction[];
}

export interface SignupCode {
  id: string; label: string; hint: string; account_type: 'business' | 'agency' | null;
  max_uses: number | null; uses: number; expires_at: string | null; revoked_at: string | null;
  status: 'active' | 'used_up' | 'expired' | 'revoked'; created_at: string; created_by: string | null;
}

export interface PlanOption { key: string; name: string; account_kind: string; }

/** Plain words for the audit log's platform actions. */
export function describeAction(a: AdminAction): string {
  const meta = a.meta as Record<string, any>;
  switch (a.action) {
    case 'platform.org_suspend': return `Suspended: ${meta['reason']}`;
    case 'platform.org_reactivate': return 'Reactivated';
    case 'platform.user_suspend': return `Suspended: ${meta['reason']}`;
    case 'platform.user_reactivate': return 'Reactivated';
    case 'subscription.change': {
      const to = meta['to'] ?? {};
      return `Plan set to ${to.plan} (${String(to.status).replace('_', ' ')}, ${to.interval})`
        + (meta['via'] ? ` via ${meta['via']}` : '');
    }
    default: return a.action;
  }
}

/** Changes in the platform area. Lists and details are read with httpResource in the pages. */
@Injectable({ providedIn: 'root' })
export class PlatformApi {
  private readonly http = inject(HttpClient);

  private send<T>(method: 'POST' | 'PUT', path: string, body?: unknown): Promise<T> {
    return firstValueFrom(this.http.request<T>(method, `${PLATFORM_API}/${path}`, { body: body ?? {} }));
  }

  assignPlan(orgId: string, body: { plan: string; status: string; interval: string; trial_days: number | null }) {
    return this.send<OrgDetail>('PUT', `organizations/${orgId}/plan`, body);
  }
  suspendOrg(orgId: string, reason: string) {
    return this.send<OrgDetail>('POST', `organizations/${orgId}/suspend`, { reason });
  }
  reactivateOrg(orgId: string) {
    return this.send<OrgDetail>('POST', `organizations/${orgId}/reactivate`);
  }
  suspendUser(userId: string, reason: string) {
    return this.send<UserDetail>('POST', `users/${userId}/suspend`, { reason });
  }
  reactivateUser(userId: string) {
    return this.send<UserDetail>('POST', `users/${userId}/reactivate`);
  }
  createCode(body: { label: string; account_type: string | null; max_uses: number | null; expires_in_days: number | null }) {
    return this.send<SignupCode & { code: string }>('POST', 'signup-codes', body);
  }
  revokeCode(id: string) {
    return this.send<SignupCode>('POST', `signup-codes/${id}/revoke`);
  }
}

const STAFF_LABELS: Record<string, string> = {
  platform_admin: 'Platform admin', support_admin: 'Support admin', billing_admin: 'Billing admin',
  site_admin: 'Website admin', content_editor: 'Content editor',
};

/** "Super Admin", "Support admin", … or null for customers. */
export function staffLabel(u: { super_admin: boolean; staff_role: string | null }): string | null {
  if (u.super_admin) return 'Super Admin';
  return u.staff_role ? (STAFF_LABELS[u.staff_role] ?? u.staff_role) : null;
}

/** A reason as a sentence: ends with a full stop if the person didn't add one. */
export function sentence(text: string | null): string {
  const t = (text ?? '').trim();
  return t && !/[.!?]$/.test(t) ? `${t}.` : t;
}
