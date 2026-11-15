import { inject } from '@angular/core';
import { Meta } from '@angular/platform-browser';

/**
 * Sets the page's meta description. Call from a page component's constructor.
 * Canonical URLs, Open Graph and structured data come in step 11.
 */
export function pageDescription(content: string): void {
  inject(Meta).updateTag({ name: 'description', content });
}
