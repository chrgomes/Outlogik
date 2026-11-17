import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Provider } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { AuthService } from '../app/core/auth.service';
import { CurrentOrgService } from '../app/core/current-org.service';
import { me, membership } from './fixtures';

export const ALL = [
  'organization.read', 'organization.update', 'members.read', 'members.invite', 'members.update',
  'members.remove', 'roles.read', 'roles.manage', 'clients.read', 'clients.write', 'clients.delete',
  'client_users.manage', 'websites.read', 'websites.write', 'websites.delete', 'dashboard.read',
];
export const CLIENT_PERMS = ['organization.read', 'clients.read', 'websites.read', 'dashboard.read'];

/** TestBed with HTTP mocks and a signed-in member of org "acme" with the given role. */
export function setupOrg(
  permissions: string[] = ALL,
  roleKey: string | null = 'owner',
  extraProviders: Provider[] = [],
): HttpTestingController {
  TestBed.configureTestingModule({
    providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), ...extraProviders],
  });
  TestBed.inject(AuthService).me.set(me([membership({ permissions, role_key: roleKey })]));
  TestBed.inject(CurrentOrgService).slug.set('acme');
  return TestBed.inject(HttpTestingController);
}

export const page = <T>(items: T[]) => ({ items, total: items.length, page: 1, page_size: 25 });

export async function flushPending(): Promise<void> {
  TestBed.tick();
  await new Promise((r) => setTimeout(r));
  TestBed.tick();
}

/** Answers the first pending request whose URL starts with `url`. */
export function answer(http: HttpTestingController, url: string, body: object | null): void {
  http.expectOne((r) => r.url === url).flush(body);
}

/** Providers a component opened as a CDK dialog expects. */
export function dialogProviders(data: unknown): Provider[] {
  return [
    { provide: DialogRef, useValue: { close: () => undefined } },
    { provide: DIALOG_DATA, useValue: data },
  ];
}

/** A tiny proof-of-work challenge (the answer is 7), for tests of the sign-in forms. */
export const TEST_CHALLENGE = {
  algorithm: 'SHA-256', salt: 'test-salt?expires=9999999999', max_number: 10, signature: 'sig',
  challenge: 'b2dbdfed6beab78907603daf70bc361044e680308f81282db32c88dbd4dab5f5',
};

/** Answers the sign-in form's challenge request and waits for it to be solved. */
export async function answerChallenge(http: HttpTestingController): Promise<void> {
  await new Promise((r) => setTimeout(r));
  http.expectOne('/api/v1/public/challenge').flush(TEST_CHALLENGE);
  for (let i = 0; i < 10; i++) await new Promise((r) => setTimeout(r));
}
