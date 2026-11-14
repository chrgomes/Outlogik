import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/** Page title, optional description, and actions on the right (`<div actions>`). */
@Component({
  selector: 'ol-page-header',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="min-w-0">
      <h1 class="h3 mb-1">{{ title() }}</h1>
      @if (description()) {
        <p class="text-muted mb-0">{{ description() }}</p>
      }
    </div>
    <div class="actions"><ng-content select="[actions]" /></div>
  `,
  styles: `
    :host {
      display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between;
      gap: 1rem; margin-bottom: 1.75rem;
    }
    .actions { display: flex; gap: 0.5rem; }
    .actions:empty { display: none; }
  `,
})
export class PageHeader {
  readonly title = input.required<string>();
  readonly description = input<string>();
}
