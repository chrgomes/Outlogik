import { isPlatformBrowser } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  PLATFORM_ID,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { filter } from 'rxjs';

import { Icon } from '@brand/icon/icon';
import { Logo } from '@brand/logo/logo';
import { AUDIENCES, COMPANY, CONSULTATION_PATH, LOGIN_URL, RESOURCES, SERVICES } from '../../config/site';
import { SiteData } from '../../config/site-data';

type Menu = 'services' | 'who' | 'resources' | 'company';

/**
 * Sticky site header. Desktop: disclosure menus (one open at a time; Escape, outside click,
 * leaving with Tab, or navigating closes them). Small screens: a native <dialog> drawer,
 * which provides the focus trap and Escape handling.
 */
@Component({
  selector: 'mk-header',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RouterLinkActive, Icon, Logo],
  templateUrl: './header.html',
  host: {
    class: 'mk-header',
    '[class.is-scrolled]': 'scrolled()',
    '(document:keydown.escape)': 'closeMenu(true)',
    '(document:click)': 'onDocumentClick($event)',
    '(window:scroll)': 'onScroll()',
  },
})
export class Header {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly browser = isPlatformBrowser(inject(PLATFORM_ID));
  private readonly drawer = viewChild<ElementRef<HTMLDialogElement>>('drawer');

  protected readonly settings = inject(SiteData).settings;
  protected readonly services = SERVICES;
  protected readonly audiences = AUDIENCES;
  protected readonly resources = RESOURCES;
  protected readonly company = COMPANY;
  protected readonly loginUrl = LOGIN_URL;
  protected readonly consultationPath = CONSULTATION_PATH;

  protected readonly open = signal<Menu | null>(null);
  protected readonly scrolled = signal(false);

  constructor() {
    inject(Router).events
      .pipe(filter((e) => e instanceof NavigationEnd), takeUntilDestroyed())
      .subscribe(() => {
        this.open.set(null);
        this.closeDrawer();
      });
  }

  protected toggle(menu: Menu): void {
    this.open.update((current) => (current === menu ? null : menu));
  }

  /** Escape: close the open menu and return focus to its button. */
  closeMenu(restoreFocus = false): void {
    const menu = this.open();
    if (!menu) return;
    this.open.set(null);
    if (restoreFocus) {
      this.host.nativeElement.querySelector<HTMLElement>(`#menu-button-${menu}`)?.focus();
    }
  }

  protected onDocumentClick(event: Event): void {
    if (!this.host.nativeElement.querySelector('.mk-nav')?.contains(event.target as Node)) {
      this.open.set(null);
    }
  }

  /** Close a menu when keyboard focus moves outside it. */
  protected onFocusOut(event: FocusEvent, menu: Menu): void {
    const item = (event.currentTarget as HTMLElement);
    if (this.open() === menu && !item.contains(event.relatedTarget as Node | null)) {
      this.open.set(null);
    }
  }

  protected onScroll(): void {
    if (this.browser) this.scrolled.set(window.scrollY > 8);
  }

  protected openDrawer(): void {
    this.drawer()?.nativeElement.showModal();
  }

  protected closeDrawer(): void {
    const dialog = this.drawer()?.nativeElement;
    if (dialog?.open) dialog.close();
  }

  /** Click on the dimmed area outside the drawer panel closes it. */
  protected onDrawerClick(event: MouseEvent): void {
    if (event.target === this.drawer()?.nativeElement) this.closeDrawer();
  }
}
