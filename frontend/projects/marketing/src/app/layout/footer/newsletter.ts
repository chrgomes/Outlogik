import { ChangeDetectionStrategy, Component, afterNextRender, inject, signal } from '@angular/core';

import { RouterLink } from '@angular/router';

import { NEWSLETTER_CONSENT_TEXT } from '../../config/forms';
import { SiteData } from '../../config/site-data';
import { FormError } from '../../shared/form-status';
import { LeadApi } from '../../shared/lead-api';

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Newsletter sign-up in the footer. CASL: an unticked consent box with the exact wording that
 * is stored, then a confirmation email (double opt-in). Built without @angular/forms because it
 * is on every page and two fields don't need it.
 */
@Component({
  selector: 'mk-newsletter',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormError, RouterLink],
  template: `
    <h2 class="mk-footer__heading" id="newsletter-title">Newsletter</h2>
    @if (sent()) {
      <p class="mk-newsletter__done" role="status">
        Almost done. Check your inbox and click the link to confirm your subscription.
      </p>
    } @else {
      <form class="mk-newsletter" (submit)="submit($event)" novalidate aria-labelledby="newsletter-title">
        <p>Practical marketing tips and news from Outlogik, now and then.</p>
        <div class="mk-newsletter__row">
          <label for="nl-email" class="visually-hidden">Email address</label>
          <input id="nl-email" type="email" autocomplete="email" placeholder="Your email address"
            [value]="email()" (input)="email.set($any($event.target).value)"
            [attr.aria-invalid]="showErrors() && !emailValid()" />
          <button type="submit" class="btn mk-btn-light" [disabled]="sending()">
            {{ sending() ? 'Sending…' : 'Subscribe' }}
          </button>
        </div>
        <label class="mk-check mk-newsletter__consent">
          <input type="checkbox" [checked]="consent()" (change)="consent.set($any($event.target).checked)"
            [attr.aria-invalid]="showErrors() && !consent()" />
          {{ consentText }}
        </label>
        @if (site.legalReady()) {
          <p class="mk-newsletter__privacy">How we handle your email: <a routerLink="/privacy-policy">privacy policy</a>.</p>
        }
        <div class="mk-honeypot" aria-hidden="true">
          <label for="nl-nickname">Leave this field empty</label>
          <input id="nl-nickname" type="text" tabindex="-1" autocomplete="off"
            (input)="nickname = $any($event.target).value" />
        </div>
        <mk-form-error [message]="error()" />
      </form>
    }
  `,
})
export class Newsletter {
  private readonly api = inject(LeadApi);
  protected readonly site = inject(SiteData);
  protected readonly consentText = NEWSLETTER_CONSENT_TEXT;
  protected readonly email = signal('');
  protected readonly consent = signal(false);
  protected readonly sending = signal(false);
  protected readonly sent = signal(false);
  protected readonly showErrors = signal(false);
  protected readonly error = signal<string | null>(null);
  protected nickname = '';
  private openedAt = 0;

  constructor() {
    afterNextRender(() => (this.openedAt = performance.now()));
  }

  protected emailValid(): boolean {
    return EMAIL.test(this.email().trim());
  }

  protected async submit(event: Event): Promise<void> {
    event.preventDefault();
    this.showErrors.set(true);
    if (!this.emailValid()) return this.error.set('Please enter a valid email address.');
    if (!this.consent()) return this.error.set('Please tick the box to confirm you’d like the newsletter.');
    this.error.set(null);
    this.sending.set(true);
    const result = await this.api.send('newsletter', { email: this.email().trim(), consent: true },
      this.openedAt, this.nickname);
    this.sending.set(false);
    if (result.ok) this.sent.set(true);
    else this.error.set(result.message);
  }
}
