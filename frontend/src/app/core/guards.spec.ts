import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import {
  ActivatedRouteSnapshot,
  convertToParamMap,
  provideRouter,
  Router,
  RouterStateSnapshot,
  UrlTree,
} from '@angular/router';

import { me, membership } from '../../testing/fixtures';
import { AuthService } from './auth.service';
import { CurrentOrgService } from './current-org.service';
import { authGuard, homeRedirect, orgGuard, permissionGuard } from './guards';

describe('route guards', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });

  const run = <T>(fn: () => T) => TestBed.runInInjectionContext(fn);
  const url = (tree: unknown) => TestBed.inject(Router).serializeUrl(tree as UrlTree);
  const state = (u: string) => ({ url: u }) as RouterStateSnapshot;
  const route = (params: Record<string, string> = {}, data: Record<string, unknown> = {}) =>
    ({ paramMap: convertToParamMap(params), data }) as unknown as ActivatedRouteSnapshot;

  it('sends signed-out users to /login with a return URL', async () => {
    const result = run(() => authGuard(route(), state('/o/acme/clients')));
    http.expectOne('/api/v1/auth/me').flush(null, { status: 401, statusText: 'Unauthorized' });
    expect(url(await result)).toBe('/login?returnUrl=%2Fo%2Facme%2Fclients');
  });

  it('lets signed-in users through', async () => {
    const result = run(() => authGuard(route(), state('/')));
    http.expectOne('/api/v1/auth/me').flush(me());
    expect(await result).toBe(true);
  });

  it('home goes to the first organization, or explains there is none', async () => {
    let result = run(() => homeRedirect(route(), state('/')));
    http.expectOne('/api/v1/auth/me').flush(me([membership({ organization_slug: 'globex' })]));
    expect(url(await result)).toBe('/o/globex');

    // Already loaded: later checks reuse the signed-in state without another request.
    TestBed.inject(AuthService).me.set(me([]));
    result = run(() => homeRedirect(route(), state('/')));
    expect(url(await result)).toBe('/no-organization');
    http.verify();
  });

  it('waits for the user on a fresh page load, then allows only their organizations', async () => {
    // Nothing loaded yet: a direct visit or reload of /o/acme/....
    const allowed = run(() => orgGuard(route({ orgSlug: 'acme' }), state('')));
    http.expectOne('/api/v1/auth/me').flush(me([membership({ organization_slug: 'acme' })]));
    expect(await allowed).toBe(true);
    expect(TestBed.inject(CurrentOrgService).slug()).toBe('acme');

    const denied = await run(() => orgGuard(route({ orgSlug: 'globex' }), state('')));
    expect(url(denied)).toBe('/not-found');
  });

  it('shows "no access" for pages the role lacks', () => {
    TestBed.inject(AuthService).me.set(
      me([membership({ organization_slug: 'acme', permissions: ['clients.read'] })]),
    );
    TestBed.inject(CurrentOrgService).slug.set('acme');
    const allowed = run(() => permissionGuard(route({}, { permission: 'clients.read' }), state('')));
    const denied = run(() => permissionGuard(route({}, { permission: 'roles.read' }), state('')));
    expect(allowed).toBe(true);
    expect(url(denied)).toBe('/o/acme/no-access');
  });
});
