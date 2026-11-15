import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { SERVICE_CONTENT } from '../../config/services-content';
import { CONSULTATION_PATH, SERVICES } from '../../config/site';
import { SiteData } from '../../config/site-data';
import { CtaBand } from '../../shared/cta-band';
import { pageDescription } from '../../shared/meta';
import { PageHero } from '../../shared/page-hero';

/** /services: the four services, each with a few of the things it includes. */
@Component({
  selector: 'mk-services-overview',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Icon, PageHero, CtaBand],
  template: `
    <mk-page-hero [crumbs]="[{ label: 'Services' }]" eyebrow="Services"
      title="Digital marketing services, planned together."
      lead="SEO, social media, content and analytics, delivered by one team with one plan, and reported in one place.">
      <div class="mk-hero__actions">
        <a [routerLink]="consultationPath" class="btn btn-primary btn-lg">{{ settings().consultation_cta_label }}</a>
      </div>
    </mk-page-hero>

    <section class="mk-section mk-section--muted" aria-label="Our services">
      <div class="mk-container mk-service-list">
        @for (s of services; track s.slug) {
          <article class="mk-service-row">
            <div>
              <span class="mk-ico-box"><ol-icon [name]="s.icon" /></span>
              <h2 class="mk-h3"><a [routerLink]="['/services', s.slug]">{{ s.name }}</a></h2>
              <p>{{ s.summary }}</p>
              <a [routerLink]="['/services', s.slug]" class="mk-arrow-link"
                [attr.aria-label]="'More about ' + s.name">Learn more <ol-icon name="arrow-right" /></a>
            </div>
            <ul class="mk-checks mk-checks--compact">
              @for (i of included(s.slug); track i) {
                <li><ol-icon name="check-circle-fill" /> {{ i }}</li>
              }
            </ul>
          </article>
        }
      </div>
    </section>

    <section class="mk-section" aria-labelledby="together-title">
      <div class="mk-container">
        <div class="mk-head">
          <p class="mk-eyebrow">Better together</p>
          <h2 class="mk-h2" id="together-title">Choose one service, or let them work together.</h2>
          <p class="mk-lead">
            Each service stands on its own. Combined, they reinforce each other: content gives SEO
            something to rank, social puts it in front of people, and analytics shows what’s working.
          </p>
        </div>
        <ol class="mk-steps">
          <li><h3>Tell us your goals</h3><p>In a free consultation, we learn about your business and what you want from marketing.</p></li>
          <li><h3>Get a proposal</h3><p>We recommend the services that fit, with what’s included and what it costs.</p></li>
          <li><h3>We do the work</h3><p>One team plans and delivers everything, with one point of contact.</p></li>
          <li><h3>See the results</h3><p>Monthly reporting across every service, and your own client portal.</p></li>
        </ol>
      </div>
    </section>

    <mk-cta-band title="Not sure where to start?"
      lead="That’s what the consultation is for. We’ll look at where you are and recommend what will help most." />
  `,
})
export class ServicesOverview {
  protected readonly settings = inject(SiteData).settings;
  protected readonly services = SERVICES;
  protected readonly consultationPath = CONSULTATION_PATH;

  protected included(slug: string): string[] {
    return SERVICE_CONTENT[slug].included.slice(0, 4).map((i) => i.title);
  }

  constructor() {
    pageDescription('SEO, social media management, website analytics and content marketing from Outlogik, with reporting in your own client portal.');
  }
}
