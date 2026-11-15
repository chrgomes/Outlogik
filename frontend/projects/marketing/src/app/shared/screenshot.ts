import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

/**
 * A real product screenshot in a minimal browser frame. Images live in public/images as
 * <name>.webp (1440 px) and <name>@2x.webp (2880 px); see scripts/capture-marketing-screenshots.mjs.
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
        <img [src]="src()" [attr.srcset]="srcset()" [alt]="alt()" width="1440" height="720"
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
  protected readonly src = computed(() => `/images/${this.name()}.webp`);
  protected readonly srcset = computed(
    () => `/images/${this.name()}.webp 1x, /images/${this.name()}@2x.webp 2x`);
}
