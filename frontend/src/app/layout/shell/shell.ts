import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';

import { LayoutService } from '../../core/layout.service';
import { Sidebar } from '../sidebar/sidebar';
import { Topbar } from '../topbar/topbar';
import { VerifyBanner } from '../verify-banner/verify-banner';
import { ToastHost } from '../../shared/toast/toast';

/** The signed-in app frame: sidebar, top bar, and the page. */
@Component({
  selector: 'ol-shell',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, Sidebar, Topbar, VerifyBanner, ToastHost],
  host: { '(document:keydown.escape)': 'layout.closeMobile()' },
  template: `
    <a class="skip-link" href="#main">Skip to content</a>
    <ol-sidebar />
    @if (layout.isMobile() && layout.mobileOpen()) {
      <div class="backdrop" (click)="layout.closeMobile()" aria-hidden="true"></div>
    }
    <div class="main-col">
      <ol-topbar />
      <ol-verify-banner />
      <main id="main" tabindex="-1">
        <router-outlet />
      </main>
    </div>
    <ol-toast-host />
  `,
  styles: `
    :host { display: flex; min-height: 100dvh; }
    .main-col { flex: 1; min-width: 0; display: flex; flex-direction: column; }
    main { flex: 1; width: 100%; max-width: 80rem; margin: 0 auto; padding: 2rem 2rem 4rem; }
    main:focus { outline: none; }
    .backdrop { position: fixed; inset: 0; z-index: 1035; background: var(--ol-backdrop); }
    @media (max-width: 991.98px) { main { padding: 1.5rem 1rem 3rem; } }
  `,
})
export class Shell {
  protected readonly layout = inject(LayoutService);

  constructor() {
    inject(Router).events
      .pipe(filter((e) => e instanceof NavigationEnd), takeUntilDestroyed())
      .subscribe(() => this.layout.closeMobile());
  }
}
