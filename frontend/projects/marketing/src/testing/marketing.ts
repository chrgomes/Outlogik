import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { provideIcons } from '@brand/icon/icon';
import { MARKETING_ICONS } from '@brand/icon/icons-marketing';
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

