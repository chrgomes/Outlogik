import { httpResource } from '@angular/common/http';
import { Injectable, computed } from '@angular/core';

import { DEFAULT_PORTAL_FEATURES, DEFAULT_SETTINGS, PortalFeature, SiteSettings } from './site';

interface PublicSite {
  settings: SiteSettings;
  portal_features: PortalFeature[];
  signup_open: boolean;
}

/**
 * Site settings and client-portal feature statuses, managed by Outlogik staff in the admin area.
 * Loaded once per page render (on the server, then handed to the browser). If the API can't be
 * reached the built-in defaults are used, so the site never breaks.
 */
@Injectable({ providedIn: 'root' })
export class SiteData {
  private readonly site = httpResource<PublicSite>(() => '/api/public/site');

  readonly settings = computed<SiteSettings>(() =>
    this.site.hasValue() ? { ...DEFAULT_SETTINGS, ...this.site.value().settings } : DEFAULT_SETTINGS);

  readonly portalFeatures = computed<PortalFeature[]>(() =>
    this.site.hasValue() ? this.site.value().portal_features : DEFAULT_PORTAL_FEATURES);
}
