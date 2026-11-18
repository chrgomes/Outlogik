import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, firstValueFrom } from 'rxjs';

import { FormProof } from '@brand/forms/proof-of-work';

import { InvitePreview, Me } from './api.types';

const API = '/api/v1/auth';

/** The signed-in user and their organizations. The session itself is an HTTP-only cookie. */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  readonly me = signal<Me | null>(null);

  readonly user = computed(() => this.me()?.user ?? null);
  readonly memberships = computed(() => this.me()?.memberships ?? []);
  /** Outlogik staff who can use the website admin area (/admin). */
  readonly isSiteAdmin = computed(() => this.user()?.platform_role === 'site_admin');
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

  // --- sign-in flows (each sets the signed-in user from the response) -----------------------

  /** The invisible browser check for one sign-in form; call prepare() when the form is used. */
  proof(): FormProof {
    return new FormProof(this.http, '/api/v1/public/challenge');
  }

  async login(email: string, password: string, proof?: FormProof): Promise<Me> {
    const pow = await (proof ?? this.proof()).take();
    return this.signedIn(this.http.post<Me>(`${API}/login`, { email, password, pow }));
  }

  async register(body: {
    email: string; password: string; full_name: string; organization_name: string;
  }): Promise<Me> {
    return this.signedIn(this.http.post<Me>(`${API}/register`, body));
  }

  async acceptInvite(body: { token: string; full_name?: string; password?: string }, proof?: FormProof): Promise<Me> {
    const pow = await (proof ?? this.proof()).take();
    return this.signedIn(this.http.post<Me>(`${API}/accept-invite`, { ...body, pow }));
  }

  previewInvite(token: string): Promise<InvitePreview> {
    return firstValueFrom(this.http.post<InvitePreview>(`${API}/invitations/preview`, { token }));
  }

  async forgotPassword(email: string, proof?: FormProof): Promise<unknown> {
    const pow = await (proof ?? this.proof()).take();
    return firstValueFrom(this.http.post(`${API}/forgot-password`, { email, pow }));
  }

  resetPassword(token: string, password: string): Promise<unknown> {
    return firstValueFrom(this.http.post(`${API}/reset-password`, { token, password }));
  }

  async verifyEmail(token: string): Promise<void> {
    await firstValueFrom(this.http.post(`${API}/verify-email`, { token }));
    if (this.me()) await this.refresh();
  }

  resendVerification(): Promise<unknown> {
    return firstValueFrom(this.http.post(`${API}/resend-verification`, {}));
  }

  private async signedIn(request: Observable<Me>): Promise<Me> {
    const me = await firstValueFrom(request);
    this.me.set(me);
    this.loaded = true;
    return me;
  }

  /** Forget the session locally (it has expired or been revoked server-side). */
  clear(): void {
    this.me.set(null);
    this.loaded = true;
  }

  async logout(everywhere = false, then = '/login'): Promise<void> {
    try {
      await firstValueFrom(this.http.post(`${API}/${everywhere ? 'logout-all' : 'logout'}`, {}));
    } finally {
      this.clear();
      await this.router.navigateByUrl(then);
    }
  }
}
