import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Logo } from '@brand/logo/logo';
import {
  AUDIENCES,
  COMPANY,
  CONSULTATION_PATH,
  LEGAL,
  LOGIN_URL,
  RESOURCES,
  SERVICES,
  SOCIAL_LABELS,
} from '../../config/site';
import { SiteData } from '../../config/site-data';
import { Newsletter } from './newsletter';
import { Consent } from '../../consent/consent';

@Component({
  selector: 'mk-footer',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Logo, Newsletter],
  host: { class: 'mk-footer' },
  template: `
    <div class="mk-container">
      <div class="mk-footer__top">
        <div class="mk-footer__brand">
          <a routerLink="/" aria-label="Outlogik home" class="mk-footer__logo"><ol-logo /></a>
          <p class="mk-footer__tagline">{{ settings().tagline }}</p>
          <p class="mk-footer__desc">{{ settings().company_description }}</p>
          @if (settings().contact_email; as email) {
            <p class="mk-footer__contact"><a [href]="'mailto:' + email">{{ email }}</a></p>
          }
          @if (settings().phone; as phone) {
            <p class="mk-footer__contact"><a [href]="'tel:' + phone">{{ phone }}</a></p>
          }
          @if (settings().social_links.length) {
            <ul class="mk-footer__social" aria-label="Outlogik on social media">
              @for (s of settings().social_links; track s.url) {
                <li><a [href]="s.url" rel="noopener me" target="_blank">{{ socialLabels[s.network] ?? s.network }}</a></li>
              }
            </ul>
          }
        </div>
        <nav class="mk-footer__cols" aria-label="Footer">
          <div>
            <h2 class="mk-footer__heading">Services</h2>
            <ul>
              @for (s of services; track s.slug) {
                <li><a [routerLink]="['/services', s.slug]">{{ s.name }}</a></li>
              }
            </ul>
          </div>
          <div>
            <h2 class="mk-footer__heading">Who we help</h2>
            <ul>
              @for (a of audiences; track a.slug) {
                <li><a [routerLink]="['/who-we-help', a.slug]">{{ a.name }}</a></li>
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
              <li><a routerLink="/how-we-work">How we work</a></li>
              <li><a routerLink="/pricing">Pricing</a></li>
              @for (c of company; track c.path) { <li><a [routerLink]="c.path">{{ c.label }}</a></li> }
              <li><a [routerLink]="consultationPath">{{ settings().consultation_cta_label }}</a></li>
              <li><a [href]="loginUrl">Client log in</a></li>
            </ul>
          </div>
        </nav>
      </div>
      <div class="mk-footer__newsletter">
        <!-- Loaded when the footer comes into view, so its code isn't part of every page load. -->
        @defer (on viewport) {
          <mk-newsletter />
        } @placeholder {
          <div class="mk-newsletter__placeholder"><h2 class="mk-footer__heading">Newsletter</h2></div>
        }
      </div>
      <div class="mk-footer__bottom">
        <p>© {{ year }} Outlogik. All rights reserved.</p>
        @if (site.legalReady() || consent.needed()) {
          <ul class="mk-footer__legal">
            @if (site.legalReady()) {
              @for (l of legal; track l.path) { <li><a [routerLink]="l.path">{{ l.label }}</a></li> }
            }
            @if (consent.needed()) {
              <li><button type="button" class="mk-footer__link-btn" (click)="consent.open()">Cookie settings</button></li>
            }
          </ul>
        }
      </div>
    </div>
  `,
})
export class Footer {
  protected readonly site = inject(SiteData);
  protected readonly settings = this.site.settings;
  protected readonly consent = inject(Consent);
  protected readonly services = SERVICES;
  protected readonly audiences = AUDIENCES;
  protected readonly resources = RESOURCES;
  protected readonly company = COMPANY;
  protected readonly legal = LEGAL;
  protected readonly socialLabels = SOCIAL_LABELS;
  protected readonly loginUrl = LOGIN_URL;
  protected readonly consultationPath = CONSULTATION_PATH;
  protected readonly year = new Date().getFullYear();
}
