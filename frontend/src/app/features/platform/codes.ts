import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';

import { apiProblem } from '../../core/api-errors';
import { DialogService } from '../../shared/dialog/dialog';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { Status } from '../../shared/table/table-parts';
import { ToastService } from '../../shared/toast/toast';
import { PLATFORM_API, PlatformApi, SignupCode } from './platform-api';

/** /admin/platform/codes: invitation codes for signing up during the beta. */
@Component({
  selector: 'ol-platform-codes',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, PageHeader, EmptyState, ErrorState, LoadingState, Status],
  template: `
    <ol-page-header title="Invitation codes"
      description="During the beta, people need one of these codes to sign up. Give each group its own code, so you can see where sign-ups came from." />

    <section class="pc-card mb-4" aria-labelledby="new-h">
      <h2 id="new-h" class="h6 mb-3">New code</h2>
      <form (submit)="$event.preventDefault(); create()" novalidate>
        <div class="row g-3">
          <div class="col-md-5">
            <label class="form-label" for="c-label">Who it's for</label>
            <input id="c-label" class="form-control" maxlength="200" placeholder="Beta wave 1" [value]="label()"
              (input)="label.set($any($event.target).value)" [class.is-invalid]="labelError()" />
            @if (labelError()) { <div class="invalid-feedback">{{ labelError() }}</div> }
          </div>
          <div class="col-md-3">
            <label class="form-label" for="c-type">Account type</label>
            <select id="c-type" class="form-select" [value]="type()" (change)="type.set($any($event.target).value)">
              <option value="">Business or agency</option>
              <option value="business">Businesses only</option>
              <option value="agency">Agencies only</option>
            </select>
          </div>
          <div class="col-6 col-md-2">
            <label class="form-label" for="c-uses">Uses</label>
            <input id="c-uses" type="number" min="1" max="10000" class="form-control" placeholder="No limit" [value]="uses()"
              (input)="uses.set($any($event.target).value)" />
          </div>
          <div class="col-6 col-md-2">
            <label class="form-label" for="c-days">Expires in (days)</label>
            <input id="c-days" type="number" min="1" max="365" class="form-control" placeholder="Never" [value]="days()"
              (input)="days.set($any($event.target).value)" />
          </div>
        </div>
        <button type="submit" class="btn btn-primary mt-3" [disabled]="busy()">Make code</button>
      </form>
      @if (created(); as c) {
        <div class="alert alert-success mt-3 mb-0" role="status">
          <p class="mb-2">Here's the code for <strong>{{ c.label }}</strong>. Copy it now: for safety, it won't be shown again.</p>
          <div class="d-flex flex-wrap gap-2 align-items-center">
            <code class="pc-code" aria-label="Invitation code">{{ c.code }}</code>
            <button type="button" class="btn btn-sm btn-outline-secondary" (click)="copy(c.code)">{{ copied() ? 'Copied' : 'Copy' }}</button>
          </div>
        </div>
      }
    </section>

    @if (codes.error()) {
      <ol-error-state message="We couldn't load the codes." (retry)="codes.reload()" />
    } @else if (codes.value(); as list) {
      @if (list.length === 0) {
        <ol-empty-state icon="envelope" title="No codes yet" message="Make a code above and send it to the people you'd like to try Outlogik." />
      } @else {
        <div class="ol-table-card">
          <div class="table-responsive">
            <table class="table ol-table mb-0">
              <thead><tr><th>For</th><th>Code ends</th><th>Account type</th><th class="text-end">Used</th><th>Expires</th><th>Status</th>
                <th><span class="visually-hidden">Actions</span></th></tr></thead>
              <tbody>
                @for (c of list; track c.id) {
                  <tr>
                    <td><span class="fw-medium">{{ c.label }}</span>
                      <span class="d-block small text-muted">{{ c.created_by ?? 'Command line' }} · {{ c.created_at | date: 'mediumDate' }}</span></td>
                    <td><code>…{{ c.hint }}</code></td>
                    <td>{{ c.account_type === 'business' ? 'Businesses' : c.account_type === 'agency' ? 'Agencies' : 'Either' }}</td>
                    <td class="text-end text-nowrap">{{ c.uses }}{{ c.max_uses ? ' of ' + c.max_uses : '' }}</td>
                    <td class="text-nowrap">{{ c.expires_at ? (c.expires_at | date: 'mediumDate') : 'Never' }}</td>
                    <td><ol-status [value]="c.status" /></td>
                    <td class="text-end">
                      @if (c.status === 'active') {
                        <button type="button" class="btn btn-sm btn-link text-danger" [attr.aria-label]="'Revoke the code for ' + c.label" (click)="revoke(c)">Revoke</button>
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }
    } @else {
      <ol-loading-state label="Loading codes…" />
    }
  `,
  styles: `
    .pc-card { padding: 1.25rem; border: 1px solid var(--ol-border); border-radius: var(--bs-border-radius-lg); background: var(--ol-surface-raised); }
    .pc-code { font-size: 1.15rem; letter-spacing: 0.08em; padding: 0.35rem 0.6rem; border-radius: var(--bs-border-radius);
      background: var(--ol-surface-raised); color: var(--ol-text-strong); }
  `,
})
export class PlatformCodes {
  private readonly api = inject(PlatformApi);
  private readonly dialog = inject(DialogService);
  private readonly toast = inject(ToastService);

  protected readonly codes = httpResource<SignupCode[]>(() => `${PLATFORM_API}/signup-codes`);
  protected readonly label = signal('');
  protected readonly type = signal('');
  protected readonly uses = signal('');
  protected readonly days = signal('');
  protected readonly labelError = signal('');
  protected readonly busy = signal(false);
  protected readonly created = signal<(SignupCode & { code: string }) | null>(null);
  protected readonly copied = signal(false);

  protected async create(): Promise<void> {
    const label = this.label().trim();
    if (label.length < 2) return this.labelError.set('Say who the code is for, for example "Beta wave 1".');
    this.labelError.set('');
    this.busy.set(true);
    try {
      const code = await this.api.createCode({ label, account_type: this.type() || null,
        max_uses: this.uses() ? Number(this.uses()) : null, expires_in_days: this.days() ? Number(this.days()) : null });
      this.created.set(code);
      this.copied.set(false);
      this.label.set(''); this.uses.set(''); this.days.set(''); this.type.set('');
      this.codes.reload();
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    } finally {
      this.busy.set(false);
    }
  }

  protected async copy(code: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(code);
      this.copied.set(true);
    } catch {
      this.toast.error('Couldn’t copy. Select the code and copy it by hand.');
    }
  }

  protected async revoke(c: SignupCode): Promise<void> {
    const ok = await this.dialog.confirm({ title: `Revoke the code for ${c.label}?`, danger: true, confirmLabel: 'Revoke',
      message: 'Nobody will be able to sign up with it any more. Accounts already made with it carry on.' });
    if (!ok) return;
    try {
      await this.api.revokeCode(c.id);
      this.toast.success('Code revoked.');
      this.codes.reload();
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    }
  }
}
