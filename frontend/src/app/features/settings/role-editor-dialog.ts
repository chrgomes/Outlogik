import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { apiProblem, applyFieldErrors } from '../../core/api-errors';
import { PermissionInfo, Role } from '../../core/api.types';
import { OrgApi } from '../../core/org-api.service';
import { FieldError, showError } from '../../shared/forms/forms';

export interface RoleEditorData {
  role?: Role;
  readOnly?: boolean;
}

/** Create, edit or view a role's permissions. Closes with the saved role. */
@Component({
  selector: 'ol-role-editor-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, FieldError],
  template: `
    <h2 class="h5 mb-1">{{ readOnly ? role!.name : role ? 'Edit role' : 'New role' }}</h2>
    <p class="text-muted small mb-3">
      @if (role?.is_system) {
        A built-in role. Its permissions can't be changed; create a custom role for something different.
      } @else if (readOnly) {
        {{ role?.description || 'A custom role.' }}
      } @else {
        Choose exactly what people with this role can do. Changes apply on their next click.
      }
    </p>
    @if (error()) {
      <div class="alert alert-danger" role="alert">{{ error() }}</div>
    }
    <form [formGroup]="form" (ngSubmit)="save()" novalidate>
      @if (!readOnly) {
        <div class="row g-3 mb-3">
          <div class="col-sm-5">
            <label for="role-name" class="form-label">Name</label>
            <input id="role-name" class="form-control" formControlName="name"
              [class.is-invalid]="invalidName()" placeholder="e.g. SEO Specialist" />
            <ol-field-error [control]="form.controls.name" />
          </div>
          <div class="col-sm-7">
            <label for="role-desc" class="form-label">Description <span class="text-muted">(optional)</span></label>
            <input id="role-desc" class="form-control" formControlName="description" />
          </div>
        </div>
      }

      @if (catalogue.hasValue()) {
        <fieldset [disabled]="readOnly">
          <legend class="visually-hidden">Permissions</legend>
          @for (group of groups(); track group.name) {
            <div class="perm-group">
              <h3 class="perm-group-title">{{ group.name }}</h3>
              @for (p of group.items; track p.code) {
                <div class="form-check">
                  <input class="form-check-input" type="checkbox" [id]="'perm-' + p.code"
                    [checked]="selected().has(p.code)" (change)="toggle(p.code)" />
                  <label class="form-check-label" [for]="'perm-' + p.code">{{ p.description }}</label>
                </div>
              }
            </div>
          }
        </fieldset>
        @if (noneSelected()) {
          <div class="text-danger small mt-2">Choose at least one permission.</div>
        }
      } @else {
        <div class="text-muted">Loading permissions…</div>
      }

      <div class="ol-dialog-actions">
        <button type="button" class="btn btn-outline-secondary" (click)="ref.close()">
          {{ readOnly ? 'Close' : 'Cancel' }}
        </button>
        @if (!readOnly) {
          <button type="submit" class="btn btn-primary" [disabled]="busy()">
            {{ role ? 'Save changes' : 'Create role' }}
          </button>
        }
      </div>
    </form>
  `,
  styles: `
    .perm-group { padding: 0.75rem 0; border-top: 1px solid var(--ol-border); }
    .perm-group-title { font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
      letter-spacing: 0.04em; color: var(--ol-text-muted); margin-bottom: 0.5rem; }
    .form-check { margin-bottom: 0.25rem; }
    fieldset:disabled .form-check-label { opacity: 1; }
  `,
})
export class RoleEditorDialog {
  protected readonly ref = inject<DialogRef<Role>>(DialogRef);
  private readonly data = inject<RoleEditorData | undefined>(DIALOG_DATA) ?? {};
  protected readonly role = this.data.role;
  protected readonly readOnly = !!this.data.readOnly || !!this.role?.is_system;
  private readonly api = inject(OrgApi);

  protected readonly catalogue = httpResource<PermissionInfo[]>(() => this.api.url('permissions'));
  protected readonly groups = computed(() => {
    const map = new Map<string, PermissionInfo[]>();
    for (const p of this.catalogue.value() ?? []) map.set(p.group, [...(map.get(p.group) ?? []), p]);
    return [...map].map(([name, items]) => ({ name, items }));
  });
  protected readonly selected = signal(new Set(this.role?.permissions ?? []));
  protected readonly noneSelected = signal(false);
  protected readonly form = inject(NonNullableFormBuilder).group({
    name: [this.role?.name ?? '', [Validators.required, Validators.maxLength(100)]],
    description: [this.role?.description ?? '', Validators.maxLength(300)],
  });
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected invalidName(): boolean {
    return showError(this.form.controls.name);
  }

  protected toggle(code: string): void {
    const next = new Set(this.selected());
    if (next.has(code)) next.delete(code);
    else next.add(code);
    this.selected.set(next);
    this.noneSelected.set(false);
  }

  protected async save(): Promise<void> {
    if (this.readOnly) return;
    const empty = this.selected().size === 0;
    this.noneSelected.set(empty);
    if (this.form.invalid || empty) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    const body = { name: v.name, description: v.description || null, permissions: [...this.selected()] };
    this.busy.set(true);
    this.error.set(null);
    try {
      this.ref.close(this.role ? await this.api.updateRole(this.role.id, body) : await this.api.createRole(body));
    } catch (err) {
      const p = apiProblem(err);
      if (p.code === 'role_name_taken') this.form.controls.name.setErrors({ server: p.message });
      else if (!applyFieldErrors(this.form, p.fields)) this.error.set(p.message);
    } finally {
      this.busy.set(false);
    }
  }
}
