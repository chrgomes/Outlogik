import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, effect, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { apiProblem } from '../../core/api-errors';
import { AuthService } from '../../core/auth.service';
import { DialogService } from '../../shared/dialog/dialog';
import { PageHeader } from '../../shared/page-header/page-header';
import { ErrorState, LoadingState } from '../../shared/states/states';
import { Status } from '../../shared/table/table-parts';
import { ToastService } from '../../shared/toast/toast';
import { OrgDetail, PLATFORM_API, PlanOption, PlatformApi, describeAction, sentence } from './platform-api';
import { ReasonData, ReasonDialog } from './reason-dialog';

/** /admin/platform/organizations/:orgId: an organization's plan, usage, members and history. */
@Component({
  selector: 'ol-platform-organization',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, RouterLink, PageHeader, ErrorState, LoadingState, Status],
  template: `
    <a class="small" [routerLink]="['/admin', 'platform', 'organizations']">← Organizations</a>
    @if (org.error()) {
      <ol-error-state message="We couldn't load this organization." (retry)="org.reload()" />
    } @else if (org.value(); as o) {
      <ol-page-header [title]="o.name" [description]="(o.kind === 'agency' ? 'Agency' : 'Business') + ' · ' + o.slug + ' · joined ' + (o.created_at | date: 'mediumDate')" />

      @if (o.status === 'suspended') {
        <div class="alert alert-danger d-flex flex-wrap gap-3 align-items-center justify-content-between" role="status">
          <span><strong>Suspended.</strong> {{ sentence(o.suspended_reason) }} Members can’t use it, and its scheduled audits and Google syncs are paused.</span>
          @if (caps().has('orgs.suspend')) {
            <button type="button" class="btn btn-sm btn-outline-secondary" [disabled]="busy()" (click)="reactivate(o)">Reactivate</button>
          }
        </div>
      }

      <div class="po-grid">
        <section class="po-card" aria-labelledby="plan-h">
          <h2 id="plan-h" class="h6">Plan</h2>
          <p class="mb-2">{{ o.plan ?? 'No plan' }}
            @if (o.subscription_status) { <ol-status [value]="o.subscription_status" /> }
            @if (o.billing_interval) { <span class="text-muted small">{{ ' ' }}· {{ o.billing_interval }}</span> }</p>
          @if (o.trial_ends_at && o.subscription_status !== 'active') {
            <p class="small text-muted">Trial {{ o.subscription_status === 'trial_ended' ? 'ended' : 'ends' }} {{ o.trial_ends_at | date: 'mediumDate' }}</p>
          }
          @if (o.signup_code) { <p class="small text-muted">Signed up with invitation code {{ o.signup_code }}</p> }
          @if (caps().has('plans.assign')) {
            <form class="border-top pt-3 mt-3" (submit)="$event.preventDefault(); assign(o)">
              <div class="row g-2">
                <div class="col-sm-6">
                  <label class="form-label small" for="p-plan">Plan</label>
                  <select id="p-plan" class="form-select form-select-sm" (change)="plan.set($any($event.target).value)">
                    @for (p of plansFor(o.kind); track p.key) { <option [value]="p.key" [selected]="p.key === plan()">{{ p.name }}</option> }
                  </select>
                </div>
                <div class="col-sm-6">
                  <label class="form-label small" for="p-status">Status</label>
                  <select id="p-status" class="form-select form-select-sm" [value]="status()" (change)="status.set($any($event.target).value)">
                    <option value="active">Active</option>
                    <option value="trialing">Trial</option>
                    <option value="past_due">Past due</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                </div>
                <div class="col-sm-6">
                  <label class="form-label small" for="p-interval">Billing</label>
                  <select id="p-interval" class="form-select form-select-sm" [value]="interval()" (change)="interval.set($any($event.target).value)">
                    <option value="monthly">Monthly</option>
                    <option value="annual">Annual (paid upfront)</option>
                  </select>
                </div>
                @if (status() === 'trialing') {
                  <div class="col-sm-6">
                    <label class="form-label small" for="p-days">Trial length (days)</label>
                    <input id="p-days" type="number" min="1" max="90" class="form-control form-control-sm" [value]="trialDays()"
                      (input)="trialDays.set(+$any($event.target).value)" />
                  </div>
                }
              </div>
              <button type="submit" class="btn btn-sm btn-primary mt-3" [disabled]="busy()">Save plan</button>
            </form>
          }
        </section>

        <section class="po-card" aria-labelledby="usage-h">
          <h2 id="usage-h" class="h6">Limits and usage</h2>
          <table class="table table-sm mb-0">
            <tbody>
              @for (l of o.limits; track l.key) {
                <tr><td>{{ l.label }}</td><td class="text-end text-nowrap">{{ l.used === null ? 'Up to ' + (l.limit ?? 'unlimited') : l.used + ' of ' + (l.limit ?? 'unlimited') }}</td></tr>
              }
            </tbody>
          </table>
        </section>
      </div>

      <section class="ol-table-card mt-4" aria-labelledby="members-h">
        <h2 id="members-h" class="h6 p-3 pb-2 mb-0">Members</h2>
        <div class="table-responsive">
          <table class="table ol-table mb-0">
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th></tr></thead>
            <tbody>
              @for (m of o.members_list; track m.user_id) {
                <tr>
                  <td><a class="row-link" [routerLink]="['/admin', 'platform', 'users', m.user_id]">{{ m.name }}</a></td>
                  <td>{{ m.email }}</td><td>{{ m.role }}</td>
                  <td><ol-status [value]="m.user_active ? m.status : 'suspended'" /></td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </section>

      <section class="po-card mt-4" aria-labelledby="history-h">
        <h2 id="history-h" class="h6">Staff changes</h2>
        @if (o.history.length) {
          <ul class="list-unstyled mb-0 po-history">
            @for (h of o.history; track h.created_at + h.action) {
              <li><span>{{ describe(h) }}</span>
                <span class="small text-muted">{{ h.actor ?? 'Command line' }} · {{ h.created_at | date: 'medium' }}</span></li>
            }
          </ul>
        } @else {
          <p class="text-muted mb-0">No staff changes yet.</p>
        }
      </section>

      @if (caps().has('orgs.suspend') && o.status !== 'suspended') {
        <section class="po-card po-danger mt-4" aria-labelledby="suspend-h">
          <h2 id="suspend-h" class="h6">Suspend</h2>
          <p class="small text-muted">Members can’t use the organization until it’s reactivated, and its scheduled audits and Google syncs pause. Nothing is deleted.</p>
          <button type="button" class="btn btn-outline-danger" [disabled]="busy()" (click)="suspend(o)">Suspend {{ o.name }}</button>
        </section>
      }
    } @else {
      <ol-loading-state label="Loading…" />
    }
  `,
  styles: `
    .po-grid { display: grid; gap: 1.5rem; grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr)); }
    .po-card { padding: 1.25rem; border: 1px solid var(--ol-border); border-radius: var(--bs-border-radius-lg); background: var(--ol-surface-raised); }
    .po-danger { border-color: var(--bs-danger-border-subtle); }
    .po-history li { display: flex; flex-direction: column; padding: 0.5rem 0; border-top: 1px solid var(--ol-border); }
  `,
})
export class PlatformOrganization {
  readonly orgId = input.required<string>();
  private readonly auth = inject(AuthService);
  private readonly api = inject(PlatformApi);
  private readonly dialog = inject(DialogService);
  private readonly toast = inject(ToastService);

