import { TestBed } from '@angular/core/testing';

import { DEFAULT_SETTINGS } from '../config/site';
import { answerSite, settle, setupMarketing } from '../../testing/marketing';
import { addNonce, contentSecurityPolicy } from '../../csp';
import { CookieBanner } from './cookie-banner';
import { Consent } from './consent';

const clearCookies = () => {
  for (const c of document.cookie.split('; ')) {
    if (c) document.cookie = `${c.split('=')[0]}=; Max-Age=0; Path=/`;
  }
};
const scripts = () => [...document.head.querySelectorAll('script[src]')].map((s) => s.getAttribute('src'));

async function setup(over: object = {}) {
  setupMarketing();
  const consent = TestBed.inject(Consent);
  consent.needed(); // reading the settings sends the site-data request
  TestBed.tick();
  await settle();
  answerSite({ settings: { ...DEFAULT_SETTINGS, ...over } });
  await settle();
  const fixture = TestBed.createComponent(CookieBanner);
  consent.start();
  fixture.detectChanges();
  TestBed.tick();
  return { consent, fixture, el: fixture.nativeElement as HTMLElement };
}

describe('Analytics consent', () => {
  beforeEach(() => {
    clearCookies();
    document.head.querySelectorAll('script[src]').forEach((s) => s.remove());
    delete (window as { dataLayer?: unknown }).dataLayer;
  });

  it('shows no banner and loads nothing when no analytics tool is switched on', async () => {
    const { el, consent } = await setup();
    expect(consent.needed()).toBe(false);
    expect(el.querySelector('.mk-cookies')).toBeNull();
    expect(scripts()).toEqual([]);
  });

  it('asks first, naming the tools, with Accept and Reject looking the same', async () => {
    const { el } = await setup({ ga4_measurement_id: 'G-TEST1234', clarity_project_id: 'abc123def' });
    const banner = el.querySelector('.mk-cookies')!;
    expect(banner.textContent).toContain('Google Analytics and Microsoft Clarity');
    const buttons = [...banner.querySelectorAll('button')];
    expect(buttons.map((b) => b.textContent!.trim())).toEqual(['Accept analytics', 'Reject analytics']);
    expect(buttons[0].className).toBe(buttons[1].className);
    expect(scripts()).toEqual([]);
    expect(document.cookie).toBe('');
  });

  it('loads the tools only after Accept, remembers the choice and reports conversions', async () => {
    const { el, fixture, consent } = await setup({ ga4_measurement_id: 'G-TEST1234' });
    el.querySelector<HTMLButtonElement>('button')!.click();
    fixture.detectChanges();
    TestBed.tick();
    expect(document.cookie).toContain('ol_consent=granted');
    expect(scripts()).toEqual(['https://www.googletagmanager.com/gtag/js?id=G-TEST1234']);
    expect(el.querySelector('.mk-cookies')).toBeNull();
    consent.track('generate_lead', { form: 'contact' });
    const events = ((window as { dataLayer?: IArguments[] }).dataLayer ?? []).map((a) => [...a].slice(0, 2));
    expect(events).toContainEqual(['event', 'generate_lead']);
  });

  it('does nothing after Reject, and reports no conversions', async () => {
    const { el, fixture, consent } = await setup({ ga4_measurement_id: 'G-TEST1234' });
    el.querySelectorAll<HTMLButtonElement>('button')[1].click();
    fixture.detectChanges();
    TestBed.tick();
    expect(document.cookie).toContain('ol_consent=denied');
    consent.track('generate_lead');
    expect(scripts()).toEqual([]);
    expect((window as { dataLayer?: unknown[] }).dataLayer).toBeUndefined();
  });

  it('remembers an earlier choice', async () => {
    document.cookie = 'ol_consent=denied; Path=/';
    const { el } = await setup({ ga4_measurement_id: 'G-TEST1234' });
    expect(el.querySelector('.mk-cookies')).toBeNull();
  });
});

describe('Content-Security-Policy', () => {
  it('allows only scripts with the response nonce (and what they load)', () => {
    const csp = contentSecurityPolicy('abc');
    expect(csp).toContain("script-src 'nonce-abc' 'strict-dynamic'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).not.toMatch(/script-src[^;]*'unsafe-inline'/);
  });

  it('adds the nonce to every script and module preload', () => {
    const html = '<script>x</script><script src="a.js" type="module"></script>' +
      '<script nonce="keep"></script><link rel="modulepreload" href="c.js">';
    expect(addNonce(html, 'n1')).toBe('<script nonce="n1">x</script><script nonce="n1" src="a.js" type="module"></script>' +
      '<script nonce="keep"></script><link rel="modulepreload" nonce="n1" href="c.js">');
  });
});
