import { DOCUMENT, DestroyRef, Injectable, computed, effect, inject, signal } from '@angular/core';
import { Meta, Title } from '@angular/platform-browser';
import { ActivatedRouteSnapshot, RouterStateSnapshot, TitleStrategy } from '@angular/router';

import { SITE_URL } from '../config/site';
import { SiteData } from '../config/site-data';

/** A schema.org object for JSON-LD (https://schema.org). */
export type StructuredData = Record<string, unknown>;

export const SITE_NAME = 'Outlogik';
/** Shown when a link to the site is shared (1200×630). */
export const SHARE_IMAGE = `${SITE_URL}/images/og-default.png`;
export const LOGO_IMAGE = `${SITE_URL}/images/outlogik-logo-512.png`;

interface RouteMeta {
  /** The page's title, without the " · Outlogik" ending (that comes from the site settings). */
  title: string | null;
  /** A complete title used as-is (the homepage). */
  fullTitle: string | null;
  description: string | null;
  /** Path for the canonical URL, without query string or fragment. Null for error pages. */
  path: string | null;
  noindex: boolean;
}

/**
 * Search and sharing metadata for every page (spec §13): title, description, canonical URL,
 * Open Graph and Twitter cards, robots, and JSON-LD structured data. Rendered on the server, so
 * search engines and link previews see it without running JavaScript.
 *
 * The router (via SeoTitleStrategy) sets what the route knows; pages add a description and
 * structured data while they're open (pageDescription(), structuredData()). One effect writes
 * the tags whenever any of it, or the site settings, change.
 */
@Injectable({ providedIn: 'root' })
export class Seo {
  private readonly meta = inject(Meta);
  private readonly titleService = inject(Title);
  private readonly document = inject(DOCUMENT);
  private readonly settings = inject(SiteData).settings;

  readonly route = signal<RouteMeta>({ title: null, fullTitle: null, description: null, path: '/', noindex: false });
  readonly description = signal<string | null>(null);
  readonly data = signal<Map<string, StructuredData>>(new Map());

  readonly title = computed(() => {
    const r = this.route();
    return r.fullTitle ?? (r.title ? r.title + this.settings().seo_title_suffix : SITE_NAME);
  });

  constructor() {
    effect(() => this.write());
  }

  /** Adds structured data until the calling component is destroyed. Call from a constructor. */
  add(key: string, value: StructuredData): void {
    this.data.update((m) => new Map(m).set(key, value));
  }

  remove(key: string): void {
    this.data.update((m) => {
      const next = new Map(m);
      next.delete(key);
      return next;
    });
  }

  private write(): void {
    const r = this.route();
    const title = this.title();
    const description = this.description() ?? r.description ?? this.settings().seo_default_description;
    const url = r.path === null ? null : SITE_URL + r.path;

    this.titleService.setTitle(title);
    this.tag('name', 'description', description);
    this.tag('name', 'robots', r.noindex ? 'noindex' : null);
    this.tag('property', 'og:site_name', SITE_NAME);
    this.tag('property', 'og:type', 'website');
    this.tag('property', 'og:title', title);
    this.tag('property', 'og:description', description);
    this.tag('property', 'og:url', url);
    this.tag('property', 'og:image', SHARE_IMAGE);
    this.tag('property', 'og:image:width', '1200');
    this.tag('property', 'og:image:height', '630');
    this.tag('property', 'og:image:alt', 'Outlogik: digital marketing, handled.');
    this.tag('name', 'twitter:card', 'summary_large_image');
    this.canonical(r.noindex ? null : url);
    this.jsonLd([this.organization(), ...this.data().values()]);
  }

  /**
   * Who publishes the site, on every page. A ProfessionalService type with an address and
   * service area follows once those are known (Phase 1.5 plan, decisions 12 and A).
   */
  private organization(): StructuredData {
    const s = this.settings();
    return {
      '@type': 'Organization',
      '@id': ORGANIZATION_ID,
      name: SITE_NAME,
      url: SITE_URL + '/',
      logo: LOGO_IMAGE,
      description: s.company_description,
      slogan: s.tagline,
      ...(s.contact_email ? { email: s.contact_email } : {}),
      ...(s.phone ? { telephone: s.phone } : {}),
      ...(s.social_links.length ? { sameAs: s.social_links.map((l) => l.url) } : {}),
    };
  }

  private tag(attr: 'name' | 'property', key: string, content: string | null): void {
    const selector = `${attr}="${key}"`;
    if (content === null) this.meta.removeTag(selector);
    else this.meta.updateTag({ [attr]: key, content }, selector);
  }

  private canonical(url: string | null): void {
    let link = this.document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    if (url === null) {
      link?.remove();
      return;
    }
    if (!link) {
      link = this.document.createElement('link');
      link.setAttribute('rel', 'canonical');
      this.document.head.appendChild(link);
    }
    link.setAttribute('href', url);
  }

  private jsonLd(items: StructuredData[]): void {
    let script = this.document.head.querySelector<HTMLScriptElement>('script#ol-jsonld');
    if (!script) {
      script = this.document.createElement('script');
      script.id = 'ol-jsonld';
      script.type = 'application/ld+json';
      this.document.head.appendChild(script);
    }
    const graph = { '@context': 'https://schema.org', '@graph': items };
    // "<" is escaped so content can never close the script element.
    script.textContent = JSON.stringify(graph).replace(/</g, '\\u003c');
  }
}

/**
 * Runs after every navigation: passes the route's title, description and path to Seo. Route
 * titles are page names ("Pricing"); the ending (" · Outlogik") comes from the site settings.
 */
@Injectable({ providedIn: 'root' })
export class SeoTitleStrategy extends TitleStrategy {
  private readonly seo = inject(Seo);

  override updateTitle(snapshot: RouterStateSnapshot): void {
    let route: ActivatedRouteSnapshot = snapshot.root;
    while (route.firstChild) route = route.firstChild;
    const data = route.data;
    const notFound = route.routeConfig?.path === '**';
    this.seo.route.set({
      title: this.buildTitle(snapshot) ?? null,
      fullTitle: (data['fullTitle'] as string | undefined) ?? null,
      description: (data['description'] as string | undefined) ?? null,
      path: notFound ? null : '/' + snapshot.url.split(/[?#]/)[0].replace(/^\/+|\/+$/g, ''),
      noindex: notFound || data['noindex'] === true,
    });
  }
}

/** Sets the page's meta description while the calling page is open. Call from a constructor. */
export function pageDescription(content: string): void {
  const seo = inject(Seo);
  seo.description.set(content);
  inject(DestroyRef).onDestroy(() => {
    if (seo.description() === content) seo.description.set(null);
  });
}

/** Adds JSON-LD structured data while the calling page is open. Call from a constructor. */
export function structuredData(key: string, value: StructuredData): void {
  const seo = inject(Seo);
  seo.add(key, value);
  inject(DestroyRef).onDestroy(() => seo.remove(key));
}

/** The organization, as referenced by other structured data. */
export const ORGANIZATION_ID = `${SITE_URL}/#organization`;

/** A BreadcrumbList for an inner page, from "Home" down to the page itself. */
export function breadcrumbData(crumbs: { label: string; path?: string }[], currentPath: string): StructuredData {
  const items = [{ label: 'Home', path: '/' }, ...crumbs];
  return {
    '@type': 'BreadcrumbList',
    itemListElement: items.map((c, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: c.label,
      item: SITE_URL + (i === items.length - 1 ? currentPath : (c.path ?? '/')),
    })),
  };
}
