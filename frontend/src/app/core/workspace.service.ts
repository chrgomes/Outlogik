import { httpResource } from '@angular/common/http';
import { Injectable, computed, inject, linkedSignal } from '@angular/core';

import { Workspace } from './api.types';
import { CurrentOrgService } from './current-org.service';
import { prefs } from './storage';

const KEY = 'ol.workspace.';

/**
 * The workspaces the user can open in the current organization, and which one is selected.
 *
 * - A business has one workspace, its own, which is always selected.
 * - An agency picks one in the top bar (its own, or a client's), or "All workspaces" (null).
 *   The choice is remembered per organization in this browser.
 */
@Injectable({ providedIn: 'root' })
export class WorkspaceService {
  private readonly org = inject(CurrentOrgService);

  readonly list = httpResource<Workspace[]>(() => {
    const slug = this.org.slug();
    return this.org.area() === 'org' && slug ? `/api/v1/orgs/${slug}/workspaces` : undefined;
  });
  private readonly workspaces = computed(() => (this.list.hasValue() ? this.list.value() : []));
  /** The own workspace first, then clients' (the API's order). */
  readonly own = computed(() => this.workspaces().find((w) => w.kind === 'own') ?? null);
  readonly clients = computed(() => this.workspaces().filter((w) => w.kind === 'client'));

  private readonly selectedId = linkedSignal(() => prefs.get(KEY + this.org.slug()));

  /** The selected workspace, or null for all of them (agencies only). */
  readonly current = computed<Workspace | null>(() => {
    if (!this.org.isAgency()) return this.own();
    const id = this.selectedId();
    return this.workspaces().find((w) => w.id === id) ?? null;
  });
  /** Agencies with more than one workspace get the switcher. */
  readonly canSwitch = computed(() => this.org.isAgency() && this.workspaces().length > 1);

  select(id: string | null): void {
    this.selectedId.set(id);
    prefs.set(KEY + this.org.slug(), id ?? '');
  }
}
