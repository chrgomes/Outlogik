import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { apiProblem } from '../../core/api-errors';
import { Member, Page } from '../../core/api.types';
import { OrgApi, queryParams } from '../../core/org-api.service';

/** Give an existing client-portal user access to one more client. */
@Component({
  selector: 'ol-link-user-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule],
  template: `
    <h2 class="h5 mb-1">Add an existing client user</h2>
    <p class="text-muted small mb-3">For someone who already uses the portal for another client.</p>
    @if (error()) {
      <div class="alert alert-danger" role="alert">{{ error() }}</div>
    }
    @if (candidates().length === 0 && members.hasValue()) {
      <p class="mb-0">Everyone with the Client role already has access. Use “Invite” for someone new.</p>
      <div class="ol-dialog-actions">
        <button type="button" class="btn btn-outline-secondary" (click)="ref.close()">Close</button>
      </div>
    } @else {
      <label for="link-member" class="form-label">Person</label>
      <select id="link-member" class="form-select" [ngModel]="memberId()" (ngModelChange)="memberId.set($event)">
        <option value="" disabled>Choose a person</option>
        @for (m of candidates(); track m.id) {
          <option [value]="m.id">{{ m.full_name }} ({{ m.email }})</option>
        }
      </select>
      <div class="ol-dialog-actions">
        <button type="button" class="btn btn-outline-secondary" (click)="ref.close()">Cancel</button>
        <button type="button" class="btn btn-primary" [disabled]="!memberId() || busy()" (click)="link()">
          Give access
        </button>
      </div>
    }
  `,
})
export class LinkUserDialog {
  protected readonly ref = inject<DialogRef<boolean>>(DialogRef);
  private readonly data = inject<{ clientId: string; linkedUserIds: string[] }>(DIALOG_DATA);
  private readonly api = inject(OrgApi);
  protected readonly members = httpResource<Page<Member>>(() => ({
    url: this.api.url('members'), params: queryParams({ page_size: 100, status: 'active' }),
  }));
  protected readonly candidates = computed(() => (this.members.value()?.items ?? []).filter(
    (m) => m.role.system_key === 'client' && !this.data.linkedUserIds.includes(m.user_id)));
  protected readonly memberId = signal('');
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected async link(): Promise<void> {
    this.busy.set(true);
    try {
      await this.api.linkClientUser(this.data.clientId, this.memberId());
      this.ref.close(true);
    } catch (err) {
      this.error.set(apiProblem(err).message);
    } finally {
      this.busy.set(false);
    }
  }
}
