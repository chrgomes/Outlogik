import { ApplicationConfig, mergeApplicationConfig } from '@angular/core';
import { provideServerRendering, withRoutes } from '@angular/ssr';

import { appConfig } from './app.config';
import { serverRoutes } from './app.routes.server';

// While rendering, HttpClient resolves relative URLs such as /api/public/site against this
// site, so the request goes through the proxy in server.ts. The browser uses the same URL, which
// lets it reuse the response embedded in the page instead of fetching it again.
const serverConfig: ApplicationConfig = {
  providers: [provideServerRendering(withRoutes(serverRoutes))],
};

export const config = mergeApplicationConfig(appConfig, serverConfig);
