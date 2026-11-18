import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { apiProblem, applyFieldErrors } from '../../core/api-errors';
import { Website } from '../../core/api.types';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi } from '../../core/org-api.service';
import { WorkspaceService } from '../../core/workspace.service';
import { FieldError, showError } from '../../shared/forms/forms';

export interface WebsiteFormData {
  website?: Website;
  /** Pre-selects the workspace (agencies choose; a business always uses its own). */
  workspaceId?: string;
  /** Locks the new website to this client's workspace, e.g. when adding from a client's page. */
  clientId?: string;
}

/** Add or edit a website. Closes with the saved website. */
@Component({
  selector: 'ol-website-form-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, FieldError],
  template: `
    <h2 class="h5 mb-3">{{ existing ? 'Edit website' : 'Add website' }}</h2>
    @if (error()) {
      <div class="alert alert-danger" role="alert">{{ error() }}</div>
    }
    <form [formGroup]="form" (ngSubmit)="save()" novalidate>
      <div class="mb-3">
        <label for="site-url" class="form-label">Address</label>
        <input id="site-url" class="form-control" formControlName="url" inputmode="url"
          placeholder="example.com" [class.is-invalid]="invalid('url')" spellcheck="false"
          autocapitalize="off" aria-describedby="url-hint" />
        <ol-field-error [control]="form.controls.url" />
        <div id="url-hint" class="form-text">The site's public address. https:// is added if you leave it out.</div>
      </div>
      <div class="mb-3">
        <label for="site-name" class="form-label">Name <span class="text-muted">(optional)</span></label>
        <input id="site-name" class="form-control" formControlName="name"
          placeholder="Defaults to the domain" />
      </div>
      @if (choosesWorkspace) {
        <div class="mb-3">
          <label for="site-workspace" class="form-label">Workspace</label>
          <select id="site-workspace" class="form-select" formControlName="workspace_id"
            [class.is-invalid]="invalid('workspace_id')">
            <option value="" disabled>Choose a workspace</option>
            @if (ws.own(); as own) {
              <option [value]="own.id">{{ own.name }} (your own marketing)</option>
            }
            @if (ws.clients().length) {
              <optgroup label="Clients">
                @for (w of ws.clients(); track w.id) {
                  <option [value]="w.id">{{ w.name }}</option>
                }
              </optgroup>
            }
            @if (linkedTargets().length) {
              <optgroup label="Linked businesses">
                @for (w of linkedTargets(); track w.id) {
                  <option [value]="w.id">{{ w.organization_name }}</option>
                }
              </optgroup>
            }
          </select>
          <ol-field-error [control]="form.controls.workspace_id" />
        </div>
      }
      @if (existing) {
        <div class="mb-3">
          <label for="site-status" class="form-label">Status</label>
          <select id="site-status" class="form-select" formControlName="status">
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      }
      <div class="ol-dialog-actions">
        <button type="button" class="btn btn-outline-secondary" (click)="ref.close()">Cancel</button>
        <button type="submit" class="btn btn-primary" [disabled]="busy()">
          {{ existing ? 'Save changes' : 'Add website' }}
        </button>
      </div>
    </form>
  `,
})
export class WebsiteFormDialog {
  protected readonly ref = inject<DialogRef<Website>>(DialogRef);
  private readonly data = inject<WebsiteFormData | undefined>(DIALOG_DATA) ?? {};
  protected readonly existing = this.data.website;
  protected readonly lockedClient = !this.existing && !!this.data.clientId;
  private readonly api = inject(OrgApi);
  protected readonly ws = inject(WorkspaceService);
  /**
   * Agencies pick the workspace; a business only has its own. A website in a linked business's
   * workspace stays there (websites only move within the organization that owns them).
   */
  protected readonly choosesWorkspace = inject(CurrentOrgService).isAgency() && !this.lockedClient
    && !(this.existing && this.ws.linked().some((w) => w.id === this.existing!.workspace_id));
  /** New websites can go into businesses' workspaces shared with permission to make changes. */
  protected readonly linkedTargets = computed(
    () => (this.existing ? [] : this.ws.linked().filter((w) => w.access === 'manage')));
  protected readonly form = inject(NonNullableFormBuilder).group({
    url: [this.existing?.url ?? '', [Validators.required, Validators.maxLength(2048)]],
    name: [this.existing?.name ?? ''],
    workspace_id: [this.existing?.workspace_id ?? this.data.workspaceId ?? '',
      this.choosesWorkspace ? Validators.required : []],
    status: [this.existing?.status ?? 'active'],
  });
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected invalid(name: 'url' | 'workspace_id'): boolean {
    return showError(this.form.controls[name]);
  }

  protected async save(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    this.busy.set(true);
    this.error.set(null);
    try {
      const name = v.name || null;
      let saved: Website;
      if (this.existing) {
        saved = await this.api.updateWebsite(this.existing.id, {
          url: v.url, name: name ?? this.existing.domain, status: v.status as Website['status'],
          ...(this.choosesWorkspace ? { workspace_id: v.workspace_id } : {}) });
      } else if (this.choosesWorkspace) {
        saved = await this.api.createWebsite(v.workspace_id, { url: v.url, name });
      } else {
        // A client's page (that client's workspace), or a business (its own workspace).
        saved = await this.api.createWebsiteFor({ client_id: this.data.clientId, url: v.url, name });
      }
      this.ref.close(saved);
    } catch (err) {
      const p = apiProblem(err);
      if (p.code === 'website_exists') this.form.controls.url.setErrors({ server: p.message });
      else if (!applyFieldErrors(this.form, p.fields)) this.error.set(p.message);
    } finally {
      this.busy.set(false);
    }
  }
}
