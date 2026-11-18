import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { catchError, map, of } from 'rxjs';

/**
 * Whether anyone can create an account. Outlogik runs invite-only (clients are invited to their
 * portal); the API says which. Used by the sign-in and register pages only.
 */
@Injectable({ providedIn: 'root' })
export class SignupStatus {
  readonly open = toSignal(
    inject(HttpClient).get<{ signup_open: boolean }>('/api/v1/public/site').pipe(
      map((site) => site.signup_open),
      catchError(() => of(false)),
    ),
    { initialValue: false },
  );
}
