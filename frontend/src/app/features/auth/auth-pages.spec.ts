import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router, withComponentInputBinding } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { me, membership } from '../../../testing/fixtures';
import { AuthService } from '../../core/auth.service';
import { AcceptInvite } from './accept-invite';
import { Login } from './login';
import { Register } from './register';
import { ResetPassword } from './reset-password';

const API = '/api/v1/auth';

function setup() {
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      provideRouter([
        { path: 'login', component: Login },
        { path: 'register', component: Register },
        { path: 'reset-password', component: ResetPassword },
        { path: 'accept-invite', component: AcceptInvite },
        { path: '**', children: [] },
      ], withComponentInputBinding()), // as in app.config.ts
    ],
  });
  return TestBed.inject(HttpTestingController);
}

function type(el: HTMLElement, selector: string, value: string) {
  const input = el.querySelector<HTMLInputElement>(selector)!;
  input.value = value;
  input.dispatchEvent(new Event('input'));
}

const settle = () => new Promise((r) => setTimeout(r));

describe('Login page', () => {
  it('signs in and goes to the return URL', async () => {
    const http = setup();
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/login?returnUrl=%2Fo%2Facme%2Fclients');
    const el = harness.routeNativeElement!;
    type(el, '#email', 'olive@acme.example.com');
    type(el, '#password', 'correct horse battery');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    const req = http.expectOne(`${API}/login`);
    expect(req.request.body).toEqual({ email: 'olive@acme.example.com', password: 'correct horse battery' });
    req.flush(me());
    await settle();
    expect(TestBed.inject(Router).url).toBe('/o/acme/clients');
    expect(TestBed.inject(AuthService).user()?.email).toBe('olive@acme.example.com');
  });

  it('never redirects off-site after sign-in', async () => {
    const http = setup();
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/login?returnUrl=https:%2F%2Fevil.example.com');
    const el = harness.routeNativeElement!;
    type(el, '#email', 'olive@acme.example.com');
    type(el, '#password', 'x');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    http.expectOne(`${API}/login`).flush(me());
    await settle();
    expect(TestBed.inject(Router).url).toBe('/');
  });

  it('shows the server error and clears the password', async () => {
    const http = setup();
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/login');
    const el = harness.routeNativeElement!;
    type(el, '#email', 'olive@acme.example.com');
    type(el, '#password', 'wrong');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    http.expectOne(`${API}/login`).flush(
      { error: { code: 'invalid_credentials', message: 'Incorrect email or password.', details: null } },
      { status: 401, statusText: 'Unauthorized' });
    await settle();
    harness.detectChanges();
    expect(el.querySelector('.alert-danger')!.textContent).toContain('Incorrect email or password.');
    expect(el.querySelector<HTMLInputElement>('#password')!.value).toBe('');
  });

  it('does not submit an empty form', async () => {
    const http = setup();
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/login');
    harness.routeNativeElement!.querySelector('form')!.dispatchEvent(new Event('submit'));
    harness.detectChanges();
    http.expectNone(`${API}/login`);
    expect(harness.routeNativeElement!.textContent).toContain('This field is required.');
  });
});

describe('Invite-only sign-up', () => {
  it('sign-in page asks for an invitation instead of offering sign-up', async () => {
    const http = setup();
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/login');
    http.expectOne('/api/v1/public/site').flush({ signup_open: false });
    harness.detectChanges();
    const el = harness.routeNativeElement!;
    expect(el.querySelector('a[href="/register"]')).toBeNull();
    expect(el.textContent).toContain('Ask your Outlogik contact for an invitation');
  });

  it('register page explains accounts are by invitation', async () => {
    const http = setup();
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/register');
    http.expectOne('/api/v1/public/site').flush({ signup_open: false });
    harness.detectChanges();
    const el = harness.routeNativeElement!;
    expect(el.querySelector('form')).toBeNull();
    expect(el.textContent).toContain('Accounts are by invitation');
  });
});

