import { CdkMenu, CdkMenuItem, CdkMenuItemRadio, CdkMenuTrigger } from '@angular/cdk/menu';
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { CurrentOrgService } from '../../core/current-org.service';
import { LayoutService } from '../../core/layout.service';
import { ThemePreference, ThemeService } from '../../core/theme.service';
import { Icon } from '../../shared/icon/icon';
import { IconName } from '../../shared/icon/icons';

@Component({
  selector: 'ol-topbar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CdkMenuTrigger, CdkMenu, CdkMenuItem, CdkMenuItemRadio, Icon],
  templateUrl: './topbar.html',
  styleUrl: './topbar.scss',
})
export class Topbar {
  protected readonly auth = inject(AuthService);
  protected readonly org = inject(CurrentOrgService);
  protected readonly layout = inject(LayoutService);
  protected readonly theme = inject(ThemeService);
  private readonly router = inject(Router);

  protected readonly themes: { value: ThemePreference; label: string; icon: IconName }[] = [
    { value: 'light', label: 'Light', icon: 'sun' },
    { value: 'dark', label: 'Dark', icon: 'moon-stars' },
    { value: 'system', label: 'Match system', icon: 'circle-half' },
  ];
  protected readonly themeIcon = computed<IconName>(
    () => this.themes.find((t) => t.value === this.theme.preference())!.icon,
  );
  protected readonly initials = computed(() => {
    const name = this.auth.user()?.full_name ?? '';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? parts.at(-1)![0] : '')).toUpperCase();
  });

  protected switchTo(slug: string): void {
    void this.router.navigate(['/o', slug]);
  }
}
