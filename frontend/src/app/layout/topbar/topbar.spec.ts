import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { me, membership } from '../../../testing/fixtures';
import { AuthService } from '../../core/auth.service';
import { CurrentOrgService } from '../../core/current-org.service';
import { Topbar } from './topbar';

describe('Topbar', () => {
  beforeEach(() => {
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
});
