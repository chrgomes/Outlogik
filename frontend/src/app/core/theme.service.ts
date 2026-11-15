import { DOCUMENT } from '@angular/common';
import { Injectable, computed, effect, inject, signal } from '@angular/core';

import { prefs } from './storage';

export type ThemePreference = 'light' | 'dark' | 'system';
export const THEME_KEY = 'ol-theme';

/**
 * Light / dark / follow-the-system theme. Applies Bootstrap's data-bs-theme on <html>.
 * index.html sets the same attribute before Angular starts, so there's no flash.
 */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly doc = inject(DOCUMENT);
  private readonly media =
    typeof matchMedia === 'function' ? matchMedia('(prefers-color-scheme: dark)') : null;
  private readonly systemDark = signal(this.media?.matches ?? false);

  readonly preference = signal<ThemePreference>(readPreference());
  readonly resolved = computed<'light' | 'dark'>(() => {
    const pref = this.preference();
    return pref === 'system' ? (this.systemDark() ? 'dark' : 'light') : pref;
  });

  constructor() {
    this.media?.addEventListener('change', (e) => this.systemDark.set(e.matches));
    effect(() => this.doc.documentElement.setAttribute('data-bs-theme', this.resolved()));
  }

  set(preference: ThemePreference): void {
    this.preference.set(preference);
    prefs.set(THEME_KEY, preference);
  }
}

function readPreference(): ThemePreference {
  const stored = prefs.get(THEME_KEY);
  return stored === 'light' || stored === 'dark' ? stored : 'system';
}
