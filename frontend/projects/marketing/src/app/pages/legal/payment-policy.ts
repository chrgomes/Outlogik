import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { CONSULTATION_PATH } from '../../config/site';
import { SiteData } from '../../config/site-data';
import { pageDescription } from '../../seo/seo';
import { LegalPage } from './legal-page';

/**
 * /payment-policy: how Outlogik bills for its services (decided 2026-11-17): monthly in arrears,
 * due in 15 days, work may pause when an invoice is over 30 days late (no interest), 30 days'
 * notice to cancel, no refunds for work done. Each client's proposal can set different terms.
 * For review by the business, and ideally a lawyer or accountant, before launch.
 */
@Component({
  selector: 'mk-payment-policy',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, LegalPage],
  templateUrl: './payment-policy.html',
})
export class PaymentPolicy {
  protected readonly s = inject(SiteData).settings;
  protected readonly consultationPath = CONSULTATION_PATH;

  constructor() {
    pageDescription('How Outlogik bills for its services: monthly billing, payment terms, cancelling ongoing services and refunds.');
  }
}
