import { ChangeDetectionStrategy, Component, input, signal } from '@angular/core';
import { AbstractControl, FormControl, ReactiveFormsModule } from '@angular/forms';

const MESSAGES: Record<string, (e: unknown) => string> = {
  required: () => 'This field is required.',
  email: () => 'Enter a valid email address.',
  minlength: (e) => `Use at least ${(e as { requiredLength: number }).requiredLength} characters.`,
  maxlength: (e) => `Use at most ${(e as { requiredLength: number }).requiredLength} characters.`,
  mismatch: () => "The passwords don't match.",
  server: (e) => String(e),
};

/** True once the user has interacted with the control (or tried to submit) and it's invalid. */
export function showError(control: AbstractControl): boolean {
  return control.invalid && (control.touched || control.dirty);
}

/** The first error message for a control, or null. */
export function errorMessage(control: AbstractControl): string | null {
  if (!showError(control) || !control.errors) return null;
  const [key, value] = Object.entries(control.errors)[0];
  return (MESSAGES[key] ?? (() => 'This value is not valid.'))(value);
}

/**
 * Field error text. Uses default change detection on purpose: form state isn't a signal,
 * and these are tiny, so re-checking them with their parent is the simplest correct option.
 */
@Component({
  selector: 'ol-field-error',
  changeDetection: ChangeDetectionStrategy.Default,
  template: `@if (message) {<div class="invalid-feedback d-block" [id]="id()">{{ message }}</div>}`,
})
export class FieldError {
  readonly control = input.required<AbstractControl>();
  readonly id = input<string>();
  protected get message(): string | null {
    return errorMessage(this.control());
  }
}

/** Password input with a show/hide toggle. */
@Component({
  selector: 'ol-password-input',
  changeDetection: ChangeDetectionStrategy.Default,
  imports: [ReactiveFormsModule],
  template: `
    <div class="input-group has-validation">
      <input
        [type]="visible() ? 'text' : 'password'"
        class="form-control"
        [class.is-invalid]="invalid"
        [id]="inputId()"
        [formControl]="control()"
        [attr.autocomplete]="autocomplete()"
        [attr.aria-describedby]="describedBy() || null"
        [attr.aria-invalid]="invalid"
        spellcheck="false"
        autocapitalize="off"
      />
      <button
        type="button"
        class="btn btn-outline-secondary"
        (click)="visible.set(!visible())"
        [attr.aria-pressed]="visible()"
      >
        {{ visible() ? 'Hide' : 'Show' }}<span class="visually-hidden"> password</span>
      </button>
    </div>
  `,
})
export class PasswordInput {
  readonly control = input.required<FormControl<string>>();
  readonly inputId = input.required<string>();
  readonly autocomplete = input<'current-password' | 'new-password'>('current-password');
  readonly describedBy = input<string>();
  protected readonly visible = signal(false);
  protected get invalid(): boolean {
    return showError(this.control());
  }
}
