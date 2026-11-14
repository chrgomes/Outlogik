import { TestBed } from '@angular/core/testing';

import { THEME_KEY, ThemeService } from './theme.service';

describe('ThemeService', () => {
  beforeEach(() => localStorage.clear());

  function create(): ThemeService {
    const service = TestBed.inject(ThemeService);
    TestBed.tick();
    return service;
  }

  it('follows the system by default', () => {
    const theme = create();
    expect(theme.preference()).toBe('system');
    expect(['light', 'dark']).toContain(document.documentElement.getAttribute('data-bs-theme'));
  });

  it('applies and remembers an explicit choice', () => {
    const theme = create();
    theme.set('dark');
    TestBed.tick();
    expect(document.documentElement.getAttribute('data-bs-theme')).toBe('dark');
    expect(localStorage.getItem(THEME_KEY)).toBe('dark');

    theme.set('light');
    TestBed.tick();
    expect(document.documentElement.getAttribute('data-bs-theme')).toBe('light');
  });

  it('reads the saved preference on start', () => {
    localStorage.setItem(THEME_KEY, 'dark');
    expect(create().resolved()).toBe('dark');
  });

  it('ignores junk in storage', () => {
    localStorage.setItem(THEME_KEY, 'purple');
    expect(create().preference()).toBe('system');
  });
});
