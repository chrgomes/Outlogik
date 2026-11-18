import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

/**
 * A real product screenshot in a minimal browser frame. Images live in public/images as
 * <name>-720.webp, <name>.webp (1440 px) and <name>@2x.webp (2880 px); see
 * scripts/capture-marketing-screenshots.mjs. The browser picks the smallest that's sharp enough.
 * Width and height are fixed so the page doesn't shift while the image loads.
 */
@Component({
  selector: 'mk-screenshot',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <figure class="mk-shot">
      <div class="mk-browser">
        <div class="mk-browser__bar" aria-hidden="true">
          <i></i><i></i><i></i>
          @if (address()) { <span class="mk-browser__url">{{ address() }}</span> }
        </div>
        <img [src]="src()" [attr.srcset]="srcset()" [attr.sizes]="sizes()" [alt]="alt()" width="1440" height="720"
          [attr.loading]="priority() ? 'eager' : 'lazy'"
          [attr.fetchpriority]="priority() ? 'high' : null" decoding="async" />
      </div>
      @if (caption()) { <figcaption class="mk-caption">{{ caption() }}</figcaption> }
    </figure>
  `,
})
export class Screenshot {
  readonly name = input.required<string>();
  readonly alt = input.required<string>();
  readonly address = input<string>();
  readonly caption = input<string>('Screenshot with example data');
  /** Above the fold: load immediately with high priority (the hero image). */
  readonly priority = input(false);
  /** How wide the image is shown: the full container (hero), or about half of it (beside text). */
  readonly layout = input<'full' | 'half'>('half');
  protected readonly src = computed(() => `/images/${this.name()}.webp`);
  protected readonly srcset = computed(() => {
    const n = `/images/${this.name()}`;
    return `${n}-720.webp 720w, ${n}.webp 1440w, ${n}@2x.webp 2880w`;
  });
  /** Matches the page layout: one column below 992 px, otherwise full width or ~7/12 of 75rem. */
  protected readonly sizes = computed(() =>
    this.layout() === 'full'
      ? '(max-width: 1248px) calc(100vw - 2rem), 1152px'
      : '(max-width: 991px) calc(100vw - 2rem), 672px');
}
