import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { AUDIENCES, DEFAULT_SETTINGS, LOGIN_URL, SERVICES } from '../config/site';
import { answerSite, settle, setupMarketing } from '../../testing/marketing';
import { Footer } from './footer/footer';
import { Header } from './header/header';

describe('Header', () => {
  function render() {
    setupMarketing();
    const fixture = TestBed.createComponent(Header);
    fixture.detectChanges();
    return { fixture, el: fixture.nativeElement as HTMLElement };
  }

  const trigger = (el: HTMLElement, menu: string) =>
    el.querySelector<HTMLButtonElement>(`#menu-button-${menu}`)!;
  const panel = (el: HTMLElement, menu: string) => el.querySelector<HTMLElement>(`#menu-${menu}`)!;

  it('has the agency navigation', () => {
    const { el } = render();
    const labels = [...el.querySelectorAll('.mk-nav__list > li > :first-child')]
      .map((n) => n.textContent!.trim());
    expect(labels).toEqual(['Services', 'Who we help', 'How we work', 'Pricing', 'Company']);
  });

  it('Log in goes to the client portal; the main button books a consultation', () => {
    const { el } = render();
    expect(el.querySelector('.mk-header__login')!.getAttribute('href')).toBe(LOGIN_URL);
    const cta = el.querySelector('.mk-header__cta')!;
    expect(cta.getAttribute('href')).toBe('/book-a-consultation');
    expect(cta.textContent!.trim()).toBe('Book a free consultation');
    expect(el.innerHTML).not.toContain('/register');
  });

  it('lists every service and business type in its menu', () => {
    const { el } = render();
    expect([...el.querySelectorAll('#menu-services .mk-mega__link')].map((a) => a.getAttribute('href')))
      .toEqual(SERVICES.map((s) => `/services/${s.slug}`));
    expect([...el.querySelectorAll('#menu-who .mk-mega__link')].map((a) => a.getAttribute('href')))
      .toEqual(AUDIENCES.map((a) => `/who-we-help/${a.slug}`));
  });

  it('opens one menu at a time and reports it to assistive technology', () => {
    const { fixture, el } = render();
    expect(panel(el, 'services').hidden).toBe(true);
    trigger(el, 'services').click();
    fixture.detectChanges();
    expect(trigger(el, 'services').getAttribute('aria-expanded')).toBe('true');
    expect(panel(el, 'services').hidden).toBe(false);
    trigger(el, 'who').click();
    fixture.detectChanges();
    expect(panel(el, 'services').hidden).toBe(true);
    expect(panel(el, 'who').hidden).toBe(false);
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
    trigger(el, 'services').click();
    fixture.detectChanges();
    document.body.click();
    fixture.detectChanges();
    expect(panel(el, 'services').hidden).toBe(true);
    trigger(el, 'services').click();
    fixture.detectChanges();
    await TestBed.inject(Router).navigateByUrl('/services');
    fixture.detectChanges();
    expect(panel(el, 'services').hidden).toBe(true);
  });

  it('uses the call-to-action label managed in the admin area', async () => {
    const { fixture, el } = render();
    await settle();
    answerSite({ settings: { ...DEFAULT_SETTINGS, consultation_cta_label: 'Talk to us' } });
    await settle();
    fixture.detectChanges();
    expect(el.querySelector('.mk-header__cta')!.textContent!.trim()).toBe('Talk to us');
  });

  it('hides Resources until there is published content', () => {
    const { el } = render();
    expect(el.querySelector('#menu-button-resources')).toBeNull();
  });
});

describe('Footer', () => {
  it('links every service and business type, and no legal links until they exist', () => {
    setupMarketing();
    const fixture = TestBed.createComponent(Footer);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const hrefs = [...el.querySelectorAll('a')].map((a) => a.getAttribute('href'));
    for (const s of SERVICES) expect(hrefs).toContain(`/services/${s.slug}`);
    for (const a of AUDIENCES) expect(hrefs).toContain(`/who-we-help/${a.slug}`);
    expect(hrefs).toContain(LOGIN_URL);
    expect(hrefs).toContain('/book-a-consultation');
    expect(el.querySelector('.mk-footer__legal')).toBeNull();
    expect(el.textContent).toContain(`© ${new Date().getFullYear()} Outlogik`);
  });

  it('shows contact details and social links only once they are set', async () => {
    setupMarketing();
    const fixture = TestBed.createComponent(Footer);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.mk-footer__social')).toBeNull();
    expect(el.querySelector('a[href^="mailto:"]')).toBeNull();
    await settle();
    answerSite({ settings: { ...DEFAULT_SETTINGS, contact_email: 'hello@outlogik.example.com',
      social_links: [{ network: 'linkedin', url: 'https://www.linkedin.com/company/outlogik' }] } });
    await settle();
    fixture.detectChanges();
    expect(el.querySelector('a[href="mailto:hello@outlogik.example.com"]')).not.toBeNull();
    const social = el.querySelector('.mk-footer__social a')!;
    expect(social.textContent).toBe('LinkedIn');
    expect(social.getAttribute('rel')).toContain('noopener');
  });
});
