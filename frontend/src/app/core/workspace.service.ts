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
 * - A client-portal user always has one of their own workspaces selected, never "All": the
 *   portal shows a client their own dashboard, not the agency's overview (§7).
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
  /** The organization's own workspace, its clients', and businesses' shared with it. */
  readonly own = computed(() => this.workspaces().find((w) => w.kind === 'own' && !w.linked) ?? null);
  readonly clients = computed(() => this.workspaces().filter((w) => w.kind === 'client' && !w.linked));
  readonly linked = computed(() => this.workspaces().filter((w) => w.linked));

  private readonly selectedId = linkedSignal(() => prefs.get(KEY + this.org.slug()));

  /** Changes aren't allowed in the selected workspace (shared with view-only access). */
  readonly readOnly = computed(() => this.current()?.access === 'view');

  /** The selected workspace, or null for all of them (agency staff only). */
  readonly current = computed<Workspace | null>(() => {
    if (!this.org.isAgency()) return this.own();
    const id = this.selectedId();
    const selected = this.workspaces().find((w) => w.id === id);
    if (this.org.isClientUser()) return selected ?? this.workspaces()[0] ?? null;
    return selected ?? null;
  });
  /** Whether "All workspaces" is offered. */
  readonly canSeeAll = computed(() => !this.org.isClientUser());
  /** Agencies with more than one workspace get the switcher. */
  readonly canSwitch = computed(() => this.org.isAgency() && this.workspaces().length > 1);

  select(id: string | null): void {
    this.selectedId.set(id);
    prefs.set(KEY + this.org.slug(), id ?? '');
  }
}
