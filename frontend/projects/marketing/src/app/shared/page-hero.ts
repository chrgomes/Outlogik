import { ChangeDetectionStrategy, Component, DestroyRef, effect, inject, input } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { Seo, breadcrumbData } from '../seo/seo';

export interface Crumb {
  label: string;
  path?: string;
}

/** Heading block for inner pages: breadcrumbs, eyebrow, the page's single h1, a lead, actions. */
@Component({
  selector: 'mk-page-hero',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="mk-page-hero">
      <div class="mk-container">
        @if (crumbs().length) {
          <nav aria-label="Breadcrumb">
            <ol class="mk-crumbs">
              <li><a routerLink="/">Home</a></li>
              @for (c of crumbs(); track c.label; let last = $last) {
                <li>
                  @if (c.path && !last) {
                    <a [routerLink]="c.path">{{ c.label }}</a>
                  } @else {
                    <span aria-current="page">{{ c.label }}</span>
                  }
                </li>
              }
            </ol>
          </nav>
        }
        @if (eyebrow()) { <p class="mk-eyebrow">{{ eyebrow() }}</p> }
        <h1 class="mk-display mk-page-hero__title">{{ title() }}</h1>
        @if (lead()) { <p class="mk-lead">{{ lead() }}</p> }
        <ng-content />
      </div>
    </section>
  `,
})
export class PageHero {
  readonly title = input.required<string>();
  readonly lead = input('');
  readonly eyebrow = input('');
  readonly crumbs = input<Crumb[]>([]);

  constructor() {
    // The same trail, as structured data for search results.
    const seo = inject(Seo);
    const route = inject(ActivatedRoute);
    effect(() => {
      const path = '/' + route.snapshot.pathFromRoot.flatMap((r) => r.url.map((u) => u.path)).join('/');
      if (this.crumbs().length) seo.add('breadcrumbs', breadcrumbData(this.crumbs(), path));
    });
    inject(DestroyRef).onDestroy(() => seo.remove('breadcrumbs'));
  }
}
