import { CdkMenu, CdkMenuItem, CdkMenuItemRadio, CdkMenuTrigger } from '@angular/cdk/menu';
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { CurrentOrgService } from '../../core/current-org.service';
import { LayoutService } from '../../core/layout.service';
import { ThemePreference, ThemeService } from '../../core/theme.service';
import { WorkspaceService } from '../../core/workspace.service';
import { Icon } from '@brand/icon/icon';
import { IconName } from '@brand/icon/icons';

@Component({
  selector: 'ol-topbar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CdkMenuTrigger, CdkMenu, CdkMenuItem, CdkMenuItemRadio, Icon],
  templateUrl: './topbar.html',
  host: { role: 'banner' },
  styleUrl: './topbar.scss',
})
export class Topbar {
  protected readonly auth = inject(AuthService);
  protected readonly org = inject(CurrentOrgService);
  protected readonly layout = inject(LayoutService);
  protected readonly theme = inject(ThemeService);
  protected readonly ws = inject(WorkspaceService);
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

  protected readonly workspaceLabel = computed(() => {
    const w = this.ws.current();
    if (!w) return `${this.ws.list.value()?.length ?? 0} workspaces`;
    if (w.linked) return w.access === 'view' ? 'Linked business · view only' : 'Linked business';
    return w.kind === 'own' ? 'Your own marketing' : 'Client';
  });

  protected switchTo(slug: string): void {
    void this.router.navigate(['/o', slug]);
  }

  protected openAdmin(): void {
    void this.router.navigate(['/admin']);
  }
}
