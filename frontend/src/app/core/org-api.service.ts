import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import {
  AccessGrant,
  Client,
  ClientUser,
  Invitation,
  Member,
  OrganizationDetail,
  Role,
  Website,
  WorkspaceRef,
} from './api.types';
import { CurrentOrgService } from './current-org.service';
import { WorkspaceService } from './workspace.service';

/** Writes that change workspace names or website counts, so the switcher reloads. */
const CHANGES_WORKSPACES = /^(|clients(\/[^/]+)?|websites(\/.+)?|workspaces\/.+)$/;

/** Drops empty values so they aren't sent as query parameters. */
export function queryParams(values: Record<string, string | number | null | undefined>): HttpParams {
  let params = new HttpParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== null && value !== undefined && value !== '') params = params.set(key, value);
  }
  return params;
}

/**
 * Writes to the organization in the URL. Lists are read with httpResource in components,
 * using url() to build the address.
 */
@Injectable({ providedIn: 'root' })
export class OrgApi {
  private readonly http = inject(HttpClient);
  private readonly org = inject(CurrentOrgService);
  private readonly workspaces = inject(WorkspaceService);

  url(path = ''): string {
    return `/api/v1/orgs/${this.org.slug()}${path ? '/' + path : ''}`;
  }

  private async send<T>(method: 'POST' | 'PATCH' | 'PUT' | 'DELETE', path: string, body?: unknown): Promise<T> {
    const result = await firstValueFrom(this.http.request<T>(method, this.url(path), { body: body ?? {} }));
    if (CHANGES_WORKSPACES.test(path)) this.workspaces.list.reload();
    return result;
  }

  // Organization
  updateOrganization(body: { name: string }) {
    return this.send<OrganizationDetail>('PATCH', '', body);
  }
  leave() {
    return this.send<void>('POST', 'leave');
  }

  // Clients
  createClient(body: Partial<Client>) {
    return this.send<Client>('POST', 'clients', body);
  }
  updateClient(id: string, body: Partial<Client>) {
    return this.send<Client>('PATCH', `clients/${id}`, body);
  }
  deleteClient(id: string) {
    return this.send<void>('DELETE', `clients/${id}`);
  }
  linkClientUser(clientId: string, memberId: string) {
    return this.send<ClientUser[]>('POST', `clients/${clientId}/users`, { member_id: memberId });
  }
  unlinkClientUser(clientId: string, userId: string) {
    return this.send<void>('DELETE', `clients/${clientId}/users/${userId}`);
  }

  // Websites
  /** Into a workspace. */
  createWebsite(workspaceId: string, body: { url: string; name?: string | null }) {
    return this.send<Website>('POST', `workspaces/${workspaceId}/websites`, body);
  }
  /** Into a client's workspace, or without client_id the organization's own workspace. */
  createWebsiteFor(body: { client_id?: string; url: string; name?: string | null }) {
    return this.send<Website>('POST', 'websites', body);
  }
  updateWebsite(id: string, body: Partial<Website>) {
    return this.send<Website>('PATCH', `websites/${id}`, body);
  }
  deleteWebsite(id: string) {
    return this.send<void>('DELETE', `websites/${id}`);
  }

  // Workspace assignments (members whose role is limited to assigned workspaces)
  setMemberWorkspaces(memberId: string, workspaceIds: string[]) {
    return this.send<WorkspaceRef[]>('PUT', `members/${memberId}/workspaces`, { workspace_ids: workspaceIds });
  }

  // Access grants: a business shares its workspace with an agency
  createGrant(body: { email: string; access: 'manage' | 'view' }) {
    return this.send<AccessGrant>('POST', 'access-grants', body);
  }
  revokeGrant(id: string) {
    return this.send<void>('DELETE', `access-grants/${id}`);
  }
  /** An agency ends its access to a business's workspace. */
  disconnectWorkspace(workspaceId: string) {
    return this.send<void>('DELETE', `workspaces/${workspaceId}/access`);
  }

  // Members and invitations
  updateMember(id: string, body: { role_id?: string; status?: string }) {
    return this.send<Member>('PATCH', `members/${id}`, body);
  }
  removeMember(id: string) {
    return this.send<void>('DELETE', `members/${id}`);
  }
  invite(body: { email: string; role_id: string; client_id?: string | null }) {
    return this.send<Invitation>('POST', 'invitations', body);
  }
  resendInvitation(id: string) {
    return this.send<Invitation>('POST', `invitations/${id}/resend`);
  }
  revokeInvitation(id: string) {
    return this.send<void>('DELETE', `invitations/${id}`);
  }

  // Roles
  createRole(body: { name: string; description?: string | null; permissions: string[]; workspace_scope?: string }) {
    return this.send<Role>('POST', 'roles', body);
  }
  updateRole(id: string, body: { name?: string; description?: string | null; permissions?: string[]; workspace_scope?: string }) {
    return this.send<Role>('PATCH', `roles/${id}`, body);
  }
  deleteRole(id: string) {
    return this.send<void>('DELETE', `roles/${id}`);
  }
}
