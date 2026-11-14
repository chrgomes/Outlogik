import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { me, membership } from '../../../testing/fixtures';
import { AuthService } from '../../core/auth.service';
import { CurrentOrgService } from '../../core/current-org.service';
import { LayoutService } from '../../core/layout.service';
import { Sidebar } from './sidebar';

describe('Sidebar', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ imports: [Sidebar], providers: [provideRouter([])] });
  });

  function render(permissions: string[]) {
    TestBed.inject(AuthService).me.set(me([membership({ permissions })]));
    TestBed.inject(CurrentOrgService).slug.set('acme');
    const fixture = TestBed.createComponent(Sidebar);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    const links = [...el.querySelectorAll('nav a')].map((a) => a.textContent!.trim());
    return { fixture, el, links };
  }

  it('shows only the sections the role can open', () => {
    const { links, el } = render(['dashboard.read', 'clients.read', 'websites.read']);
    expect(links).toEqual(['Dashboard', 'Clients', 'Websites']);
    expect(el.textContent).not.toContain('Settings');
  });

  it('shows settings to roles that can manage them', () => {
    const { links } = render([
      'dashboard.read', 'clients.read', 'websites.read', 'organization.update', 'members.read',
      'roles.read',
    ]);
    expect(links).toEqual(['Dashboard', 'Clients', 'Websites', 'Organization', 'Team', 'Roles']);
  });

  it('links point into the current organization', () => {
    const { el } = render(['clients.read']);
    expect(el.querySelector('nav a')!.getAttribute('href')).toBe('/o/acme/clients');
  });

  it('collapses to icons with accessible names, and remembers it', () => {
    const { fixture, el } = render(['clients.read']);
    TestBed.inject(LayoutService).toggleCollapsed();
    fixture.detectChanges();
    expect(el.classList).toContain('collapsed');
    expect(el.querySelector('nav a')!.getAttribute('aria-label')).toBe('Clients');
    expect(localStorage.getItem('ol-sidebar-collapsed')).toBe('1');
  });
});
