import {
  ChangeDetectionStrategy,
  Component,
  computed,
  Directive,
  effect,
  inject,
  input,
  output,
  TemplateRef,
  ViewContainerRef,
} from '@angular/core';

import { CurrentOrgService } from '../../core/current-org.service';
import { Icon } from '@brand/icon/icon';

/** "1–25 of 80" with previous / next. Hidden when everything fits on one page. */
@Component({
  selector: 'ol-pager',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (total() > pageSize()) {
      <nav class="d-flex align-items-center justify-content-between gap-3 mt-3" aria-label="Pages">
        <span class="text-muted small tabular-nums">{{ from() }}–{{ to() }} of {{ total() }}</span>
        <div class="btn-group">
          <button type="button" class="btn btn-sm btn-outline-secondary" [disabled]="page() <= 1"
            (click)="pageChange.emit(page() - 1)">Previous</button>
          <button type="button" class="btn btn-sm btn-outline-secondary" [disabled]="to() >= total()"
            (click)="pageChange.emit(page() + 1)">Next</button>
        </div>
      </nav>
    }
  `,
})
export class Pager {
  readonly page = input.required<number>();
  readonly pageSize = input.required<number>();
  readonly total = input.required<number>();
  readonly pageChange = output<number>();
  protected readonly from = computed(() => (this.page() - 1) * this.pageSize() + 1);
  protected readonly to = computed(() => Math.min(this.page() * this.pageSize(), this.total()));
}

/** Search box that emits after the user pauses typing. */
@Component({
  selector: 'ol-search',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  template: `
    <div class="search">
      <ol-icon name="search" class="search-icon" />
      <input type="search" class="form-control" [placeholder]="placeholder()"
        [attr.aria-label]="placeholder()" [value]="value()" (input)="typed($any($event.target).value)" />
    </div>
  `,
  styles: `
    .search { position: relative; }
    .search-icon { position: absolute; left: 0.75rem; top: 50%; transform: translateY(-50%);
      color: var(--ol-text-muted); pointer-events: none; }
    input { padding-left: 2.25rem; }
  `,
})
export class Search {
  readonly placeholder = input('Search');
  readonly value = input('');
  readonly search = output<string>();
  private timer: ReturnType<typeof setTimeout> | undefined;

  protected typed(value: string): void {
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.search.emit(value.trim()), 250);
  }
}

const STATUS_STYLES: Record<string, string> = {
  active: 'text-bg-success-subtle', pending: 'text-bg-secondary-subtle',
  paused: 'text-bg-warning-subtle', expired: 'text-bg-warning-subtle',
  archived: 'text-bg-secondary-subtle', disabled: 'text-bg-danger-subtle',
};

/** A small status label: Active, Archived, Paused, Disabled, Pending, Expired. */
@Component({
  selector: 'ol-status',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span class="badge rounded-pill fw-medium" [class]="cls()">{{ label() }}</span>`,
  styles: `
    .badge { font-size: 0.75rem; }
    .text-bg-success-subtle { background: var(--bs-success-bg-subtle); color: var(--bs-success-text-emphasis); }
    .text-bg-warning-subtle { background: var(--bs-warning-bg-subtle); color: var(--bs-warning-text-emphasis); }
    .text-bg-danger-subtle { background: var(--bs-danger-bg-subtle); color: var(--bs-danger-text-emphasis); }
    .text-bg-secondary-subtle { background: var(--ol-surface-active); color: var(--ol-text); }
  `,
})
export class Status {
  readonly value = input.required<string>();
  protected readonly label = computed(() => this.value()[0].toUpperCase() + this.value().slice(1));
  protected readonly cls = computed(() => `badge rounded-pill fw-medium ${STATUS_STYLES[this.value()] ?? ''}`);
}

/**
 * Shows its content only if the user's role has the permission in the current organization.
 * Usage: <button *olCan="'clients.write'">. For convenience only; the API enforces it.
 */
@Directive({ selector: '[olCan]' })
export class Can {
  private readonly org = inject(CurrentOrgService);
  private readonly template = inject(TemplateRef);
  private readonly container = inject(ViewContainerRef);
  readonly olCan = input.required<string>();
  private shown = false;

  constructor() {
    effect(() => {
      const allowed = this.org.can(this.olCan());
      if (allowed && !this.shown) this.container.createEmbeddedView(this.template);
      if (!allowed && this.shown) this.container.clear();
      this.shown = allowed;
    });
  }
}
