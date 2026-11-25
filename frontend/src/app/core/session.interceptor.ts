import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthService } from './auth.service';

/**
 * When any API call says the session is gone (401), drop it locally and go to sign-in. When it
 * says the organization was suspended meanwhile (403 org_suspended), reload who we are and show
 * the suspended page.
 */
export const sessionInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return next(req).pipe(
    catchError((err: unknown) => {
      const isAuthCall = req.url.startsWith('/api/v1/auth/');
      if (err instanceof HttpErrorResponse && err.status === 401 && !isAuthCall && auth.me()) {
        auth.clear();
        void router.navigate(['/login'], {
          queryParams: { returnUrl: router.url, reason: 'expired' },
        });
      }
      if (err instanceof HttpErrorResponse && err.status === 403 && err.error?.error?.code === 'org_suspended') {
        const slug = /^\/api\/v1\/orgs\/([^/]+)/.exec(req.url)?.[1];
        if (slug) void auth.refresh().then(() => router.navigate(['/suspended', slug]));
      }
      return throwError(() => err);
    }),
  );
};
