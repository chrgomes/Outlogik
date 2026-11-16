import {
  ChangeDetectionStrategy, Component, DestroyRef, RESPONSE_INIT, effect, inject, input,
} from '@angular/core';

import { LEGAL_UPDATED } from '../../config/site';
import { SiteData } from '../../config/site-data';
import { Seo } from '../../seo/seo';
import { PageHero } from '../../shared/page-hero';
import { NotFound } from '../not-found/not-found';

/**
 * Frame for the legal pages. They're published only once the legal details are set in the
 * admin area (decision 12). Until then the page shows "not found", answers 404 on the server,
 * and stays out of search engines, so no placeholder text is ever published.
 */
@Component({
  selector: 'mk-legal-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PageHero, NotFound],
  template: `
    @if (site.legalReady()) {
      <mk-page-hero [crumbs]="[{ label: title() }]" eyebrow="Legal" [title]="title()"
        [lead]="'Last updated ' + updated" />
      <section class="mk-section">
        <div class="mk-container">
          <div class="mk-legal"><ng-content /></div>
        </div>
      </section>
    } @else if (site.loaded()) {
      <mk-not-found />
    }
  `,
})
export class LegalPage {
  readonly title = input.required<string>();
  protected readonly site = inject(SiteData);
  protected readonly updated = LEGAL_UPDATED;

  constructor() {
    const seo = inject(Seo);
    const response = inject(RESPONSE_INIT, { optional: true });
    effect(() => {
      const hidden = !this.site.legalReady();
      seo.unpublished.set(hidden);
      if (response && this.site.loaded()) {
        response.status = hidden ? 404 : 200;
        if (hidden) response.headers = { ...(response.headers ?? {}), 'Cache-Control': 'no-store' };
      }
    });
    inject(DestroyRef).onDestroy(() => seo.unpublished.set(false));
  }
}
