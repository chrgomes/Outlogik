import { HttpErrorResponse } from '@angular/common/http';
import { AbstractControl, FormGroup } from '@angular/forms';

export interface ApiProblem {
  status: number;
  code: string;
  message: string;
  /** Field name → message, from validation errors. */
  fields: Record<string, string>;
  details: unknown;
}

/** Turns any HTTP failure into one shape the UI can show. */
export function apiProblem(err: unknown): ApiProblem {
  if (!(err instanceof HttpErrorResponse)) {
    return { status: 0, code: 'unknown', message: 'Something went wrong.', fields: {}, details: null };
  }
  if (err.status === 0) {
    return { status: 0, code: 'network', fields: {}, details: null,
      message: "Can't reach Outlogik. Check your connection and try again." };
  }
  const body = err.error?.error as { code?: string; message?: string; details?: unknown } | undefined;
  const fields: Record<string, string> = {};
  if (Array.isArray(body?.details)) {
    for (const d of body.details as { field?: string; message?: string }[]) {
      if (d.field && d.message && !fields[d.field]) fields[d.field] = humanise(d.message);
    }
  }
  let message = body?.message ?? 'Something went wrong. Please try again.';
  if (err.status === 429) {
    const wait = Number((body?.details as { retry_after?: number })?.retry_after ?? 0);
    message = wait > 90
      ? `Too many attempts. Try again in ${Math.ceil(wait / 60)} minutes.`
      : 'Too many attempts. Try again in a minute.';
  }
  return { status: err.status, code: body?.code ?? 'error', message, fields, details: body?.details };
}

/** Puts server-side field errors on the matching form controls (as `server`). */
export function applyFieldErrors(form: FormGroup, fields: Record<string, string>): boolean {
  let applied = false;
  for (const [name, message] of Object.entries(fields)) {
    const control: AbstractControl | null = form.get(name);
    if (control) {
      control.setErrors({ ...control.errors, server: message });
      control.markAsTouched();
      applied = true;
    }
  }
  return applied;
}

function humanise(message: string): string {
  return message
    .replace(/^Value error, /, '')
    .replace(/^String should have at least (\d+) characters?$/, 'Use at least $1 characters.')
    .replace(/^String should have at most (\d+) characters?$/, 'Use at most $1 characters.')
    .replace(/^value is not a valid email address:.*$/, 'Enter a valid email address.')
    .replace(/^Field required$/, 'This field is required.');
}

/** Only same-app paths are allowed as a post-login destination (no open redirects). */
export function safeReturnUrl(value: string | null | undefined): string {
  if (!value || !value.startsWith('/') || value.startsWith('//') || value.startsWith('/\\')) {
    return '/';
  }
  return value;
}
