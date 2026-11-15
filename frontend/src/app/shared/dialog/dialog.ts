import { Dialog, DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ComponentType } from '@angular/cdk/portal';
import { ChangeDetectionStrategy, Component, inject, Injectable, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

/** Opens app dialogs with one look and focus handling (CDK Dialog traps focus). */
@Injectable({ providedIn: 'root' })
export class DialogService {
  private readonly dialog = inject(Dialog);

  open<R, D = unknown>(component: ComponentType<unknown>, data?: D, wide = false): Promise<R | undefined> {
    const ref = this.dialog.open<R, D>(component, {
      data,
      panelClass: ['ol-dialog', ...(wide ? ['ol-dialog--wide'] : [])],
      backdropClass: 'ol-dialog-backdrop',
      autoFocus: 'first-tabbable',
      restoreFocus: true,
    });
    return firstValueFrom(ref.closed);
  }

  confirm(options: ConfirmOptions): Promise<boolean> {
    return this.open<boolean, ConfirmOptions>(ConfirmDialog, options).then((r) => r === true);
  }
}

export interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel: string;
  danger?: boolean;
  /** Ask the user to type this text before confirming (for destructive actions). */
  typeToConfirm?: string;
}

@Component({
  selector: 'ol-confirm-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule],
  template: `
    <h2 class="h5 mb-2" id="confirm-title">{{ data.title }}</h2>
    <p class="text-muted">{{ data.message }}</p>
    @if (data.typeToConfirm) {
      <label for="confirm-text" class="form-label small">
        Type <strong>{{ data.typeToConfirm }}</strong> to confirm
      </label>
      <input id="confirm-text" class="form-control mb-3" [ngModel]="typed()"
        (ngModelChange)="typed.set($event)" autocomplete="off" />
    }
    <div class="ol-dialog-actions">
      <button type="button" class="btn btn-outline-secondary" (click)="ref.close(false)">Cancel</button>
      <button type="button" class="btn" [class.btn-danger]="data.danger"
        [class.btn-primary]="!data.danger" (click)="ref.close(true)"
        [disabled]="data.typeToConfirm && typed().trim() !== data.typeToConfirm">
        {{ data.confirmLabel }}
      </button>
    </div>
  `,
  host: { role: 'alertdialog', 'aria-labelledby': 'confirm-title' },
})
export class ConfirmDialog {
  protected readonly ref = inject<DialogRef<boolean>>(DialogRef);
  protected readonly data = inject<ConfirmOptions>(DIALOG_DATA);
  protected readonly typed = signal('');
}
