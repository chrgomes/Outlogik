import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'mk-not-found',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="mk-section">
      <div class="mk-container mk-narrow">
        <p class="mk-eyebrow">404</p>
        <h1 class="mk-h1">We couldn’t find that page</h1>
        <p class="mk-lead">It may have moved, or the address may be mistyped.</p>
        <a routerLink="/" class="btn btn-primary">Go to the homepage</a>
      </div>
    </section>
  `,
})
export class NotFound {}
