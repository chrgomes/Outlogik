import { ChangeDetectionStrategy, Component, Injectable, inject, signal } from '@angular/core';

import { Icon } from '@brand/icon/icon';

export interface Toast {
  id: number;
  kind: 'success' | 'error';
  message: string;
}

/** Short confirmation messages ("Client created"). Errors stay until dismissed. */
@Injectable({ providedIn: 'root' })
export class ToastService {
  readonly toasts = signal<Toast[]>([]);
  private nextId = 1;

  success(message: string): void {
    this.push('success', message, 4000);
  }

  error(message: string): void {
    this.push('error', message, 0);
  }

  dismiss(id: number): void {
    this.toasts.update((list) => list.filter((t) => t.id !== id));
  }

  private push(kind: Toast['kind'], message: string, ttl: number): void {
    const toast = { id: this.nextId++, kind, message };
    this.toasts.update((list) => [...list.slice(-3), toast]);
    if (ttl) setTimeout(() => this.dismiss(toast.id), ttl);
  }
}

@Component({
  selector: 'ol-toast-host',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  template: `
    <div class="stack" aria-live="polite">
      @for (t of toasts.toasts(); track t.id) {
        <div class="toast-item" [class.error]="t.kind === 'error'"
          [attr.role]="t.kind === 'error' ? 'alert' : 'status'">
          <ol-icon [name]="t.kind === 'error' ? 'exclamation-triangle' : 'check2'" />
          <span class="flex-grow-1">{{ t.message }}</span>
          <button type="button" class="close" (click)="toasts.dismiss(t.id)" aria-label="Dismiss">
            <ol-icon name="x-lg" size="0.75rem" />
          </button>
        </div>
      }
    </div>
  `,
  styles: `
    .stack {
      position: fixed; right: 1.25rem; bottom: 1.25rem; z-index: 1100;
      display: flex; flex-direction: column; gap: 0.5rem; width: min(24rem, calc(100vw - 2rem));
    }
    .toast-item {
      display: flex; align-items: center; gap: 0.625rem; padding: 0.75rem 0.875rem;
      border-radius: var(--bs-border-radius-lg); background: var(--ol-text-strong);
      color: var(--ol-bg); box-shadow: var(--ol-shadow); font-size: 0.875rem;
    }
    .toast-item.error { background: var(--bs-danger); color: #fff; }
    .close { border: 0; background: none; color: inherit; opacity: 0.7; padding: 0.25rem; }
    .close:hover { opacity: 1; }
  `,
})
export class ToastHost {
  protected readonly toasts = inject(ToastService);
}
