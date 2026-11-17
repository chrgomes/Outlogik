import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { TitleStrategy, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { provideIcons } from '@brand/icon/icon';
import { MARKETING_ICONS } from '@brand/icon/icons-marketing';
import { routes } from '../app/app.routes';
import { SeoTitleStrategy } from '../app/seo/seo';
import { DEFAULT_SETTINGS } from '../app/config/site';

/** TestBed for marketing components: router, icons and mocked HTTP. */
export function setupMarketing() {
  TestBed.configureTestingModule({
    providers: [
      provideRouter([{ path: '**', children: [] }]),
      provideIcons(MARKETING_ICONS),
      provideHttpClient(),
      provideHttpClientTesting(),
    ],
  });
}

/** Let pending effects and requests run. */
export const settle = () => new Promise((r) => setTimeout(r));

/** Answer the site-data request the header, footer and pages make. */
export function answerSite(over: object = {}) {
  TestBed.inject(HttpTestingController).expectOne('/api/public/site').flush({
    settings: DEFAULT_SETTINGS, portal_features: [], signup_open: false, ...over,
  });
}


/**
 * Render a page through the site's real routes. Pass `features` to answer the site-data request
 * with those portal features; otherwise it stays pending and the built-in defaults are shown.
 */
export async function visit(url: string, features?: object[]): Promise<HTMLElement> {
  TestBed.configureTestingModule({
    providers: [
      provideRouter(routes),
      { provide: TitleStrategy, useClass: SeoTitleStrategy },
      provideIcons(MARKETING_ICONS),
      provideHttpClient(),
      provideHttpClientTesting(),
    ],
  });
  const harness = await RouterTestingHarness.create(url);
  TestBed.tick(); // let the SEO effect write the page's tags
  if (features) {
    answerSite({ portal_features: features });
    await settle();
    harness.detectChanges();
  }
  return harness.routeNativeElement as HTMLElement;
}

/** Phrases the copy must never contain (spec §19: no guarantees, no invented proof). */
export const FORBIDDEN_CLAIMS =
  /we guarantee|guaranteed|#1|number one|top of google|testimonial|case stud|trusted by|% increase/;

/** A tiny proof-of-work challenge (the answer is 7), for tests that send a form. */
export const TEST_CHALLENGE = {
  algorithm: 'SHA-256', salt: 'test-salt?expires=9999999999', max_number: 10, signature: 'sig',
  challenge: 'b2dbdfed6beab78907603daf70bc361044e680308f81282db32c88dbd4dab5f5',
};

/** Answers the form's challenge request and waits for the browser to solve it. */
export async function answerChallenge(): Promise<void> {
  await settle();
  TestBed.inject(HttpTestingController).expectOne('/api/public/challenge').flush(TEST_CHALLENGE);
  for (let i = 0; i < 10; i++) await settle(); // hashing is asynchronous
}
