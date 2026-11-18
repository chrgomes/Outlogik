import { HttpClient } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { apiProblem } from '../../core/api-errors';
import { GrantPreview, Membership } from '../../core/api.types';
import { AuthService } from '../../core/auth.service';
import { prefs } from '../../core/storage';
import { takeLinkToken } from '../auth/link-token';

const API = '/api/v1/access-grants';

/**
 * Opened from the email a business sends: someone at an agency accepts access to the
 * business's workspace, into one of their agencies.
 */
@Component({
  selector: 'ol-accept-access',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink],
  template: `
    @if (error()) {
      <h1 class="h4 mb-2">This link can't be used</h1>
      <p class="text-muted">{{ error() }}</p>
      <a routerLink="/" class="btn btn-primary w-100">Go to Outlogik</a>
    } @else if (preview(); as p) {
      <h1 class="h4 mb-1">{{ p.business_name }} shared their workspace</h1>
      <p class="text-muted mb-4">
        {{ p.invited_by ?? 'Someone' }} at {{ p.business_name }} gave your agency
        {{ p.access === 'manage' ? 'access to work on' : 'view-only access to' }} their marketing workspace:
        websites and results. Nothing is copied, and they can end it at any time.
      </p>
      @if (p.agencies.length === 0) {
        <div class="alert alert-warning" role="alert">
          You can't accept this for an agency: you need to be an owner or administrator of an agency account
          on Outlogik. Ask your agency's owner to accept it, or to give you that role.
        </div>
      } @else {
        <form (ngSubmit)="accept()">
          @if (p.agencies.length > 1) {
            <div class="mb-3">
              <label for="agency" class="form-label">Which agency is it for?</label>
              <select id="agency" class="form-select" name="agency" [(ngModel)]="agencyId">
                @for (a of p.agencies; track a.organization_id) {
                  <option [value]="a.organization_id">{{ a.name }}</option>
                }
              </select>
            </div>
          } @else {
            <p class="mb-3">It will appear in <strong>{{ p.agencies[0].name }}</strong>'s workspaces.</p>
          }
          <button type="submit" class="btn btn-primary w-100" [disabled]="busy()">
            @if (busy()) {<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>}
            Accept access
          </button>
        </form>
      }
    } @else {
      <p class="text-muted" role="status">Checking the link…</p>
    }
  `,
})
export class AcceptAccess {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly token = takeLinkToken();

  protected readonly preview = signal<GrantPreview | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly busy = signal(false);
  protected agencyId = '';

  constructor() {
    if (!this.token) {
      this.error.set('The link is missing its code. Open it again from the email.');
      return;
    }
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      const p = await firstValueFrom(this.http.post<GrantPreview>(`${API}/preview`, { token: this.token }));
      this.agencyId = p.agencies[0]?.organization_id ?? '';
      this.preview.set(p);
    } catch (err) {
      this.error.set(apiProblem(err).message);
    }
  }

  protected async accept(): Promise<void> {
    const p = this.preview();
    if (!p || !this.agencyId) return;
    this.busy.set(true);
    try {
      const memberships = await firstValueFrom(this.http.post<Membership[]>(
        `${API}/accept`, { token: this.token, organization_id: this.agencyId }));
      await this.auth.refresh();
      const agency = memberships.find((m) => m.organization_id === this.agencyId);
      if (agency) {
        prefs.set(`ol.workspace.${agency.organization_slug}`, '');
        await this.router.navigate(['/o', agency.organization_slug, 'websites']);
      }
    } catch (err) {
      this.error.set(apiProblem(err).message);
    } finally {
      this.busy.set(false);
    }
  }
}
