import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { DomSanitizer } from '@angular/platform-browser';

import { ICONS, IconName } from './icons';

/** Inline SVG icon from the bundled set. Decorative unless a `label` is given. */
@Component({
  selector: 'ol-icon',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    class: 'ol-icon',
    '[attr.role]': 'label() ? "img" : null',
    '[attr.aria-label]': 'label() || null',
    '[attr.aria-hidden]': 'label() ? null : "true"',
  },
  template: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor"
    [attr.width]="size()" [attr.height]="size()" [innerHTML]="svg()"></svg>`,
  styles: `:host { display: inline-flex; flex-shrink: 0; line-height: 0; }`,
})
export class Icon {
  private readonly sanitizer = inject(DomSanitizer);
  readonly name = input.required<IconName>();
  readonly size = input<number | string>('1em');
  readonly label = input<string>();
  // Icon markup is generated at build time from a trusted package, never user input.
  protected readonly svg = computed(() => this.sanitizer.bypassSecurityTrustHtml(ICONS[this.name()]));
}
