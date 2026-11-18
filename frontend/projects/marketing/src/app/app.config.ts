import { provideHttpClient, withFetch } from '@angular/common/http';
import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideClientHydration, withEventReplay } from '@angular/platform-browser';
import { TitleStrategy, provideRouter, withInMemoryScrolling } from '@angular/router';

import { provideIcons } from '@brand/icon/icon';
import { MARKETING_ICONS } from '@brand/icon/icons-marketing';

import { routes } from './app.routes';
import { SeoTitleStrategy } from './seo/seo';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideIcons(MARKETING_ICONS),
    provideRouter(routes, withInMemoryScrolling({
      scrollPositionRestoration: 'enabled',
      anchorScrolling: 'enabled',
    })),
    { provide: TitleStrategy, useClass: SeoTitleStrategy },
    provideHttpClient(withFetch()),
    // Server-rendered HTML is reused, and clicks made before the JavaScript loads are replayed.
    provideClientHydration(withEventReplay()),
  ],
};
