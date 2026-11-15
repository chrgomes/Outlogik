import {
  provideHttpClient,
  withFetch,
  withInterceptors,
  withXsrfConfiguration,
} from '@angular/common/http';
import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';

import { provideIcons } from '@brand/icon/icon';
import { APP_ICONS } from '@brand/icon/icons-app';

import { routes } from './app.routes';
import { AuthService } from './core/auth.service';
import { sessionInterceptor } from './core/session.interceptor';
import { ThemeService } from './core/theme.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideIcons(APP_ICONS),
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(
      withFetch(),
      // Double-submit CSRF: the API sets this cookie; Angular echoes it on state-changing
      // requests to same-origin URLs (the dev server proxies /api to FastAPI).
      withXsrfConfiguration({ cookieName: 'XSRF-TOKEN', headerName: 'X-XSRF-TOKEN' }),
      withInterceptors([sessionInterceptor]),
    ),
    provideAppInitializer(() => {
      inject(ThemeService); // apply the theme straight away
      return inject(AuthService).ensureCsrfCookie();
    }),
  ],
};
