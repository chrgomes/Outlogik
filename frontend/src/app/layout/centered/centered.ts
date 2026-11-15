import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

import { Logo } from '../../shared/logo/logo';

/** Frame for signed-out and system pages: logo above a centred card. */
@Component({
  selector: 'ol-centered-layout',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, RouterLink, Logo],
  template: `
    <main>
      <a routerLink="/" class="brand" aria-label="Outlogik home"><ol-logo /></a>
      <div class="card-wrap"><router-outlet /></div>
    </main>
  `,
  styles: `
    :host { display: block; min-height: 100dvh; background: var(--ol-surface); }
    main {
      min-height: 100dvh; display: flex; flex-direction: column; align-items: center;
      padding: 3rem 1rem;
    }
    .brand { color: var(--ol-text-strong); margin: 2rem 0 2.5rem; --ol-logo-height: 2.25rem; }
    .card-wrap {
      width: 100%; max-width: 26rem; padding: 2rem; border: 1px solid var(--ol-border);
      border-radius: var(--bs-border-radius-lg); background: var(--ol-surface-raised);
      box-shadow: var(--bs-box-shadow-sm);
    }
    @media (max-width: 575.98px) { .card-wrap { padding: 1.5rem 1.25rem; } }
  `,
})
export class CenteredLayout {}
