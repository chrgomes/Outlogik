import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';

import { apiProblem } from '../../core/api-errors';
import { PageHeader } from '../../shared/page-header/page-header';
import { ErrorState, LoadingState } from '../../shared/states/states';
import { ToastService } from '../../shared/toast/toast';
import { ADMIN_API, AdminApi, PortalFeature } from './admin-api';

/**
 * /admin/portal-features: the client-portal features listed on the website, and whether each
 * is available, in development, or hidden. Changes show on the website within about a minute.
 */
@Component({
  selector: 'ol-portal-features',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PageHeader, ErrorState, LoadingState],
  template: `
    <ol-page-header title="Portal features"
      description="What the website says the client portal can do. Only mark a feature available once clients can use it." />

    @if (features.error()) {
      <ol-error-state message="We couldn't load the features." (retry)="features.reload()" />
    } @else if (features.hasValue()) {
      <div class="ol-table-card">
        <table class="table ol-table align-middle">
          <thead><tr><th>Feature</th><th class="status-col">Shown on the website as</th></tr></thead>
          <tbody>
            @for (f of features.value(); track f.slug) {
              <tr>
                <td>
                  <strong class="d-block">{{ f.name }}</strong>
                  <small class="text-muted">{{ f.summary }}</small>
                </td>
                <td>
                  <select class="form-select" [attr.aria-label]="'Status of ' + f.name" [value]="f.status"
                    [disabled]="saving() === f.slug" (change)="setStatus(f, $any($event.target).value)">
                    <option value="available">Available</option>
                    <option value="in_development">In development</option>
                    <option value="hidden">Hidden</option>
                  </select>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      <p class="text-muted small mt-3">The website updates within about a minute of a change.</p>
    } @else {
      <ol-loading-state label="Loading features…" />
    }
  `,
  styles: `.status-col { width: 14rem; }`,
})
export class PortalFeatures {
  private readonly api = inject(AdminApi);
  private readonly toast = inject(ToastService);
  protected readonly saving = signal<string | null>(null);
  protected readonly features = httpResource<PortalFeature[]>(() => `${ADMIN_API}/site/portal-features`);

  protected async setStatus(f: PortalFeature, status: PortalFeature['status']): Promise<void> {
    this.saving.set(f.slug);
    try {
      const updated = await this.api.updateFeature(f.slug, { status });
      this.features.update((list) => list?.map((x) => (x.slug === f.slug ? updated : x)));
      this.toast.success(`${f.name}: ${status.replace('_', ' ')}.`);
    } catch (e) {
      this.toast.error(apiProblem(e).message);
      this.features.reload();
    } finally {
      this.saving.set(null);
    }
  }
}