describe('Register page', () => {
  it('shows "email taken" on the email field with a sign-in link', async () => {
    const http = setup();
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/register');
    http.expectOne('/api/v1/public/site').flush({ signup_open: true });
    harness.detectChanges();
    const el = harness.routeNativeElement!;
    type(el, '#full_name', 'Olive');
    type(el, '#organization_name', 'Acme');
    type(el, '#email', 'olive@acme.example.com');
    type(el, '#password', 'correct horse battery');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    http.expectOne(`${API}/register`).flush(
      { error: { code: 'email_taken', message: 'An account with this email already exists.', details: null } },
      { status: 409, statusText: 'Conflict' });
    await settle();
    harness.detectChanges();
    expect(el.querySelector('#email')!.classList).toContain('is-invalid');
    expect(el.textContent).toContain('An account with this email already exists.');
    expect(el.querySelector('a[href="/login"]')).not.toBeNull();
  });

  it('creates the account and opens the new organization', async () => {
    const http = setup();
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/register');
    http.expectOne('/api/v1/public/site').flush({ signup_open: true });
    harness.detectChanges();
    const el = harness.routeNativeElement!;
    type(el, '#full_name', 'Olive');
    type(el, '#organization_name', 'Acme');
    type(el, '#email', 'olive@acme.example.com');
    type(el, '#password', 'correct horse battery');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    http.expectOne(`${API}/register`).flush(me([membership({ organization_slug: 'acme' })]));
    await settle();
    expect(TestBed.inject(Router).url).toBe('/o/acme');
  });
});

describe('Reset password page', () => {
  it('requires matching passwords and removes the token from the URL', async () => {
    const http = setup();
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/reset-password?token=tok-123');
    await settle();
    expect(TestBed.inject(Router).url).toBe('/reset-password');
    const el = harness.routeNativeElement!;
    type(el, '#password', 'a long new password');
    type(el, '#confirm', 'something else');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    harness.detectChanges();
    http.expectNone(`${API}/reset-password`);
    expect(el.textContent).toContain("The passwords don't match.");

    type(el, '#confirm', 'a long new password');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    const req = http.expectOne(`${API}/reset-password`);
    expect(req.request.body).toEqual({ token: 'tok-123', password: 'a long new password' });
    req.flush({ message: 'ok' });
    await settle();
    expect(TestBed.inject(Router).url).toBe('/login?reset=1');
  });
});

describe('Accept invitation page', () => {
  const preview = (over = {}) => ({
    email: 'new@example.com', organization_name: 'Acme', organization_slug: 'acme',
    role_name: 'Team Member', client_name: null, invited_by: 'Olive', account_exists: false,
    expires_at: '2026-11-21T00:00:00Z', ...over,
  });

  async function open(http: HttpTestingController, signedIn: ReturnType<typeof me> | null, inv: object) {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/accept-invite?token=tok-1');
    const meReq = http.expectOne(`${API}/me`);
    if (signedIn) meReq.flush(signedIn);
    else meReq.flush(null, { status: 401, statusText: 'Unauthorized' });
    http.expectOne(`${API}/invitations/preview`).flush(inv);
    await settle();
    harness.detectChanges();
    return harness;
  }

  it('new invitee creates an account and lands in the organization', async () => {
    const http = setup();
    const harness = await open(http, null, preview());
    const el = harness.routeNativeElement!;
    expect(el.textContent).toContain('Join Acme');
    type(el, '#full_name', 'Nina New');
    type(el, '#password', 'correct horse battery');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    const req = http.expectOne(`${API}/accept-invite`);
    expect(req.request.body).toEqual({ token: 'tok-1', full_name: 'Nina New',
      password: 'correct horse battery' });
    req.flush(me());
    await settle();
    expect(TestBed.inject(Router).url).toBe('/o/acme');
  });

  it('existing account, signed out: asks to sign in and come back', async () => {
    const http = setup();
    const harness = await open(http, null, preview({ account_exists: true }));
    const link = harness.routeNativeElement!.querySelector('a.btn-primary')!;
    expect(link.getAttribute('href')).toBe('/login?returnUrl=%2Faccept-invite%3Ftoken%3Dtok-1');
  });

  it('signed in as someone else: offers to switch account', async () => {
    const http = setup();
    const harness = await open(http, me(), preview({ account_exists: true }));
    expect(harness.routeNativeElement!.textContent).toContain('but this invitation is for');
  });

  it('signed in as the invitee: one click to accept', async () => {
    const http = setup();
    const signed = me();
    signed.user.email = 'new@example.com';
    const harness = await open(http, signed, preview({ account_exists: true }));
    const button = harness.routeNativeElement!.querySelector<HTMLButtonElement>('button.btn-primary')!;
    expect(button.textContent).toContain('Accept invitation');
    button.click();
    expect(http.expectOne(`${API}/accept-invite`).request.body).toEqual({ token: 'tok-1' });
  });

  it('explains an invalid or expired invitation', async () => {
    const http = setup();
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/accept-invite?token=bad');
    http.expectOne(`${API}/me`).flush(null, { status: 401, statusText: 'Unauthorized' });
    http.expectOne(`${API}/invitations/preview`).flush(
      { error: { code: 'invalid_token', message: 'x', details: null } },
      { status: 400, statusText: 'Bad Request' });
    await settle();
    harness.detectChanges();
    expect(harness.routeNativeElement!.textContent).toContain("This invitation doesn't work");
  });
});

