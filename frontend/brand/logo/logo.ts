import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/**
 * The Outlogik logo in the current text colour, so it follows the theme. The SVG is used as a
 * mask, which keeps it a single cached file instead of inlining 10 KB of paths.
 *
 * The file is chosen by a class in the stylesheet rather than a style binding, so the logo also
 * renders on the server (the SSR DOM can't set CSS custom properties).
 */
@Component({
  selector: 'ol-logo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    role: 'img',
    'aria-label': 'Outlogik',
    '[class]': '"ol-logo ol-logo--" + variant()',
  },
  template: '',
  styles: `
    :host {
      display: inline-block;
      flex-shrink: 0;
      background-color: currentColor;
      -webkit-mask: var(--ol-logo-src) no-repeat center / contain;
      mask: var(--ol-logo-src) no-repeat center / contain;
    }
    :host(.ol-logo--full) {
      --ol-logo-src: url('/brand/outlogik-logo.svg');
      aspect-ratio: 914 / 198;
      height: var(--ol-logo-height, 1.75rem);
    }
    :host(.ol-logo--symbol) { --ol-logo-src: url('/brand/outlogik-symbol.svg'); }
    :host(.ol-logo--symbol-small) { --ol-logo-src: url('/brand/outlogik-symbol-small.svg'); }
    :host(.ol-logo--symbol), :host(.ol-logo--symbol-small) {
      aspect-ratio: 1;
      height: var(--ol-logo-height, 2rem);
    }
  `,
})
export class Logo {
  /** full = symbol + wordmark; symbol = 32 px and up; symbol-small = 16–24 px. */
  readonly variant = input<'full' | 'symbol' | 'symbol-small'>('full');
}
