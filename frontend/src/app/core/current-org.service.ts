import { Injectable, computed, inject, signal } from '@angular/core';

import { AuthService } from './auth.service';

/** The organization in the URL (/o/:orgSlug) and what the user may do in it. */
@Injectable({ providedIn: 'root' })
export class CurrentOrgService {
  private readonly auth = inject(AuthService);

  readonly slug = signal<string | null>(null);
  readonly membership = computed(
    () => this.auth.memberships().find((m) => m.organization_slug === this.slug()) ?? null,
  );
  readonly permissions = computed(() => new Set(this.membership()?.permissions ?? []));
  readonly isOwner = computed(() => this.membership()?.role_key === 'owner');
  readonly isClientUser = computed(() => this.membership()?.role_key === 'client');

  /**
   * For showing or hiding UI only. The API enforces every permission itself.
   */
  can(permission: string): boolean {
    return this.permissions().has(permission);
  }
}