  protected readonly caps = this.auth.platformCaps;
  protected readonly describe = describeAction;
  protected readonly org = httpResource<OrgDetail>(() => `${PLATFORM_API}/organizations/${this.orgId()}`);
  private readonly plans = httpResource<PlanOption[]>(() => this.caps().has('plans.assign') ? `${PLATFORM_API}/plans` : undefined);
  protected readonly plan = signal('');
  protected readonly status = signal('active');
  protected readonly interval = signal('monthly');
  protected readonly trialDays = signal(14);
  protected readonly busy = signal(false);

  constructor() {
    // Start the form from the current plan.
    effect(() => {
      const o = this.org.value();
      const options = this.plans.value() ?? [];
      if (!o || !options.length) return;
      this.plan.set(options.find((p) => p.name === o.plan)?.key ?? this.plansFor(o.kind)[0]?.key ?? '');
      this.status.set(o.subscription_status === 'trial_ended' || !o.subscription_status ? 'active' : o.subscription_status);
      this.interval.set(o.billing_interval ?? 'monthly');
    });
  }

  protected readonly sentence = sentence;

  protected plansFor(kind: string): PlanOption[] {
    return (this.plans.value() ?? []).filter((p) => p.account_kind === kind);
  }

  protected async assign(o: OrgDetail): Promise<void> {
    await this.run(() => this.api.assignPlan(o.id, { plan: this.plan(), status: this.status(), interval: this.interval(),
      trial_days: this.status() === 'trialing' ? this.trialDays() : null }), 'Plan saved.');
  }

  protected async suspend(o: OrgDetail): Promise<void> {
    const reason = await this.dialog.open<string, ReasonData>(ReasonDialog, {
      title: `Suspend ${o.name}?`, confirmLabel: 'Suspend',
      message: 'Its members won’t be able to use it until it’s reactivated. Nothing is deleted.' });
    if (reason) await this.run(() => this.api.suspendOrg(o.id, reason), `${o.name} is suspended.`);
  }

  protected async reactivate(o: OrgDetail): Promise<void> {
    await this.run(() => this.api.reactivateOrg(o.id), `${o.name} is active again.`);
  }

  private async run(action: () => Promise<OrgDetail>, done: string): Promise<void> {
    this.busy.set(true);
    try {
      this.org.set(await action());
      this.toast.success(done);
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    } finally {
      this.busy.set(false);
    }
  }
}
