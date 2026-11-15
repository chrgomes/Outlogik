import { httpResource } from '@angular/common/http';
import { Injectable, computed } from '@angular/core';

import { IconName } from '@brand/icon/icons';
import { DEFAULT_MODULES, DEFAULT_SETTINGS, ProductModule, SiteSettings } from './site';

interface PublicSite {
  settings: SiteSettings;
  modules: Omit<ProductModule, 'icon'>[];
}

const MODULE_ICONS: Record<string, IconName> = {
  'client-management': 'briefcase',
  'seo-management': 'search',
  'website-analytics': 'graph-up',
  'social-media-management': 'megaphone',
  'content-marketing': 'pencil-square',
  'marketing-analytics': 'bar-chart-line',
  reporting: 'file-earmark-bar-graph',
};

/**
 * Site settings and product module statuses, managed by Outlogik staff in the admin area.
 * Loaded once per page render (on the server, then handed to the browser). If the API can't be
 * reached the built-in defaults are used, so the site never breaks.
 */
@Injectable({ providedIn: 'root' })
export class SiteData {
  private readonly site = httpResource<PublicSite>(() => '/api/public/site');

  readonly settings = computed<SiteSettings>(() =>
    this.site.hasValue() ? this.site.value().settings : DEFAULT_SETTINGS);

  readonly modules = computed<ProductModule[]>(() =>
    this.site.hasValue()
      ? this.site.value().modules.map((m) => ({ ...m, icon: MODULE_ICONS[m.slug] ?? 'window-stack' }))
      : DEFAULT_MODULES);

  /** True when showing built-in defaults because the API couldn't be reached. */
  readonly usingDefaults = computed(() => !!this.site.error());
}
