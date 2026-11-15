import { HttpClient } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { Meta } from '@angular/platform-browser';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { failure } from '../../shared/lead-api';

type Action = 'confirm' | 'unsubscribe';

const TEXT: Record<Action, { title: string; lead: string; button: string; done: string; doneText: string }> = {
  confirm: {
    title: 'Confirm your subscription',
    lead: 'Click the button to start receiving Outlogik’s newsletter.',
    button: 'Confirm my subscription',
    done: 'You’re subscribed.',
    doneText: 'Thanks for confirming. Every newsletter includes a link to unsubscribe.',
  },
  unsubscribe: {
    title: 'Unsubscribe from the newsletter',
    lead: 'Click the button and we’ll stop sending you Outlogik’s newsletter.',
    button: 'Unsubscribe',
    done: 'You’ve been unsubscribed.',
    doneText: 'You won’t receive the newsletter any more. You can subscribe again at any time.',
  },
};

/**
 * The pages linked from newsletter emails (/newsletter/confirm and /newsletter/unsubscribe).
 * Nothing happens until the visitor clicks the button, so email security scanners that open
 * links can't confirm or unsubscribe anyone. Hidden from search engines.
 */
@Component({
  selector: 'mk-newsletter-link',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="mk-section">
      <div class="mk-container mk-narrow">
        @if (state() === 'done') {
          <h1 class="mk-h1" tabindex="-1">{{ text.done }}</h1>
          <p class="mk-lead">{{ text.doneText }}</p>
          <a routerLink="/" class="btn btn-outline-dark">Go to the homepage</a>
        } @else {
          <h1 class="mk-h1">{{ text.title }}</h1>
          @if (!token) {
            <p class="mk-lead">This link is incomplete. Please use the full link from the email.</p>
          } @else {
            <p class="mk-lead">{{ text.lead }}</p>
            <div role="alert">
              @if (error(); as message) { <p class="mk-form-error">{{ message }}</p> }
            </div>
            <button type="button" class="btn btn-primary btn-lg" (click)="go()" [disabled]="state() === 'sending'">
              {{ state() === 'sending' ? 'One moment…' : text.button }}
            </button>
          }
        }
      </div>
    </section>
  `,
})
export class NewsletterLink {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  protected readonly action = this.route.snapshot.data['action'] as Action;
  protected readonly text = TEXT[this.action];
  protected readonly token = this.route.snapshot.queryParamMap.get('token');
  protected readonly state = signal<'ready' | 'sending' | 'done'>('ready');
  protected readonly error = signal<string | null>(null);

  constructor() {
    const meta = inject(Meta);
    meta.updateTag({ name: 'robots', content: 'noindex' });
    inject(DestroyRef).onDestroy(() => meta.removeTag('name="robots"'));
  }

  protected async go(): Promise<void> {
    this.state.set('sending');
    this.error.set(null);
    try {
      await firstValueFrom(this.http.post(`/api/public/newsletter/${this.action}`, { token: this.token }));
      this.state.set('done');
    } catch (e) {
      this.error.set(failure(e).message);
      this.state.set('ready');
    }
  }
}
