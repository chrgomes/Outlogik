import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

/**
 * The Outlogik logo in the current text colour, so it follows the theme. The SVG is used
 * as a mask, which keeps it a single cached file instead of inlining 10 KB of paths.
 */
@Component({
  selector: 'ol-logo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    role: 'img',
    'aria-label': 'Outlogik',
    '[class]': '"ol-logo ol-logo--" + variant()',
    '[style.--ol-logo-src]': 'src()',
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
    :host(.ol-logo--full) { aspect-ratio: 914 / 198; height: var(--ol-logo-height, 1.75rem); }
    :host(.ol-logo--symbol), :host(.ol-logo--symbol-small) {
      aspect-ratio: 1; height: var(--ol-logo-height, 2rem);
    }
  `,
})
export class Logo {
  /** full = symbol + wordmark; symbol = 32 px and up; symbol-small = 16–24 px. */
  readonly variant = input<'full' | 'symbol' | 'symbol-small'>('full');
  protected readonly src = computed(() => {
    const file = { full: 'outlogik-logo', symbol: 'outlogik-symbol',
      'symbol-small': 'outlogik-symbol-small' }[this.variant()];
    return `url("brand/${file}.svg")`;
  });
}
