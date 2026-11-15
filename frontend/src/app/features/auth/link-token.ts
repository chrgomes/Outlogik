import { inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

/**
 * Reads ?token=… from an emailed link, then removes it from the address bar so it doesn't
 * linger in browser history or get copied into a shared URL. Call in a constructor.
 */
export function takeLinkToken(): string | null {
  const route = inject(ActivatedRoute);
  const router = inject(Router);
  const token = route.snapshot.queryParamMap.get('token');
  if (token) {
    void router.navigate([], {
      relativeTo: route,
      queryParams: { token: null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }
  return token;
}
