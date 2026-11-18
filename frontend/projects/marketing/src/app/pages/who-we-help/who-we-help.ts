import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { AUDIENCES, CONSULTATION_PATH } from '../../config/site';
import { SiteData } from '../../config/site-data';
import { CtaBand } from '../../shared/cta-band';
import { pageDescription } from '../../seo/seo';
import { PageHero } from '../../shared/page-hero';

/** /who-we-help: the business types we work with (decision B). */
@Component({
  selector: 'mk-who-we-help',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Icon, PageHero, CtaBand],
  template: `
    <mk-page-hero [crumbs]="[{ label: 'Who we help' }]" eyebrow="Who we help"
      title="Marketing shaped around your kind of business."
      lead="A local clinic, an online store and an in-house marketing team need different things. We start with how your customers find you and choose you.">
      <div class="mk-hero__actions">
        <a [routerLink]="consultationPath" class="btn btn-primary btn-lg">{{ settings().consultation_cta_label }}</a>
      </div>
    </mk-page-hero>

    <section class="mk-section mk-section--muted" aria-label="Business types">
      <div class="mk-container">
        <div class="mk-cards mk-cards--2">
          @for (a of audiences; track a.slug) {
            <a class="mk-card mk-card--lg" [routerLink]="['/who-we-help', a.slug]">
              <span class="mk-ico-box"><ol-icon [name]="a.icon" /></span>
              <h2 class="mk-h3">{{ a.name }}</h2>
              <p>{{ a.summary }}</p>
              <span class="mk-arrow-link">How we help <ol-icon name="arrow-right" /></span>
            </a>
          }
        </div>
      </div>
    </section>

    <section class="mk-section" aria-labelledby="other-title">
      <div class="mk-container mk-head mk-head--center">
        <h2 class="mk-h2" id="other-title">Don’t see your business here?</h2>
        <p class="mk-lead">
          These are the businesses we most often work with, not a complete list. Tell us about yours
          in a free consultation, and we’ll tell you honestly whether we’re a good fit.
        </p>
      </div>
    </section>

    <mk-cta-band />
  `,
})
export class WhoWeHelp {
  protected readonly settings = inject(SiteData).settings;
  protected readonly audiences = AUDIENCES;
  protected readonly consultationPath = CONSULTATION_PATH;

  constructor() {
    pageDescription('Outlogik works with small businesses, local and service businesses, online stores and growing companies. See how we help each.');
  }
}
