import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { Icon } from '../icon/icon';
import { IconName } from '../icon/icons';

/** Nothing to show yet: icon, title, message and optional actions (projected). */
@Component({
  selector: 'ol-empty-state',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  template: `
    <div class="icon"><ol-icon [name]="icon()" size="1.375rem" /></div>
    <h2 class="h5 mb-1">{{ title() }}</h2>
    @if (message()) {
      <p class="text-muted mb-0">{{ message() }}</p>
    }
    <div class="actions"><ng-content /></div>
  `,
  styles: `
    :host {
      display: flex; flex-direction: column; align-items: center; text-align: center;
      padding: 3.5rem 1.5rem; border: 1px dashed var(--ol-border);
      border-radius: var(--bs-border-radius-lg);
    }
    .icon {
      display: grid; place-items: center; width: 3rem; height: 3rem; margin-bottom: 1rem;
      border-radius: 50%; background: var(--ol-surface-hover); color: var(--ol-text-muted);
    }
    p { max-width: 32rem; }
    .actions { margin-top: 1.25rem; display: flex; gap: 0.5rem; }
    .actions:empty { display: none; }
  `,
})
export class EmptyState {
  readonly icon = input<IconName>('inbox');
  readonly title = input.required<string>();
  readonly message = input<string>();
}

/** Loading indicator with an accessible label. */
@Component({
  selector: 'ol-loading-state',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
    <span>{{ label() }}</span>
  `,
  host: { role: 'status', 'aria-live': 'polite' },
  styles: `
    :host {
      display: flex; align-items: center; justify-content: center; gap: 0.625rem;
      padding: 3rem 1rem; color: var(--ol-text-muted);
    }
  `,
})
export class LoadingState {
  readonly label = input('Loading…');
}

/** Something went wrong, with an optional retry. */
@Component({
  selector: 'ol-error-state',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  template: `
    <ol-icon name="exclamation-triangle" size="1.25rem" />
    <div class="flex-grow-1">
      <strong class="d-block">{{ title() }}</strong>
      <span>{{ message() }}</span>
    </div>
    @if (retryable()) {
      <button type="button" class="btn btn-sm btn-outline-secondary" (click)="retry.emit()">
        Try again
      </button>
    }
  `,
  host: { role: 'alert', class: 'alert alert-danger' },
  styles: `:host { display: flex; align-items: center; gap: 0.875rem; }`,
})
export class ErrorState {
  readonly title = input('Something went wrong');
  readonly message = input('Please try again in a moment.');
  readonly retryable = input(true);
  readonly retry = output<void>();
}
