import {
  ChangeDetectionStrategy,
  Component,
  InjectionToken,
  Provider,
  computed,
  inject,
  input,
} from '@angular/core';
import { DomSanitizer } from '@angular/platform-browser';

import { IconName, IconSet } from './icons';

/** The icons a site bundles. Each app provides its own set (see icons-app.ts / icons-marketing.ts). */
export const ICON_SET = new InjectionToken<IconSet>('ICON_SET', { factory: () => ({}) });

export function provideIcons(set: IconSet): Provider {
  return { provide: ICON_SET, useValue: set };
}

/**
 * Inline SVG icon from the bundled set. Decorative unless a `label` is given.
 * The whole <svg> is rendered as markup on the host (not innerHTML on an <svg> element),
 * which also works in server-side rendering.
 */
@Component({
  selector: 'ol-icon',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    class: 'ol-icon',
    '[attr.role]': 'label() ? "img" : null',
    '[attr.aria-label]': 'label() || null',
    '[attr.aria-hidden]': 'label() ? null : "true"',
    '[innerHTML]': 'svg()',
  },
  template: '',
  styles: `:host { display: inline-flex; flex-shrink: 0; line-height: 0; }`,
})
export class Icon {
  private readonly sanitizer = inject(DomSanitizer);
  private readonly icons = inject(ICON_SET);
  readonly name = input.required<IconName>();
  readonly size = input<number | string>('1em');
  readonly label = input<string>();
  // Icon markup is generated at build time from a trusted package, never user input.
  protected readonly svg = computed(() => {
    const size = String(this.size()).replace(/[^\w.%]/g, '');
    return this.sanitizer.bypassSecurityTrustHtml(
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" ` +
        `width="${size}" height="${size}" focusable="false">${this.icons[this.name()] ?? ''}</svg>`,
    );
  });
}
