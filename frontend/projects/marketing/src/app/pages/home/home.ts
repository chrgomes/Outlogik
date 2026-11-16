import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { AUDIENCES, CONSULTATION_PATH, SERVICES, SITE_URL, TOOLS } from '../../config/site';
import { SiteData } from '../../config/site-data';
import { StatusBadge } from '../../layout/status-badge';
import { ORGANIZATION_ID, SITE_NAME, structuredData } from '../../seo/seo';
import { Screenshot } from '../../shared/screenshot';

/**
 * Homepage (plan revision 2, section 4). Results and testimonials are deliberately absent until
 * real ones exist (spec §4.8, §19).
 */
@Component({
  selector: 'mk-home',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Icon, Screenshot, StatusBadge],
  templateUrl: './home.html',
})
export class Home {
  private readonly site = inject(SiteData);
  protected readonly settings = this.site.settings;
  protected readonly features = this.site.portalFeatures;
  protected readonly services = SERVICES;
  protected readonly audiences = AUDIENCES;
  protected readonly tools = TOOLS;
  protected readonly consultationPath = CONSULTATION_PATH;

  constructor() {
    structuredData('website', {
      '@type': 'WebSite', '@id': `${SITE_URL}/#website`, name: SITE_NAME, url: SITE_URL + '/',
      publisher: { '@id': ORGANIZATION_ID }, inLanguage: 'en',
    });
  }
}
