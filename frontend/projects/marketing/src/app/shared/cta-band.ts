import { ChangeDetectionStrategy, Component, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { CONSULTATION_PATH } from '../config/site';
import { SiteData } from '../config/site-data';

/** The closing call to action used at the end of most pages. */
@Component({
  selector: 'mk-cta-band',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="mk-section mk-section--dark mk-cta" aria-labelledby="cta-title">
      <div class="mk-container">
        <h2 class="mk-h2" id="cta-title">{{ title() }}</h2>
        <p class="mk-lead">{{ lead() }}</p>
        <div class="mk-cta__actions">
          <a [routerLink]="consultationPath" class="btn btn-lg mk-btn-light">{{ settings().consultation_cta_label }}</a>
          <a routerLink="/contact" class="btn btn-lg mk-btn-ghost">Contact us</a>
        </div>
      </div>
    </section>
  `,
})
export class CtaBand {
  readonly title = input('Let’s talk about your marketing.');
  readonly lead = input('Tell us where you are and where you want to be. We’ll tell you honestly how we can help.');
  protected readonly settings = inject(SiteData).settings;
  protected readonly consultationPath = CONSULTATION_PATH;
}
