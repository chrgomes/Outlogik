import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { apiProblem, applyFieldErrors } from '../../core/api-errors';
import { Client } from '../../core/api.types';
import { OrgApi } from '../../core/org-api.service';
import { FieldError, showError } from '../../shared/forms/forms';

/** Add or edit a client. Closes with the saved client. */
@Component({
  selector: 'ol-client-form-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, FieldError],
  template: `
    <h2 class="h5 mb-3">{{ existing ? 'Edit client' : 'Add client' }}</h2>
    @if (error()) {
      <div class="alert alert-danger" role="alert">{{ error() }}</div>
    }
    <form [formGroup]="form" (ngSubmit)="save()" novalidate>
      <div class="mb-3">
        <label for="client-name" class="form-label">Name</label>
        <input id="client-name" class="form-control" formControlName="name"
          [class.is-invalid]="invalid('name')" placeholder="e.g. Bakery Ltd" />
        <ol-field-error [control]="form.controls.name" />
      </div>
      <div class="mb-3">
        <label for="client-email" class="form-label">Contact email <span class="text-muted">(optional)</span></label>
        <input id="client-email" type="email" class="form-control" formControlName="contact_email"
          [class.is-invalid]="invalid('contact_email')" />
        <ol-field-error [control]="form.controls.contact_email" />
      </div>
      <div class="mb-3">
        <label for="client-notes" class="form-label">Internal notes <span class="text-muted">(optional)</span></label>
        <textarea id="client-notes" class="form-control" rows="3" formControlName="notes"
          aria-describedby="notes-hint"></textarea>
        <div id="notes-hint" class="form-text">Only your team sees notes, never the client.</div>
      </div>
      <div class="ol-dialog-actions">
        <button type="button" class="btn btn-outline-secondary" (click)="ref.close()">Cancel</button>
        <button type="submit" class="btn btn-primary" [disabled]="busy()">
          {{ existing ? 'Save changes' : 'Add client' }}
        </button>
      </div>
    </form>
  `,
})
export class ClientFormDialog {
  protected readonly ref = inject<DialogRef<Client>>(DialogRef);
  protected readonly existing = inject<{ client?: Client } | undefined>(DIALOG_DATA)?.client;
  private readonly api = inject(OrgApi);
  protected readonly form = inject(NonNullableFormBuilder).group({
    name: [this.existing?.name ?? '', [Validators.required, Validators.maxLength(200)]],
    contact_email: [this.existing?.contact_email ?? '', [Validators.email]],
    notes: [this.existing?.notes ?? '', [Validators.maxLength(10000)]],
  });
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected invalid(name: 'name' | 'contact_email'): boolean {
    return showError(this.form.controls[name]);
  }

  protected async save(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    const body = { name: v.name, contact_email: v.contact_email || null, notes: v.notes || null };
    this.busy.set(true);
    this.error.set(null);
    try {
      const saved = this.existing
        ? await this.api.updateClient(this.existing.id, body)
        : await this.api.createClient(body);
      this.ref.close(saved);
    } catch (err) {
      const p = apiProblem(err);
      if (!applyFieldErrors(this.form, p.fields)) this.error.set(p.message);
    } finally {
      this.busy.set(false);
    }
  }
}
