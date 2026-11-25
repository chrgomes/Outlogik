import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { catchError, of } from 'rxjs';

/**
 * Whether anyone can create an account, and whether it takes an invitation code (the beta).
 * The API says which. Used by the sign-in and register pages only.
 */
@Injectable({ providedIn: 'root' })
export class SignupStatus {
  private readonly site = toSignal(
    inject(HttpClient).get<{ signup_open: boolean; signup_code_required?: boolean }>('/api/v1/public/site').pipe(
      catchError(() => of({ signup_open: false, signup_code_required: false })),
    ),
    { initialValue: { signup_open: false, signup_code_required: false } },
  );
  readonly open = computed(() => this.site().signup_open);
  readonly codeRequired = computed(() => !!this.site().signup_code_required);
}
