import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { CurrentOrgService } from '../../core/current-org.service';
import { LayoutService } from '../../core/layout.service';
import { Icon } from '@brand/icon/icon';
import { Logo } from '@brand/logo/logo';
import { ADMIN_NAV, NAV } from '../nav';

@Component({
  selector: 'ol-sidebar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RouterLinkActive, Icon, Logo],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss',
  host: {
    role: 'complementary',
    'aria-label': 'Sidebar',
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
  protected readonly admin = computed(() => this.org.area() === 'admin');
  protected readonly home = computed(() => (this.admin() ? ['/admin'] : ['/o', this.org.slug()]));
  /** Each link as router commands, so the template doesn't care which area is open. */
  protected readonly sections = computed(() => {
    if (this.admin()) {
      return ADMIN_NAV.map((s) => ({
        label: s.label, items: s.items.map((i) => ({ ...i, link: ['/admin', ...i.path.split('/')] })),
      }));
    }
    return NAV.map((s) => ({
      label: s.label,
      items: s.items.filter((i) => this.org.permissions().has(i.permission)
          && (!i.agencyOnly || this.org.isAgency()) && (!i.businessOnly || !this.org.isAgency())
          && (!i.staffOnly || !this.org.isClientUser()))
        // One command per segment: 'settings/members' as a single command becomes settings%2Fmembers.
        .map((i) => ({ ...i, link: ['/o', this.org.slug(), ...i.path.split('/')] })),
    })).filter((s) => s.items.length > 0);
  });
}
