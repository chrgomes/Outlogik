import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { Footer } from './layout/footer/footer';
import { Header } from './layout/header/header';

@Component({
  selector: 'mk-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, Header, Footer],
  template: `
    <a class="mk-skip-link" href="#main">Skip to content</a>
    <mk-header />
    <main id="main" tabindex="-1">
      <router-outlet />
    </main>
    <mk-footer />
  `,
})
export class App {}
