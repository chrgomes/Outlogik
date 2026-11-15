import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/**
 * The hidden spam trap for website forms: a text field people never see or reach with the
 * keyboard, so only bots fill it in. Bind it to the form's `nickname` value.
 */
@Component({
  selector: 'mk-honeypot',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'mk-honeypot', 'aria-hidden': 'true' },
  template: `<ng-content />`,
})
export class Honeypot {}

/** An error message shown above a form's submit button, announced to screen readers. */
@Component({
  selector: 'mk-form-error',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div role="alert" aria-live="assertive">
      @if (message()) { <p class="mk-form-error">{{ message() }}</p> }
    </div>
  `,
})
export class FormError {
  readonly message = input<string | null>(null);
}
