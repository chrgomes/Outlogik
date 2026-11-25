import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { me } from '../../testing/fixtures';
import { AuthService } from './auth.service';
import { sessionInterceptor } from './session.interceptor';

describe('sessionInterceptor', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([{ path: '**', children: [] }]),
        provideHttpClient(withInterceptors([sessionInterceptor])),
        provideHttpClientTesting(),
      ],
    });
  });

  it('sends the user to sign-in when the session has been revoked', async () => {
    const router = TestBed.inject(Router);
    await router.navigateByUrl('/o/acme/clients');
    TestBed.inject(AuthService).me.set(me());

    const call = firstValueFrom(TestBed.inject(HttpClient).get('/api/v1/orgs/acme/clients'));
    TestBed.inject(HttpTestingController).expectOne('/api/v1/orgs/acme/clients')
      .flush(null, { status: 401, statusText: 'Unauthorized' });
    await expect(call).rejects.toBeTruthy();
    await new Promise((r) => setTimeout(r));

    expect(TestBed.inject(AuthService).me()).toBeNull();
    expect(router.url).toBe('/login?returnUrl=%2Fo%2Facme%2Fclients&reason=expired');
  });

  it('leaves failed sign-in attempts to the page', async () => {
    const router = TestBed.inject(Router);
    await router.navigateByUrl('/login');
    const call = firstValueFrom(TestBed.inject(HttpClient).post('/api/v1/auth/login', {}));
    TestBed.inject(HttpTestingController).expectOne('/api/v1/auth/login')
      .flush(null, { status: 401, statusText: 'Unauthorized' });
    await expect(call).rejects.toBeTruthy();
    expect(router.url).toBe('/login');
  });
});

describe('sessionInterceptor: a suspended organization', () => {
  it('reloads who we are and shows the suspended page', async () => {
    const { TestBed } = await import('@angular/core/testing');
    const { provideHttpClient, withInterceptors, HttpClient } = await import('@angular/common/http');
    const { provideHttpClientTesting, HttpTestingController } = await import('@angular/common/http/testing');
    const { provideRouter, Router } = await import('@angular/router');
    const { firstValueFrom } = await import('rxjs');
    const { AuthService } = await import('./auth.service');
    const { sessionInterceptor } = await import('./session.interceptor');
    const { me } = await import('../../testing/fixtures');
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [provideHttpClient(withInterceptors([sessionInterceptor])),
      provideHttpClientTesting(), provideRouter([{ path: '**', children: [] }])] });
    TestBed.inject(AuthService).me.set(me());
    const http = TestBed.inject(HttpTestingController);
    const call = firstValueFrom(TestBed.inject(HttpClient).get('/api/v1/orgs/acme/websites')).catch(() => null);
    http.expectOne('/api/v1/orgs/acme/websites').flush(
      { error: { code: 'org_suspended', message: 'This organization is suspended.', details: null } },
      { status: 403, statusText: 'Forbidden' });
    await call;
    http.expectOne('/api/v1/auth/me').flush(me());
    await new Promise((r) => setTimeout(r));
    expect(TestBed.inject(Router).url).toBe('/suspended/acme');
  });
});
