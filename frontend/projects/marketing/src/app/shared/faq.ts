import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { Question } from '../config/services-content';

/** Frequently asked questions as native disclosure widgets (work before JavaScript loads). */
@Component({
  selector: 'mk-faq',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mk-faq">
      @for (item of items(); track item.q) {
        <details class="mk-faq__item">
          <summary>{{ item.q }}</summary>
          <p>{{ item.a }}</p>
        </details>
      }
    </div>
  `,
})
export class Faq {
  readonly items = input.required<Question[]>();
}
