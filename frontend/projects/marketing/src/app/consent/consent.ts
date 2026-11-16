import { isPlatformBrowser } from '@angular/common';
import { DOCUMENT, Injectable, PLATFORM_ID, computed, effect, inject, signal, untracked } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

import { SiteData } from '../config/site-data';

export type Choice = 'granted' | 'denied';

/** The one cookie the site sets itself: the visitor's analytics choice (strictly necessary). */
export const CONSENT_COOKIE = 'ol_consent';
const CONSENT_DAYS = 365;
/** Cookies the analytics tools set, removed when a visitor withdraws consent. */
const ANALYTICS_COOKIES = /^(_ga|_gid|_gat|_gcl|_clck|_clsk|CLID|MUID|ANONCHK|SM)/;


type Win = Window & { dataLayer?: unknown[]; gtag?: (...args: unknown[]) => void; clarity?: unknown };

/**
 * Analytics with consent (Phase 1.5 plan, decision 9). Every tool is optional and off unless its
 * ID is set in the admin area. Nothing is loaded, and no banner is shown, until one is. Then:
 * - the banner asks once, with Accept and Reject given equal weight;
 * - tools load only after Accept, and the choice is remembered for a year in one first-party
 *   cookie (`ol_consent`);
 * - "Cookie settings" in the footer reopens the choice; withdrawing deletes the tools' cookies
 *   and reloads the page so their code is gone.
 */
@Injectable({ providedIn: 'root' })
export class Consent {
  private readonly browser = isPlatformBrowser(inject(PLATFORM_ID));
  private readonly document = inject(DOCUMENT);
  private readonly settings = inject(SiteData).settings;
  private readonly router = inject(Router);

  /** The visitor's choice, or null if they haven't made one (always null on the server). */
  readonly choice = signal<Choice | null>(null);
  /** True once running in the browser, so the banner never appears in server-rendered HTML. */
  readonly ready = signal(false);
  readonly panelOpen = signal(false);

  /** The analytics tools switched on in the admin area. */
  readonly tools = computed<string[]>(() => {
    const s = this.settings();
    return [
      ...(s.ga4_measurement_id ? ['Google Analytics'] : []),
      ...(s.gtm_container_id ? ['Google Tag Manager'] : []),
      ...(s.clarity_project_id ? ['Microsoft Clarity'] : []),
    ];
  });
  readonly needed = computed(() => this.tools().length > 0);
  readonly showBanner = computed(
    () => this.ready() && this.needed() && (this.choice() === null || this.panelOpen()));

  private loaded = false;

  constructor() {
    effect(() => {
      if (this.ready() && this.choice() === 'granted' && this.needed()) untracked(() => this.load());
    });
  }

  /** Call once in the browser, after the first render (from the root component). */
  start(): void {
    if (!this.browser) return;
    this.choice.set(this.readCookie());
    this.ready.set(true);
  }

  open(): void {
    this.panelOpen.set(true);
  }

  accept(): void {
    this.save('granted');
    this.panelOpen.set(false);
  }

  reject(): void {
    const withdrawing = this.choice() === 'granted';
    this.save('denied');
    this.panelOpen.set(false);
    if (withdrawing) {
      this.deleteAnalyticsCookies();
      // The tools' code is already running; a reload is the only way to stop it.
      this.document.location.reload();
    }
  }

  /** Reports a conversion (e.g. a consultation request) to the tools, if the visitor accepted. */
  track(event: string, params: Record<string, string> = {}): void {
    if (!this.loaded) return;
    const w = this.document.defaultView as Win;
    if (this.settings().ga4_measurement_id) w.gtag?.('event', event, params);
    if (this.settings().gtm_container_id) w.dataLayer?.push({ event, ...params });
  }

  private save(choice: Choice): void {
    this.choice.set(choice);
    const secure = this.document.location.protocol === 'https:' ? '; Secure' : '';
    this.document.cookie =
      `${CONSENT_COOKIE}=${choice}; Max-Age=${CONSENT_DAYS * 86400}; Path=/; SameSite=Lax${secure}`;
  }

  private readCookie(): Choice | null {
    const match = this.document.cookie.match(new RegExp(`(?:^|; )${CONSENT_COOKIE}=(granted|denied)`));
    return (match?.[1] as Choice | undefined) ?? null;
  }

  private deleteAnalyticsCookies(): void {
    const host = this.document.location.hostname;
    const domains = ['', host, '.' + host, '.' + host.split('.').slice(-2).join('.')];
    for (const cookie of this.document.cookie.split('; ')) {
      const name = cookie.split('=')[0];
      if (!ANALYTICS_COOKIES.test(name)) continue;
      for (const d of domains) {
        this.document.cookie = `${name}=; Max-Age=0; Path=/${d ? '; Domain=' + d : ''}`;
      }
    }
  }

  private load(): void {
    if (this.loaded) return;
    this.loaded = true;
    const s = this.settings();
    const w = this.document.defaultView as Win;
    w.dataLayer = w.dataLayer ?? [];

    if (s.ga4_measurement_id) {
      // Page views are sent on each navigation below, because the site is a single-page app.
      // gtag must queue the `arguments` object itself, as Google's own snippet does.
      w.gtag = function gtag() { w.dataLayer!.push(arguments); };
      w.gtag('js', new Date());
      w.gtag('config', s.ga4_measurement_id, { send_page_view: false });
      this.script(`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(s.ga4_measurement_id)}`);
    }
    if (s.gtm_container_id) {
      w.dataLayer.push({ 'gtm.start': Date.now(), event: 'gtm.js' });
      this.script(`https://www.googletagmanager.com/gtm.js?id=${encodeURIComponent(s.gtm_container_id)}`);
    }
    if (s.clarity_project_id) {
      const queue: unknown[] = [];
      w.clarity = w.clarity ?? Object.assign((...args: unknown[]) => queue.push(args), { q: queue });
      this.script(`https://www.clarity.ms/tag/${encodeURIComponent(s.clarity_project_id)}`);
    }

    this.pageView();
    this.router.events.pipe(filter((e) => e instanceof NavigationEnd)).subscribe(() => this.pageView());
  }

  private lastPageView = '';

  /** One page view per address: the first load and the router's first navigation can coincide. */
  private pageView(): void {
    const w = this.document.defaultView as Win;
    if (this.document.location.href === this.lastPageView) return;
    this.lastPageView = this.document.location.href;
    const params = { page_location: this.document.location.href, page_title: this.document.title };
    if (this.settings().ga4_measurement_id) w.gtag?.('event', 'page_view', params);
    if (this.settings().gtm_container_id) w.dataLayer?.push({ event: 'page_view', ...params });
  }

  private script(src: string): void {
    const el = this.document.createElement('script');
    el.async = true;
    el.src = src;
    this.document.head.appendChild(el);
  }
}
