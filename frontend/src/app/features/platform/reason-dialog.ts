import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';

export interface ReasonData { title: string; message: string; confirmLabel: string; }

/** Asks why (a suspension needs a reason, kept with the account and in the audit log). */
@Component({
  selector: 'ol-reason-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h2 class="h5 mb-1">{{ data.title }}</h2>
    <p class="text-muted small mb-3">{{ data.message }}</p>
    <form (submit)="$event.preventDefault(); submit()" novalidate>
      <label class="form-label" for="reason">Reason</label>
      <textarea id="reason" class="form-control" rows="3" maxlength="500" [class.is-invalid]="error()"
        aria-describedby="reason-help" [value]="reason()" (input)="reason.set($any($event.target).value)"></textarea>
      <div id="reason-help" class="form-text">Kept with the account and in the audit log. Other staff will see it.</div>
      @if (error()) { <div class="invalid-feedback d-block">{{ error() }}</div> }
      <div class="d-flex justify-content-end gap-2 mt-3">
        <button type="button" class="btn btn-outline-secondary" (click)="ref.close()">Cancel</button>
        <button type="submit" class="btn btn-danger">{{ data.confirmLabel }}</button>
      </div>
    </form>
  `,
})
export class ReasonDialog {
  protected readonly ref = inject<DialogRef<string>>(DialogRef);
  protected readonly data = inject<ReasonData>(DIALOG_DATA);
  protected readonly reason = signal('');
  protected readonly error = signal('');

  protected submit(): void {
    const text = this.reason().trim();
    if (text.length < 3) return this.error.set('Write a short reason.');
    this.ref.close(text);
  }
}
