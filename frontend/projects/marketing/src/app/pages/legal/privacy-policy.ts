import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Consent } from '../../consent/consent';
import { SiteData } from '../../config/site-data';
import { pageDescription } from '../../seo/seo';
import { LegalPage } from './legal-page';
import { FEDERAL_AUTHORITY, PROVINCIAL_AUTHORITIES } from './privacy-authorities';

/**
 * /privacy-policy. Written from what the website and client portal actually collect and do
 * (spec §17: policies must reflect actual data collection), considering PIPEDA and CASL. The
 * business details, the province's own privacy law and the analytics tools in use come from the
 * site settings. For review by the business, and ideally a lawyer, before launch.
 */
@Component({
  selector: 'mk-privacy-policy',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, LegalPage],
  templateUrl: './privacy-policy.html',
})
export class PrivacyPolicy {
  protected readonly s = inject(SiteData).settings;
  protected readonly consent = inject(Consent);
  protected readonly federal = FEDERAL_AUTHORITY;
  protected readonly provincial = computed(() => PROVINCIAL_AUTHORITIES[this.s().province ?? ''] ?? null);
  protected readonly toolList = computed(() => {
    const tools = this.consent.tools();
    return tools.length > 1 ? `${tools.slice(0, -1).join(', ')} and ${tools.at(-1)}` : (tools[0] ?? '');
  });

  constructor() {
    pageDescription('How Outlogik collects, uses and protects personal information on its website and client portal, and the choices you have.');
  }
}
