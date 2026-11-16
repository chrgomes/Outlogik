import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';
import { CurrentOrgService } from './current-org.service';

/** Signed-in users only; others go to /login and come back afterwards. */
export const authGuard: CanActivateFn = async (_route, state) => {
  const router = inject(Router);
  const me = await inject(AuthService).ensureLoaded();
  return me ? true : router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
};

/** Signed-out users only (sign-in, sign-up); signed-in users go home. */
export const guestGuard: CanActivateFn = async () => {
  const me = await inject(AuthService).ensureLoaded();
  return me ? inject(Router).createUrlTree(['/']) : true;
};

/** "/" → the first organization, or a page explaining there are none. */
export const homeRedirect: CanActivateFn = async () => {
  const router = inject(Router);
  const me = await inject(AuthService).ensureLoaded();
  if (!me) return router.createUrlTree(['/login']);
  const first = me.memberships[0];
  if (first) return router.createUrlTree(['/o', first.organization_slug]);
  return router.createUrlTree([me.user.platform_role === 'site_admin' ? '/admin' : '/no-organization']);
};

/**
 * /o/:orgSlug must be one of the user's organizations. Guards on one route run side by side,
 * so this waits for /me itself rather than relying on authGuard having finished.
 */
export const orgGuard: CanActivateFn = async (route) => {
  const slug = route.paramMap.get('orgSlug');
  const router = inject(Router);
  const currentOrg = inject(CurrentOrgService);
  const me = await inject(AuthService).ensureLoaded();
  if (!me) return false; // authGuard redirects to sign-in
  if (!me.memberships.some((m) => m.organization_slug === slug)) {
    return router.createUrlTree(['/not-found']);
  }
  currentOrg.slug.set(slug);
  currentOrg.area.set('org');
  return true;
};

/**
 * /admin: Outlogik site admins only. Everyone else sees "not found", matching the API, which
 * answers 404 so the admin area doesn't reveal itself.
 */
export const siteAdminGuard: CanActivateFn = async (_route, state) => {
  const router = inject(Router);
  const currentOrg = inject(CurrentOrgService); // before any await: inject() needs the guard's context
  const me = await inject(AuthService).ensureLoaded();
  if (!me) return router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
  if (me.user.platform_role !== 'site_admin') return router.createUrlTree(['/not-found']);
  currentOrg.area.set('admin');
  return true;
};

/** Pages that need a permission show "no access" instead (the API also refuses). */
export const permissionGuard: CanActivateFn = (route) => {
  const needed = route.data['permission'] as string | undefined;
  const org = inject(CurrentOrgService);
  if (!needed || org.can(needed)) return true;
  return inject(Router).createUrlTree(['/o', org.slug(), 'no-access']);
};
