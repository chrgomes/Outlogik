import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Logo } from '@brand/logo/logo';
import {
  AUDIENCES,
  COMPANY,
  DESCRIPTION,
  LEGAL,
  MODULES,
  RESOURCES,
  TAGLINE,
  appLink,
} from '../../config/site';

@Component({
  selector: 'mk-footer',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Logo],
  host: { class: 'mk-footer' },
  template: `
    <div class="mk-container">
      <div class="mk-footer__top">
        <div class="mk-footer__brand">
          <a routerLink="/" aria-label="Outlogik home" class="mk-footer__logo"><ol-logo /></a>
          <p class="mk-footer__tagline">{{ tagline }}</p>
          <p class="mk-footer__desc">{{ description }}</p>
        </div>
        <nav class="mk-footer__cols" aria-label="Footer">
          <div>
            <h2 class="mk-footer__heading">Platform</h2>
            <ul>
              <li><a routerLink="/platform">Overview</a></li>
              @for (m of modules; track m.slug) {
                <li><a [routerLink]="['/platform', m.slug]">{{ m.name }}</a></li>
              }
            </ul>
          </div>
          <div>
            <h2 class="mk-footer__heading">Solutions</h2>
            <ul>
              @for (a of audiences; track a.slug) {
                <li><a [routerLink]="['/solutions', a.slug]">{{ a.name }}</a></li>
              }
            </ul>
          </div>
          @if (resources.length) {
            <div>
              <h2 class="mk-footer__heading">Resources</h2>
              <ul>
                @for (r of resources; track r.path) { <li><a [routerLink]="r.path">{{ r.label }}</a></li> }
              </ul>
            </div>
          }
          <div>
            <h2 class="mk-footer__heading">Company</h2>
            <ul>
              @for (c of company; track c.path) { <li><a [routerLink]="c.path">{{ c.label }}</a></li> }
              <li><a routerLink="/pricing">Pricing</a></li>
              <li><a [href]="loginUrl">Log in</a></li>
              <li><a [href]="registerUrl">Create an account</a></li>
            </ul>
          </div>
        </nav>
      </div>
      <div class="mk-footer__bottom">
        <p>© {{ year }} Outlogik. All rights reserved.</p>
        @if (legal.length) {
          <ul class="mk-footer__legal">
            @for (l of legal; track l.path) { <li><a [routerLink]="l.path">{{ l.label }}</a></li> }
          </ul>
        }
      </div>
    </div>
  `,
})
export class Footer {
  protected readonly modules = MODULES;
  protected readonly audiences = AUDIENCES;
  protected readonly resources = RESOURCES;
  protected readonly company = COMPANY;
  protected readonly legal = LEGAL;
  protected readonly tagline = TAGLINE;
  protected readonly description = DESCRIPTION;
  protected readonly loginUrl = appLink('/login');
  protected readonly registerUrl = appLink('/register');
  protected readonly year = new Date().getFullYear();
}
