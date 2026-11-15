import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { CurrentOrgService } from '../../core/current-org.service';
import { LayoutService } from '../../core/layout.service';
import { Icon } from '@brand/icon/icon';
import { Logo } from '@brand/logo/logo';
import { NAV } from '../nav';

@Component({
  selector: 'ol-sidebar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RouterLinkActive, Icon, Logo],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss',
  host: {
    '[class.collapsed]': 'collapsed()',
    '[class.mobile]': 'layout.isMobile()',
    '[class.open]': 'layout.mobileOpen()',
    '[attr.aria-hidden]': 'layout.isMobile() && !layout.mobileOpen() ? "true" : null',
    '[attr.inert]': 'layout.isMobile() && !layout.mobileOpen() ? "" : null',
  },
})
export class Sidebar {
  protected readonly layout = inject(LayoutService);
  protected readonly org = inject(CurrentOrgService);

  /** Collapsing applies on desktop only; the mobile slide-over is always full width. */
  protected readonly collapsed = computed(
    () => this.layout.collapsed() && !this.layout.isMobile(),
  );
  protected readonly sections = computed(() =>
    NAV.map((s) => ({ ...s, items: s.items.filter((i) => this.org.permissions().has(i.permission)) }))
      .filter((s) => s.items.length > 0),
  );
}
