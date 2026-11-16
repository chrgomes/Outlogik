import { ChangeDetectionStrategy, Component, ElementRef, effect, inject, viewChild } from '@angular/core';

import { Consent } from './consent';

/**
 * The cookie banner. Shown only when an analytics tool is switched on in the admin area and
 * the visitor hasn't chosen yet, or when they reopen it from "Cookie settings". Accept and
 * Reject look the same, so neither is nudged (CASL / PIPEDA guidance on meaningful consent).
 */
@Component({
  selector: 'mk-cookie-banner',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (consent.showBanner()) {
      <section class="mk-cookies" role="region" aria-labelledby="cookies-title" #panel tabindex="-1">
        <div class="mk-cookies__text">
          <h2 id="cookies-title" class="mk-cookies__title">Analytics cookies</h2>
          <p>
            With your permission, we use {{ toolList() }} to understand how people use this site,
            so we can improve it. These tools set cookies and receive information about your visit.
            We don’t use them unless you accept.
          </p>
          @if (consent.panelOpen() && consent.choice()) {
            <p class="mk-cookies__current">You currently {{ consent.choice() === 'granted' ? 'accept' : 'reject' }} analytics cookies.</p>
          }
        </div>
        <div class="mk-cookies__actions">
          <button type="button" class="btn mk-cookies__btn" (click)="consent.accept()">Accept analytics</button>
          <button type="button" class="btn mk-cookies__btn" (click)="consent.reject()">Reject analytics</button>
        </div>
      </section>
    }
  `,
})
export class CookieBanner {
  protected readonly consent = inject(Consent);
  private readonly panel = viewChild<ElementRef<HTMLElement>>('panel');

  constructor() {
    // When reopened from "Cookie settings", move focus to the banner.
    effect(() => {
      if (this.consent.panelOpen()) this.panel()?.nativeElement.focus();
    });
  }

  protected toolList(): string {
    const tools = this.consent.tools();
    return tools.length > 1 ? `${tools.slice(0, -1).join(', ')} and ${tools.at(-1)}` : tools[0];
  }
}
