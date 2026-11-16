import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { CONSULTATION_PATH } from '../../config/site';
import { SiteData } from '../../config/site-data';
import { pageDescription } from '../../seo/seo';
import { LegalPage } from './legal-page';

/**
 * /terms: terms for using the website and the client portal. Client services themselves are
 * governed by each client's written proposal or agreement. Governing law follows the province in
 * the site settings. For review by the business, and ideally a lawyer, before launch.
 */
@Component({
  selector: 'mk-terms',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, LegalPage],
  templateUrl: './terms.html',
})
export class Terms {
  protected readonly s = inject(SiteData).settings;
  protected readonly consultationPath = CONSULTATION_PATH;

  constructor() {
    pageDescription('The terms for using the Outlogik website and client portal.');
  }
}
