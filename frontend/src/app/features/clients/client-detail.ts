import { DatePipe } from '@angular/common';
import { HttpErrorResponse, httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { CdkMenu, CdkMenuItem, CdkMenuTrigger } from '@angular/cdk/menu';
import { Router, RouterLink } from '@angular/router';

import { apiProblem } from '../../core/api-errors';
import { Client, ClientUser, Invitation, Page, Website } from '../../core/api.types';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi, queryParams } from '../../core/org-api.service';
import { DialogService } from '../../shared/dialog/dialog';
import { Icon } from '../../shared/icon/icon';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { Can, Status } from '../../shared/table/table-parts';
import { ToastService } from '../../shared/toast/toast';
import { InviteDialog } from '../settings/invite-dialog';
import { WebsiteFormDialog } from '../websites/website-form-dialog';
import { ClientFormDialog } from './client-form-dialog';
import { LinkUserDialog } from './link-user-dialog';

@Component({
  selector: 'ol-client-detail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, RouterLink, CdkMenuTrigger, CdkMenu, CdkMenuItem, PageHeader, EmptyState,
    ErrorState, LoadingState, Can, Status, Icon],
  template: `
    <a [routerLink]="['/o', org.slug(), 'clients']" class="back-link">
      <ol-icon name="arrow-left" /> Clients
    </a>

    @if (client.error()) {
      @if (notFound()) {
        <ol-empty-state icon="briefcase" title="Client not found"
          message="It may have been deleted, or you don't have access to it." />
      } @else {
        <ol-error-state message="We couldn't load this client." (retry)="client.reload()" />
      }
    } @else if (client.hasValue()) {
      @let c = client.value();
      <ol-page-header [title]="c.name" [description]="c.contact_email ?? undefined">
        <div actions class="d-flex align-items-center gap-2">
          <ol-status [value]="c.status" />
          @if (org.can('clients.write') || org.can('clients.delete')) {
            <button *olCan="'clients.write'" type="button" class="btn btn-outline-secondary" (click)="edit(c)">
              Edit
            </button>
            <button type="button" class="icon-action" [cdkMenuTriggerFor]="more" aria-label="More actions">
              <ol-icon name="three-dots" />
            </button>
            <ng-template #more>
              <div class="ol-menu" cdkMenu>
                @if (org.can('clients.write')) {
                  <button type="button" class="ol-menu-item" cdkMenuItem (cdkMenuItemTriggered)="toggleArchive(c)">
                    {{ c.status === 'archived' ? 'Restore client' : 'Archive client' }}
                  </button>
                }
                @if (org.can('clients.delete')) {
                  <button type="button" class="ol-menu-item text-danger" cdkMenuItem (cdkMenuItemTriggered)="remove(c)">
                    Delete client…
                  </button>
                }
              </div>
            </ng-template>
          }
        </div>
      </ol-page-header>

      @if (c.notes) {
        <section class="notes">
          <h2 class="h6 text-muted mb-1">Internal notes</h2>
          <p class="mb-0">{{ c.notes }}</p>
        </section>
      }

      <!-- Websites -->
      <section class="ol-section">
        <header>
          <h2>Websites</h2>
          <button *olCan="'websites.write'" type="button" class="btn btn-sm btn-outline-secondary" (click)="addWebsite(c)">
            <ol-icon name="plus-lg" /> Add website
          </button>
        </header>
        @if (websites.hasValue()) {
          @if (websites.value().items.length === 0) {
            <ol-empty-state icon="globe2" title="No websites yet" message="Add this client's websites to track them." />
          } @else {
            <div class="ol-table-card">
              <table class="table ol-table">
                <thead><tr><th>Website</th><th>Status</th><th>Added</th></tr></thead>
                <tbody>
                  @for (w of websites.value().items; track w.id) {
                    <tr>
                      <td>
                        <span class="fw-medium">{{ w.name }}</span>
                        <a class="d-block small text-muted" [href]="w.url" target="_blank" rel="noopener noreferrer">{{ w.url }}</a>
                      </td>
                      <td><ol-status [value]="w.status" /></td>
                      <td class="text-muted text-nowrap">{{ w.created_at | date: 'mediumDate' }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        } @else if (websites.error()) {
          <ol-error-state message="We couldn't load the websites." (retry)="websites.reload()" />
        } @else {
          <ol-loading-state />
        }
      </section>

      <!-- Client-portal access -->
      @if (org.can('client_users.manage')) {
        <section class="ol-section">
          <header>
            <div>
              <h2>Client portal access</h2>
              <p class="text-muted small mb-0">People at {{ c.name }} who can sign in and see this client's websites.</p>
            </div>
            <div class="d-flex gap-2">
              <button type="button" class="btn btn-sm btn-outline-secondary" (click)="linkUser(c)">Add existing</button>
              <button *olCan="'members.invite'" type="button" class="btn btn-sm btn-outline-secondary" (click)="inviteUser(c)">
                <ol-icon name="plus-lg" /> Invite
              </button>
            </div>
          </header>
          @if (users.hasValue()) {
            @if (users.value().length === 0) {
              <ol-empty-state icon="people" title="Nobody has portal access"
                message="Invite someone from this client to give them read-only access." />
            } @else {
              <div class="ol-table-card">
                <table class="table ol-table">
                  <thead><tr><th>Person</th><th>Access since</th><th><span class="visually-hidden">Actions</span></th></tr></thead>
                  <tbody>
                    @for (u of users.value(); track u.user_id) {
                      <tr>
                        <td><span class="fw-medium">{{ u.full_name }}</span><span class="d-block small text-muted">{{ u.email }}</span></td>
                        <td class="text-muted text-nowrap">{{ u.linked_at | date: 'mediumDate' }}</td>
                        <td class="text-end">
                          <button type="button" class="btn btn-sm btn-link text-danger" (click)="unlink(c, u)">Remove access</button>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            }
          } @else if (users.error()) {
            <ol-error-state message="We couldn't load portal access." (retry)="users.reload()" />
          } @else {
            <ol-loading-state />
          }
        </section>
      }
    } @else {
      <ol-loading-state label="Loading client…" />
    }
  `,
  styles: `
    .back-link { display: inline-flex; align-items: center; gap: 0.375rem; margin-bottom: 1rem;
      color: var(--ol-text-muted); text-decoration: none; font-size: 0.875rem; }
    .back-link:hover { color: var(--ol-text-strong); }
    .notes { padding: 1rem 1.25rem; border-radius: var(--bs-border-radius-lg); background: var(--ol-surface);
      white-space: pre-line; }
  `,
})
export class ClientDetail {
  protected readonly org = inject(CurrentOrgService);
  private readonly api = inject(OrgApi);
  private readonly dialogs = inject(DialogService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);

