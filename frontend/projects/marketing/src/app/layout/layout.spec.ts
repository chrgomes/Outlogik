import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';

import { provideIcons } from '@brand/icon/icon';
import { MARKETING_ICONS } from '@brand/icon/icons-marketing';
import { APP_URL, MODULES } from '../config/site';
import { Footer } from './footer/footer';
import { Header } from './header/header';

function setup() {
  TestBed.configureTestingModule({
    providers: [provideRouter([{ path: '**', children: [] }]), provideIcons(MARKETING_ICONS)],
  });
}

describe('Header', () => {
  function render() {
    setup();
    const fixture = TestBed.createComponent(Header);
    fixture.detectChanges();
    return { fixture, el: fixture.nativeElement as HTMLElement };
  }

  const trigger = (el: HTMLElement, menu: string) =>
    el.querySelector<HTMLButtonElement>(`#menu-button-${menu}`)!;
  const panel = (el: HTMLElement, menu: string) => el.querySelector<HTMLElement>(`#menu-${menu}`)!;

  it('links Log in and Get started to the app', () => {
    const { el } = render();
    expect(el.querySelector('.mk-header__login')!.getAttribute('href')).toBe(`${APP_URL}/login`);
    expect(el.querySelector('.mk-header__cta')!.getAttribute('href')).toBe(`${APP_URL}/register`);
  });

  it('opens one menu at a time and reports it to assistive technology', () => {
    const { fixture, el } = render();
    expect(panel(el, 'platform').hidden).toBe(true);
    trigger(el, 'platform').click();
    fixture.detectChanges();
    expect(trigger(el, 'platform').getAttribute('aria-expanded')).toBe('true');
    expect(panel(el, 'platform').hidden).toBe(false);

    trigger(el, 'solutions').click();
    fixture.detectChanges();
    expect(panel(el, 'platform').hidden).toBe(true);
    expect(panel(el, 'solutions').hidden).toBe(false);
  });

  it('closes on Escape and returns focus to the menu button', () => {
    const { fixture, el } = render();
    document.body.appendChild(el);
    trigger(el, 'company').click();
    fixture.detectChanges();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    fixture.detectChanges();
    expect(panel(el, 'company').hidden).toBe(true);
    expect(document.activeElement).toBe(trigger(el, 'company'));
    el.remove();
  });

  it('closes on a click outside, and after navigating', async () => {
    const { fixture, el } = render();
    trigger(el, 'platform').click();
    fixture.detectChanges();
    document.body.click();
    fixture.detectChanges();
    expect(panel(el, 'platform').hidden).toBe(true);

    trigger(el, 'platform').click();
    fixture.detectChanges();
    await TestBed.inject(Router).navigateByUrl('/platform');
    fixture.detectChanges();
    expect(panel(el, 'platform').hidden).toBe(true);
  });

  it('labels every module that is not built yet', () => {
    const { el } = render();
    const items = [...el.querySelectorAll('#menu-platform .mk-mega__link')];
    expect(items).toHaveLength(MODULES.length);
    for (const [i, m] of MODULES.entries()) {
      expect(items[i].getAttribute('href')).toBe(`/platform/${m.slug}`);
      expect(items[i].textContent!.includes('In development')).toBe(m.status === 'in-development');
    }
  });

  it('hides Resources until there is published content', () => {
    const { el } = render();
    expect(el.querySelector('#menu-button-resources')).toBeNull();
    expect(el.textContent).not.toContain('Resources');
  });
});

describe('Footer', () => {
  it('links every module and audience, and has no legal links until they exist', () => {
    setup();
    const fixture = TestBed.createComponent(Footer);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const hrefs = [...el.querySelectorAll('a')].map((a) => a.getAttribute('href'));
    for (const m of MODULES) expect(hrefs).toContain(`/platform/${m.slug}`);
    expect(hrefs).toContain('/solutions/marketing-agencies');
    expect(hrefs).toContain(`${APP_URL}/register`);
    expect(el.querySelector('.mk-footer__legal')).toBeNull();
    expect(el.textContent).toContain(`© ${new Date().getFullYear()} Outlogik`);
  });
});
