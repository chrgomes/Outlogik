import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';

export type ApiStatus = 'checking' | 'ok' | 'degraded' | 'unreachable';

/** Temporary step-1 check that the frontend can reach the API through the dev proxy. */
@Injectable({ providedIn: 'root' })
export class ApiStatusService {
  private readonly http = inject(HttpClient);
  readonly status = signal<ApiStatus>('checking');

  check(): void {
    this.status.set('checking');
    this.http.get<{ status: string }>('/api/v1/health/ready').subscribe({
      next: (res) => this.status.set(res.status === 'ok' ? 'ok' : 'degraded'),
      error: (err) => this.status.set(err.status === 503 ? 'degraded' : 'unreachable'),
    });
  }
}
