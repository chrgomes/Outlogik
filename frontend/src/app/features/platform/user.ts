import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { apiProblem } from '../../core/api-errors';
import { AuthService } from '../../core/auth.service';
import { DialogService } from '../../shared/dialog/dialog';
import { PageHeader } from '../../shared/page-header/page-header';
import { ErrorState, LoadingState } from '../../shared/states/states';
import { Status } from '../../shared/table/table-parts';
import { ToastService } from '../../shared/toast/toast';
import { PLATFORM_API, PlatformApi, UserDetail, describeAction, sentence, staffLabel } from './platform-api';
import { ReasonData, ReasonDialog } from './reason-dialog';

/** /admin/platform/users/:userId: a person's organizations, status and history. */
@Component({
  selector: 'ol-platform-user',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, RouterLink, PageHeader, ErrorState, LoadingState, Status],
  template: `
    <a class="small" [routerLink]="['/admin', 'platform', 'users']">← Users</a>
    @if (user.error()) {
      <ol-error-state message="We couldn't load this user." (retry)="user.reload()" />
    } @else if (user.value(); as u) {
      <ol-page-header [title]="u.name" [description]="u.email + (u.verified ? '' : ' (email not confirmed)') + ' · joined ' + (u.created_at | date: 'mediumDate')" />
      @if (staffLabel(u); as s) { <p><span class="badge text-bg-secondary">Outlogik staff · {{ s }}</span></p> }

      @if (!u.active) {
        <div class="alert alert-danger d-flex flex-wrap gap-3 align-items-center justify-content-between" role="status">
          <span><strong>Suspended.</strong> {{ sentence(u.suspended_reason) }} They can’t sign in.</span>
          @if (canChange()) {
            <button type="button" class="btn btn-sm btn-outline-secondary" [disabled]="busy()" (click)="reactivate(u)">Reactivate</button>
          }
        </div>
      }

      <section class="ol-table-card" aria-labelledby="orgs-h">
        <h2 id="orgs-h" class="h6 p-3 pb-2 mb-0">Organizations</h2>
        @if (u.memberships.length) {
          <div class="table-responsive">
            <table class="table ol-table mb-0">
              <thead><tr><th>Organization</th><th>Role</th><th>Membership</th></tr></thead>
              <tbody>
                @for (m of u.memberships; track m.organization_id) {
                  <tr>
                    <td><a class="row-link" [routerLink]="['/admin', 'platform', 'organizations', m.organization_id]">{{ m.organization_name }}</a>
                      @if (m.organization_status === 'suspended') { <span class="small text-danger">{{ ' ' }}· suspended</span> }</td>
                    <td>{{ m.role }}</td>
                    <td><ol-status [value]="m.status" /></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        } @else {
          <p class="text-muted px-3">Not a member of any organization.</p>
        }
      </section>

      <section class="po-card mt-4" aria-labelledby="history-h">
        <h2 id="history-h" class="h6">Staff changes</h2>
        @if (u.history.length) {
          <ul class="list-unstyled mb-0 po-history">
            @for (h of u.history; track h.created_at + h.action) {
              <li><span>{{ describe(h) }}</span>
                <span class="small text-muted">{{ h.actor ?? 'Command line' }} · {{ h.created_at | date: 'medium' }}</span></li>
            }
          </ul>
        } @else {
          <p class="text-muted mb-0">No staff changes yet.</p>
        }
      </section>

      @if (canChange() && u.active) {
        <section class="po-card po-danger mt-4" aria-labelledby="suspend-h">
          <h2 id="suspend-h" class="h6">Suspend</h2>
          <p class="small text-muted">They’re signed out everywhere and can’t sign in until reactivated. Their organizations carry on.</p>
          <button type="button" class="btn btn-outline-danger" [disabled]="busy()" (click)="suspend(u)">Suspend {{ u.name }}</button>
        </section>
      }
    } @else {
      <ol-loading-state label="Loading…" />
    }
  `,
  styles: `
    .po-card { padding: 1.25rem; border: 1px solid var(--ol-border); border-radius: var(--bs-border-radius-lg); background: var(--ol-surface-raised); }
    .po-danger { border-color: var(--bs-danger-border-subtle); }
    .po-history li { display: flex; flex-direction: column; padding: 0.5rem 0; border-top: 1px solid var(--ol-border); }
  `,
})
export class PlatformUser {
  readonly userId = input.required<string>();
  private readonly auth = inject(AuthService);
  private readonly api = inject(PlatformApi);
  private readonly dialog = inject(DialogService);
  private readonly toast = inject(ToastService);

  protected readonly describe = describeAction;
  protected readonly staffLabel = staffLabel;
  protected readonly sentence = sentence;
  protected readonly user = httpResource<UserDetail>(() => `${PLATFORM_API}/users/${this.userId()}`);
  protected readonly busy = signal(false);
  /** Mirrors the API: not yourself, and staff only by a Super Admin. */
  protected readonly canChange = computed(() => {
    const u = this.user.value();
    const me = this.auth.user();
    if (!u || !me || !this.auth.platformCaps().has('users.suspend') || u.id === me.id) return false;
    return !(u.super_admin || u.staff_role) || me.is_super_admin;
  });

  protected async suspend(u: UserDetail): Promise<void> {
    const reason = await this.dialog.open<string, ReasonData>(ReasonDialog, {
      title: `Suspend ${u.name}?`, confirmLabel: 'Suspend',
      message: 'They’ll be signed out everywhere and can’t sign in until reactivated.' });
    if (reason) await this.run(() => this.api.suspendUser(u.id, reason), `${u.name} is suspended.`);
  }

  protected async reactivate(u: UserDetail): Promise<void> {
    await this.run(() => this.api.reactivateUser(u.id), `${u.name} can sign in again.`);
  }

  private async run(action: () => Promise<UserDetail>, done: string): Promise<void> {
    this.busy.set(true);
    try {
      this.user.set(await action());
      this.toast.success(done);
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    } finally {
      this.busy.set(false);
    }
  }
}
