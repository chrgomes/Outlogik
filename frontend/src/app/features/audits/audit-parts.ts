import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { Severity } from '../../core/api.types';

export const SEVERITY_LABEL: Record<Severity, string> = { error: 'Error', warning: 'Warning', notice: 'Notice' };
export const AREA_LABEL: Record<string, string> = {
  technical: 'Technical', seo: 'SEO', ai_search: 'AI search readiness',
};

/** Errors, warnings and notices as small counts. */
@Component({
  selector: 'ol-issue-counts',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span class="counts">
      <span class="sev sev-error" [attr.aria-label]="errors() + ' errors'">{{ errors() }}</span>
      <span class="sev sev-warning" [attr.aria-label]="warnings() + ' warnings'">{{ warnings() }}</span>
      <span class="sev sev-notice" [attr.aria-label]="notices() + ' notices'">{{ notices() }}</span>
    </span>
  `,
  styles: `
    .counts { display: inline-flex; gap: 0.375rem; }
    .sev { min-width: 2rem; padding: 0.0625rem 0.5rem; border-radius: 999px; font-size: 0.75rem;
      font-weight: 600; text-align: center; font-variant-numeric: tabular-nums; }
    .sev-error { background: var(--bs-danger-bg-subtle); color: var(--bs-danger-text-emphasis); }
    .sev-warning { background: var(--bs-warning-bg-subtle); color: var(--bs-warning-text-emphasis); }
    .sev-notice { background: var(--ol-surface-active); color: var(--ol-text); }
  `,
})
export class IssueCounts {
  readonly errors = input.required<number>();
  readonly warnings = input.required<number>();
  readonly notices = input.required<number>();
}

/** A severity badge. */
@Component({
  selector: 'ol-severity',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span class="sev" [class]="'sev sev-' + value()">{{ label() }}</span>`,
  styles: `
    .sev { padding: 0.0625rem 0.5rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
    .sev-error { background: var(--bs-danger-bg-subtle); color: var(--bs-danger-text-emphasis); }
    .sev-warning { background: var(--bs-warning-bg-subtle); color: var(--bs-warning-text-emphasis); }
    .sev-notice { background: var(--ol-surface-active); color: var(--ol-text); }
  `,
})
export class SeverityBadge {
  readonly value = input.required<Severity>();
  protected readonly label = computed(() => SEVERITY_LABEL[this.value()]);
}

/** An issue's details (a small JSON object) as readable text. */
export function describeDetails(details: Record<string, unknown>): string {
  const NAMES: Record<string, string> = {
    linked_from: 'Linked from', status: 'Status', error: 'Error', hops: 'Redirects',
    seconds: 'Seconds', title: 'Title', length: 'Characters', images: 'Images without alt text',
    of: 'Images on the page', words: 'Words', canonical: 'Canonical', headings: 'H1 headings',
    same_as: 'Same as', questions: 'Questions', blocked: 'Blocked', score: 'Mobile score',
    name: 'Names', telephone: 'Phone numbers', address: 'Addresses',
  };
  return Object.entries(details).map(([key, value]) => {
    let text: string;
    if (Array.isArray(value)) text = value.join(', ');
    else if (value && typeof value === 'object') {
      text = Object.entries(value as Record<string, unknown>)
        .map(([v, pages]) => `"${v}" (${(pages as string[]).length} page${(pages as string[]).length === 1 ? '' : 's'})`)
        .join(' · ');
    } else text = String(value);
    return `${NAMES[key] ?? key}: ${text}`;
  }).join(' — ');
}
