import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { apiProblem, applyFieldErrors } from '../../core/api-errors';
import { Client, Page, Website } from '../../core/api.types';
import { OrgApi, queryParams } from '../../core/org-api.service';
import { FieldError, showError } from '../../shared/forms/forms';

export interface WebsiteFormData {
  website?: Website;
  /** Pre-selects (and locks) the client, e.g. when adding from a client's page. */
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
      @if (!lockedClient) {
        <div class="mb-3">
          <label for="site-client" class="form-label">Client</label>
          <select id="site-client" class="form-select" formControlName="client_id"
            [class.is-invalid]="invalid('client_id')">
            <option value="" disabled>Choose a client</option>
            @for (c of clients.value()?.items ?? []; track c.id) {
              <option [value]="c.id">{{ c.name }}</option>
            }
          </select>
          <ol-field-error [control]="form.controls.client_id" />
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
  protected readonly clients = httpResource<Page<Client>>(() =>
    this.lockedClient ? undefined : {
      url: this.api.url('clients'), params: queryParams({ page_size: 100, sort: 'name' }),
    });
  protected readonly form = inject(NonNullableFormBuilder).group({
    url: [this.existing?.url ?? '', [Validators.required, Validators.maxLength(2048)]],
    name: [this.existing?.name ?? ''],
    client_id: [this.existing?.client_id ?? this.data.clientId ?? '', Validators.required],
    status: [this.existing?.status ?? 'active'],
  });
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected invalid(name: 'url' | 'client_id'): boolean {
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
      const saved = this.existing
        ? await this.api.updateWebsite(this.existing.id, {
            url: v.url, name: v.name || this.existing.domain, client_id: v.client_id,
            status: v.status as Website['status'] })
        : await this.api.createWebsite({ client_id: v.client_id, url: v.url, name: v.name || null });
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
