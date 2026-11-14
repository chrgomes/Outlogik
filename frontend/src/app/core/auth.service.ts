import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { Me } from './api.types';

const API = '/api/v1/auth';

/** The signed-in user and their organizations. The session itself is an HTTP-only cookie. */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  readonly me = signal<Me | null>(null);
  readonly user = computed(() => this.me()?.user ?? null);
  readonly memberships = computed(() => this.me()?.memberships ?? []);
  private loading: Promise<Me | null> | null = null;
  private loaded = false;

  /** Makes sure the CSRF cookie exists before the app sends any state-changing request. */
  ensureCsrfCookie(): Promise<unknown> {
    return firstValueFrom(this.http.get(`${API}/csrf`)).catch(() => null);
  }

  /** Loads /me once; later calls reuse the result. Resolves null when signed out. */
  ensureLoaded(): Promise<Me | null> {
    if (this.loaded) return Promise.resolve(this.me());
    this.loading ??= firstValueFrom(this.http.get<Me>(`${API}/me`))
      .then((me) => me, (err: HttpErrorResponse) => {
        if (err.status === 401) return null;
        throw err;
      })
      .then((me) => {
        this.me.set(me);
        this.loaded = true;
        return me;
      })
      .finally(() => (this.loading = null));
    return this.loading;
  }

  /** Re-fetch after anything that changes the user's memberships or profile. */
  refresh(): Promise<Me | null> {
    this.loaded = false;
    return this.ensureLoaded();
  }

  /** Forget the session locally (it has expired or been revoked server-side). */
  clear(): void {
    this.me.set(null);
    this.loaded = true;
  }

  async logout(everywhere = false): Promise<void> {
    try {
      await firstValueFrom(this.http.post(`${API}/${everywhere ? 'logout-all' : 'logout'}`, {}));
    } finally {
      this.clear();
      await this.router.navigateByUrl('/login');
    }
  }
}