  readonly clientId = input.required<string>();
  protected readonly client = httpResource<Client>(() => this.api.url(`clients/${this.clientId()}`));
  protected readonly websites = httpResource<Page<Website>>(() => ({
    url: this.api.url('websites'),
    params: queryParams({ client_id: this.clientId(), page_size: 100 }),
  }));
  protected readonly users = httpResource<ClientUser[]>(() =>
    this.org.can('client_users.manage') ? this.api.url(`clients/${this.clientId()}/users`) : undefined);
  protected readonly notFound = computed(
    () => (this.client.error() as HttpErrorResponse | undefined)?.status === 404);
  private readonly busy = signal(false);

  protected async edit(c: Client): Promise<void> {
    const saved = await this.dialogs.open<Client>(ClientFormDialog, { client: c });
    if (saved) {
      this.client.set(saved);
      this.toast.success('Changes saved.');
    }
  }

  protected async toggleArchive(c: Client): Promise<void> {
    const status = c.status === 'archived' ? 'active' : 'archived';
    await this.run(async () => {
      this.client.set(await this.api.updateClient(c.id, { status }));
      this.toast.success(status === 'archived' ? `${c.name} archived.` : `${c.name} restored.`);
    });
  }

  protected async remove(c: Client): Promise<void> {
    const ok = await this.dialogs.confirm({
      title: `Delete ${c.name}?`,
      message: `This permanently deletes the client, its ${c.website_count} website(s) and everyone's portal access to it. It can't be undone. To keep the history, archive it instead.`,
      confirmLabel: 'Delete client', danger: true, typeToConfirm: c.name,
    });
    if (!ok) return;
    await this.run(async () => {
      await this.api.deleteClient(c.id);
      this.toast.success(`${c.name} deleted.`);
      await this.router.navigate(['/o', this.org.slug(), 'clients']);
    });
  }

  protected async addWebsite(c: Client): Promise<void> {
    const site = await this.dialogs.open<Website>(WebsiteFormDialog, { clientId: c.id });
    if (site) {
      this.websites.reload();
      this.client.reload();
      this.toast.success(`${site.name} added.`);
    }
  }

  protected async inviteUser(c: Client): Promise<void> {
    const inv = await this.dialogs.open<Invitation>(InviteDialog, { client: { id: c.id, name: c.name } });
    if (inv) this.toast.success(`Invitation sent to ${inv.email}.`);
  }

  protected async linkUser(c: Client): Promise<void> {
    const linkedUserIds = (this.users.value() ?? []).map((u) => u.user_id);
    if (await this.dialogs.open<boolean>(LinkUserDialog, { clientId: c.id, linkedUserIds })) {
      this.users.reload();
      this.toast.success('Access given.');
    }
  }

  protected async unlink(c: Client, u: ClientUser): Promise<void> {
    const ok = await this.dialogs.confirm({
      title: `Remove ${u.full_name}'s access?`,
      message: `They won't see ${c.name} in the client portal any more. They stay in the organization.`,
      confirmLabel: 'Remove access', danger: true,
    });
    if (!ok) return;
    await this.run(async () => {
      await this.api.unlinkClientUser(c.id, u.user_id);
      this.users.reload();
      this.toast.success('Access removed.');
    });
  }

  private async run(action: () => Promise<void>): Promise<void> {
    if (this.busy()) return;
    this.busy.set(true);
    try {
      await action();
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    } finally {
      this.busy.set(false);
    }
  }
}

