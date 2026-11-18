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

  function render(permissions: string[], kind: 'agency' | 'business' = 'agency') {
    TestBed.inject(AuthService).me.set(me([membership({ permissions, organization_kind: kind })]));
    TestBed.inject(CurrentOrgService).slug.set('acme');
    const fixture = TestBed.createComponent(Sidebar);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    const links = [...el.querySelectorAll('nav a')].map((a) => a.textContent!.trim());
    return { fixture, el, links };
  }

  it('shows only the sections the role can open', () => {
    // The built-in Client role: no team or role pages.
    const { links } = render(['organization.read', 'dashboard.read', 'clients.read', 'websites.read']);
    expect(links).toEqual(['Dashboard', 'Clients', 'Websites', 'Organization']);
  });

  it('hides the Settings heading when no settings page is available', () => {
    const { el } = render(['dashboard.read', 'clients.read']);
    expect(el.textContent).not.toContain('Settings');
  });

  it('shows settings to roles that can manage them', () => {
    const { links } = render([
      'dashboard.read', 'clients.read', 'websites.read', 'organization.read', 'members.read',
      'roles.read',
    ]);
    expect(links).toEqual(['Dashboard', 'Clients', 'Websites', 'Organization', 'Team', 'Roles']);
  });

  it('hides Clients from business accounts', () => {
    const { links } = render(['dashboard.read', 'clients.read', 'websites.read'], 'business');
    expect(links).toEqual(['Dashboard', 'Websites']);
  });

  it('shows Agency access to businesses and Linked businesses to agencies', () => {
    const perms = ['organization.read', 'access_grants.manage', 'linked_accounts.manage'];
    expect(render(perms, 'business').links).toEqual(['Organization', 'Agency access']);
  });

  it('shows Linked businesses to agencies', () => {
    const perms = ['organization.read', 'access_grants.manage', 'linked_accounts.manage'];
    expect(render(perms, 'agency').links).toEqual(['Organization', 'Linked businesses']);
  });

  it('links point into the current organization', () => {
    const { el } = render(['clients.read']);
    expect(el.querySelector('nav a')!.getAttribute('href')).toBe('/o/acme/clients');
  });

  it('nested pages get a real path, not an encoded slash', () => {
    const { el } = render(['members.read', 'roles.read']);
    const hrefs = [...el.querySelectorAll('nav a')].map((a) => a.getAttribute('href'));
    expect(hrefs).toEqual(['/o/acme/settings/members', '/o/acme/settings/roles']);
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
