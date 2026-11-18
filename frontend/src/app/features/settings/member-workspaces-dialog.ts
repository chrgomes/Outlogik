import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';

import { apiProblem } from '../../core/api-errors';
import { Member, WorkspaceRef } from '../../core/api.types';
import { OrgApi } from '../../core/org-api.service';
import { WorkspaceService } from '../../core/workspace.service';

/**
 * Choose which workspaces a member with a limited role (Account Manager, Client Viewer, or a
 * custom role) can see. Closes with the saved list.
 */
@Component({
  selector: 'ol-member-workspaces-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h2 class="h5 mb-1">Workspaces for {{ member.full_name }}</h2>
    <p class="text-muted small mb-3">
      {{ member.role.name }} sees only the workspaces ticked here.
      @if (clientOnly) { Client Viewers can only be given client workspaces. }
    </p>
    @if (error()) {
      <div class="alert alert-danger" role="alert">{{ error() }}</div>
    }
    @if (current.hasValue()) {
      <fieldset>
        <legend class="visually-hidden">Workspaces</legend>
        @for (group of groups(); track group.label) {
          @if (group.items.length) {
            <h3 class="ws-group-title">{{ group.label }}</h3>
            @for (w of group.items; track w.id) {
              <div class="form-check">
                <input class="form-check-input" type="checkbox" [id]="'ws-' + w.id"
                  [checked]="selected().has(w.id)" (change)="toggle(w.id)" />
                <label class="form-check-label" [for]="'ws-' + w.id">
                  {{ w.name }}
                  @if (w.organization_name) {<small class="text-muted"> · shared by {{ w.organization_name }}</small>}
                </label>
              </div>
            }
          }
        }
        @if (!options().length) {
          <p class="text-muted mb-0">There are no workspaces to choose from yet.</p>
        }
      </fieldset>
    } @else if (current.error()) {
      <div class="alert alert-danger" role="alert">We couldn't load this person's workspaces.</div>
    } @else {
      <div class="text-muted">Loading…</div>
    }
    <div class="ol-dialog-actions">
      <button type="button" class="btn btn-outline-secondary" (click)="ref.close()">Cancel</button>
      <button type="button" class="btn btn-primary" [disabled]="busy() || !current.hasValue()" (click)="save()">
        Save
      </button>
    </div>
  `,
  styles: `
    .ws-group-title { font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
      letter-spacing: 0.04em; color: var(--ol-text-muted); margin: 0.75rem 0 0.375rem; }
    .form-check { margin-bottom: 0.25rem; }
  `,
})
export class MemberWorkspacesDialog {
  protected readonly ref = inject<DialogRef<WorkspaceRef[]>>(DialogRef);
  protected readonly member = inject<Member>(DIALOG_DATA);
  private readonly api = inject(OrgApi);
  private readonly ws = inject(WorkspaceService);
  protected readonly clientOnly = this.member.role.system_key === 'client';

  protected readonly current = httpResource<WorkspaceRef[]>(
    () => this.api.url(`members/${this.member.id}/workspaces`));
  protected readonly selected = signal(new Set<string>());
  protected readonly options = computed(() => {
    const all = [...(this.ws.own() ? [this.ws.own()!] : []), ...this.ws.clients(), ...this.ws.linked()];
    return this.clientOnly ? all.filter((w) => w.kind === 'client' && !w.linked) : all;
  });
  protected readonly groups = computed(() => [
    { label: 'Your own marketing', items: this.options().filter((w) => w.kind === 'own' && !w.linked) },
    { label: 'Clients', items: this.options().filter((w) => w.kind === 'client') },
    { label: 'Linked businesses', items: this.options().filter((w) => w.linked) },
  ]);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  constructor() {
    effect(() => {
      if (this.current.hasValue()) this.selected.set(new Set(this.current.value().map((w) => w.id)));
    });
  }

  protected toggle(id: string): void {
    const next = new Set(this.selected());
    if (next.has(id)) next.delete(id);
    else next.add(id);
    this.selected.set(next);
  }

  protected async save(): Promise<void> {
    this.busy.set(true);
    this.error.set(null);
    try {
      this.ref.close(await this.api.setMemberWorkspaces(this.member.id, [...this.selected()]));
    } catch (err) {
      this.error.set(apiProblem(err).message);
    } finally {
      this.busy.set(false);
    }
  }
}
