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
  const staff = me.user.platform_role === 'site_admin' || (me.user.platform_caps ?? []).includes('platform.read');
  return router.createUrlTree([staff ? '/admin' : '/no-organization']);
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
  const membership = me.memberships.find((m) => m.organization_slug === slug);
  if (!membership) return router.createUrlTree(['/not-found']);
  if (membership.organization_status === 'suspended') return router.createUrlTree(['/suspended', slug]);
  currentOrg.slug.set(slug);
  currentOrg.area.set('org');
  return true;
};

/**
 * /admin: Outlogik staff only (the website admin, the platform area, or both). Everyone else
 * sees "not found", matching the API, which answers 404 so the admin area doesn't reveal itself.
 */
export const staffAreaGuard: CanActivateFn = async (_route, state) => {
  const router = inject(Router);
  const currentOrg = inject(CurrentOrgService); // before any await: inject() needs the guard's context
  const auth = inject(AuthService);
  const me = await auth.ensureLoaded();
  if (!me) return router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
  if (!auth.isStaff()) return router.createUrlTree(['/not-found']);
  currentOrg.area.set('admin');
  return true;
};

/** /admin pages for the website (leads, newsletter, settings): site admins only. */
export const websiteAdminGuard: CanActivateFn = () =>
  inject(AuthService).isSiteAdmin() || inject(Router).createUrlTree(['/admin']);

/** /admin/platform pages: staff with the capability in the route's data (default platform.read). */
export const platformGuard: CanActivateFn = (route) => {
  const cap = (route.data['cap'] as string | undefined) ?? 'platform.read';
  return inject(AuthService).platformCaps().has(cap) || inject(Router).createUrlTree(['/not-found']);
};

/** /admin → the first page this staff member can open. */
export const adminHomeRedirect: CanActivateFn = () => {
  const auth = inject(AuthService);
  return inject(Router).createUrlTree(['/admin', auth.isPlatformStaff() ? 'platform' : 'leads']);
};

/** Pages that need a permission show "no access" instead (the API also refuses). */
export const permissionGuard: CanActivateFn = (route) => {
  const needed = route.data['permission'] as string | undefined;
  const org = inject(CurrentOrgService);
  if (!needed || org.can(needed)) return true;
  return inject(Router).createUrlTree(['/o', org.slug(), 'no-access']);
};

/** Agency staff pages (clients, websites, organization settings): client-portal users go to
 * their dashboard instead. Their data stays limited by the API either way. */
export const staffGuard: CanActivateFn = () => {
  const org = inject(CurrentOrgService);
  return !org.isClientUser() || inject(Router).createUrlTree(['/o', org.slug(), 'dashboard']);
};

/** Agency-only pages (clients): a business account goes to its dashboard instead. */
export const agencyGuard: CanActivateFn = () => {
  const org = inject(CurrentOrgService);
  return org.isAgency() || inject(Router).createUrlTree(['/o', org.slug(), 'dashboard']);
};

/** Business-only pages (agency access): an agency goes to its dashboard instead. */
export const businessGuard: CanActivateFn = () => {
  const org = inject(CurrentOrgService);
  return !org.isAgency() || inject(Router).createUrlTree(['/o', org.slug(), 'dashboard']);
};
