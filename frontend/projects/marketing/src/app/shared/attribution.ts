import { DOCUMENT, Injectable, PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

export interface Attribution {
  page?: string;
  landing_page?: string;
  referrer?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_term?: string;
  utm_content?: string;
}

const KEY = 'ol-visit';
const UTM = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'] as const;

/**
 * Where a visitor came from, sent with the website's forms (spec §10: lead source and UTM
 * attribution). Recorded on the first page of each visit and kept in sessionStorage only: no
 * cookies, nothing sent anywhere until the visitor submits a form, and gone when the tab closes.
 */
@Injectable({ providedIn: 'root' })
export class VisitAttribution {
  private readonly browser = isPlatformBrowser(inject(PLATFORM_ID));
  private readonly document = inject(DOCUMENT);

  /** Call once when the site starts in the browser. */
  record(): void {
    if (!this.browser) return;
    try {
      if (sessionStorage.getItem(KEY)) return;
      const location = this.document.location;
      const params = new URLSearchParams(location.search);
      const visit: Attribution = { landing_page: (location.pathname + location.search).slice(0, 500) };
      const referrer = this.document.referrer;
      if (referrer && new URL(referrer).origin !== location.origin) visit.referrer = referrer.slice(0, 500);
      for (const key of UTM) {
        const value = params.get(key);
        if (value) visit[key] = value.slice(0, 120);
      }
      sessionStorage.setItem(KEY, JSON.stringify(visit));
    } catch {
      // Storage blocked or unavailable: attribution is optional.
    }
  }

  /** The visit's attribution plus the page the form is on. */
  forForm(): Attribution {
    const page = this.browser ? this.document.location.pathname.slice(0, 300) : undefined;
    try {
      const stored = this.browser ? sessionStorage.getItem(KEY) : null;
      return { ...(stored ? (JSON.parse(stored) as Attribution) : {}), page };
    } catch {
      return { page };
    }
  }
}
