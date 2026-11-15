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
