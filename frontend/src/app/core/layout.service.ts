import { BreakpointObserver } from '@angular/cdk/layout';
import { Injectable, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { map } from 'rxjs';

import { prefs } from './storage';

const COLLAPSED_KEY = 'ol-sidebar-collapsed';

/** Sidebar state: collapsed on desktop (remembered), slide-over on small screens. */
@Injectable({ providedIn: 'root' })
export class LayoutService {
  readonly isMobile = toSignal(
    inject(BreakpointObserver).observe('(max-width: 991.98px)').pipe(map((s) => s.matches)),
    { initialValue: false },
  );
  readonly collapsed = signal(prefs.get(COLLAPSED_KEY) === '1');
  readonly mobileOpen = signal(false);

  toggleCollapsed(): void {
    this.collapsed.update((c) => !c);
    prefs.set(COLLAPSED_KEY, this.collapsed() ? '1' : '0');
  }

  openMobile(): void {
    this.mobileOpen.set(true);
  }

  closeMobile(): void {
    this.mobileOpen.set(false);
  }
}
