import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { Consent } from '../consent/consent';
import { VisitAttribution } from './attribution';

export type SendResult = { ok: true } | { ok: false; message: string; fields: string[] };

/**
 * Sends the website's forms to the API (through this site's /api/public proxy). Every form
 * includes the visit's attribution and two spam checks: a hidden field people leave empty, and
 * how long the form was open.
 */
@Injectable({ providedIn: 'root' })
export class LeadApi {
  private readonly http = inject(HttpClient);
  private readonly attribution = inject(VisitAttribution);
  private readonly consent = inject(Consent);

  async send(path: string, body: object, openedAt: number, honeypot = ''): Promise<SendResult> {
    try {
      await firstValueFrom(this.http.post(`/api/public/${path}`, {
        ...body,
        nickname: honeypot,
        elapsed_ms: Math.max(0, Math.round(performance.now() - openedAt)),
        attribution: this.attribution.forForm(),
      }));
      this.reportConversion(path);
      return { ok: true };
    } catch (e) {
      return failure(e);
    }
  }

  private reportConversion(path: string): void {
    const conversion = CONVERSIONS[path];
    if (conversion) this.consent.track(...conversion);
  }
}

/** Conversion events for analytics tools (sent only if the visitor accepted analytics). */
const CONVERSIONS: Record<string, [string, Record<string, string>]> = {
  'leads/consultation': ['generate_lead', { form: 'consultation' }],
  'leads/contact': ['generate_lead', { form: 'contact' }],
  newsletter: ['sign_up', { method: 'newsletter' }],
};

export function failure(e: unknown): { ok: false; message: string; fields: string[] } {
  const res = e instanceof HttpErrorResponse ? e : null;
  const error = res?.error?.error as { code?: string; message?: string; details?: { field: string }[] } | undefined;
  if (res?.status === 422) {
    const fields = (Array.isArray(error?.details) ? error.details : []).map((d) => d.field.split('.')[0]);
    return { ok: false, message: 'Please check the highlighted fields and try again.', fields };
  }
  if (res?.status === 429) {
    return { ok: false, message: 'You’ve sent several requests in a short time. Please wait a few minutes and try again.', fields: [] };
  }
  if (res?.status === 400 && error?.message) return { ok: false, message: error.message, fields: [] };
  return { ok: false, message: 'Sorry, we couldn’t send that. Please try again in a moment.', fields: [] };
}
