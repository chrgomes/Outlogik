import { ChangeDetectionStrategy, Component, afterNextRender, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { Footer } from './layout/footer/footer';
import { Header } from './layout/header/header';
import { Consent } from './consent/consent';
import { CookieBanner } from './consent/cookie-banner';
import { VisitAttribution } from './shared/attribution';

@Component({
  selector: 'mk-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, Header, Footer, CookieBanner],
  template: `
    <a class="mk-skip-link" href="#main">Skip to content</a>
    <mk-header />
    <main id="main" tabindex="-1">
      <router-outlet />
    </main>
    <mk-footer />
    <mk-cookie-banner />
  `,
})
export class App {
  constructor() {
    const attribution = inject(VisitAttribution);
    const consent = inject(Consent);
    afterNextRender(() => {
      attribution.record();
      consent.start();
    });
  }
}
