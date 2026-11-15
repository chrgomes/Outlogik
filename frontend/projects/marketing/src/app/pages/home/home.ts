import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { appLink } from '../../config/site';

/** Homepage. Step 1 has the hero only; step 3 builds the full page (spec §4). */
@Component({
  selector: 'mk-home',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Icon],
  template: `
    <section class="mk-hero">
      <div class="mk-container">
        <p class="mk-eyebrow">Early access</p>
        <h1 class="mk-display">Everything you need to manage digital marketing. One platform.</h1>
        <p class="mk-lead">
          Outlogik brings your clients, their websites and your team into one workspace,
          with SEO, analytics and reporting on the way.
        </p>
        <div class="mk-hero__actions">
          <a [href]="registerUrl" class="btn btn-primary btn-lg">Get started</a>
          <a routerLink="/platform" class="btn btn-outline-dark btn-lg">Explore the platform <ol-icon name="arrow-right" /></a>
        </div>
      </div>
    </section>
  `,
})
export class Home {
  protected readonly registerUrl = appLink('/register');
}
