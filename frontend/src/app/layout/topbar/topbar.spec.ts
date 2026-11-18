import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { me, membership } from '../../../testing/fixtures';
import { flushPending } from '../../../testing/org-setup';
import { Workspace } from '../../core/api.types';
import { WorkspaceService } from '../../core/workspace.service';
import { AuthService } from '../../core/auth.service';
import { CurrentOrgService } from '../../core/current-org.service';
import { Topbar } from './topbar';

describe('Topbar', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [Topbar],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    TestBed.inject(AuthService).me.set(me([
      membership({ organization_slug: 'acme', organization_name: 'Acme', role_name: 'Owner' }),
      membership({ organization_id: 'org-2', organization_slug: 'globex',
        organization_name: 'Globex', role_name: 'Client' }),
    ]));
    TestBed.inject(CurrentOrgService).slug.set('globex');
  });

  it('shows the current organization, role and user initials', () => {
    const fixture = TestBed.createComponent(Topbar);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.org-name')!.textContent).toContain('Globex');
    expect(el.querySelector('.org-role')!.textContent).toContain('Client');
    expect(el.querySelector('.avatar')!.textContent!.trim()).toBe('OO');
  });

  it('lists every organization in the switcher', () => {
    const fixture = TestBed.createComponent(Topbar);
    fixture.detectChanges();
    (fixture.nativeElement.querySelector('.org-switcher') as HTMLButtonElement).click();
    fixture.detectChanges();
    const items = [...document.querySelectorAll('.ol-menu [role="menuitemradio"]')];
    expect(items.map((i) => i.textContent!.replace(/\s+/g, ' ').trim())).toEqual([
      'Acme Owner', 'Globex Client',
    ]);
    expect(items[1].getAttribute('aria-checked')).toBe('true');
  });

  describe('workspace switcher', () => {
    const ws = (over: Partial<Workspace>): Workspace => ({
      id: 'w-own', kind: 'own', name: 'Globex', client_id: null, client_status: null,
      website_count: 0, created_at: '2026-11-18T00:00:00Z', ...over,
    });

    async function render(kind: 'agency' | 'business', list: Workspace[]) {
      TestBed.inject(AuthService).me.set(me([membership({
        organization_slug: 'globex', organization_name: 'Globex', organization_kind: kind })]));
      const fixture = TestBed.createComponent(Topbar);
      fixture.detectChanges();
      await flushPending();
      TestBed.inject(HttpTestingController).expectOne('/api/v1/orgs/globex/workspaces').flush(list);
      await flushPending();
      fixture.detectChanges();
      return fixture;
    }

    it('lets an agency pick all, its own or a client workspace, and remembers it', async () => {
      const fixture = await render('agency', [
        ws({}), ws({ id: 'w-1', kind: 'client', name: 'Bakery', client_id: 'c1', client_status: 'active' }),
        ws({ id: 'w-2', kind: 'client', name: 'Dentist', client_id: 'c2', client_status: 'archived' }),
      ]);
      const el: HTMLElement = fixture.nativeElement;
      const button = el.querySelector('.ws-switcher') as HTMLButtonElement;
      expect(button.textContent).toContain('All workspaces');
      button.click();
      fixture.detectChanges();
      const items = [...document.querySelectorAll('.ws-menu [role="menuitemradio"]')] as HTMLElement[];
      expect(items.map((i) => i.textContent!.replace(/\s+/g, ' ').trim())).toEqual([
        'All workspaces', 'Globex', 'Bakery', 'Dentist · archived',
      ]);
      items[2].click();
      fixture.detectChanges();
      expect(TestBed.inject(WorkspaceService).current()?.name).toBe('Bakery');
      expect(button.textContent).toContain('Bakery');
      expect(localStorage.getItem('ol.workspace.globex')).toBe('w-1');
    });

    it('is not shown to a business, which always works in its own workspace', async () => {
      const fixture = await render('business', [ws({})]);
      expect(fixture.nativeElement.querySelector('.ws-switcher')).toBeNull();
      expect(TestBed.inject(WorkspaceService).current()?.id).toBe('w-own');
    });
  });
});
