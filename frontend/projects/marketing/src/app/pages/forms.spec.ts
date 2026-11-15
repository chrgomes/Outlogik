import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Meta } from '@angular/platform-browser';

import { Newsletter } from '../layout/footer/newsletter';
import { NEWSLETTER_CONSENT_TEXT, SERVICE_OPTIONS } from '../config/forms';
import { VisitAttribution } from '../shared/attribution';
import { settle, setupMarketing, visit } from '../../testing/marketing';

function type(el: HTMLElement, selector: string, value: string) {
  const input = el.querySelector<HTMLInputElement | HTMLTextAreaElement>(selector)!;
  input.value = value;
  input.dispatchEvent(new Event('input'));
}

function tick(el: HTMLElement, selector: string) {
  const box = el.querySelector<HTMLInputElement>(selector)!;
  box.click();
}

async function submit(el: HTMLElement) {
  el.querySelector<HTMLButtonElement>('button[type="submit"]')!.click();
  await settle();
}

const http = () => TestBed.inject(HttpTestingController);

describe('Book a consultation', () => {
  beforeEach(() => sessionStorage.clear());

  it('asks for the required fields before sending anything', async () => {
    const el = await visit('/book-a-consultation');
    await submit(el);
    TestBed.inject(VisitAttribution);
    http().expectNone('/api/public/leads/consultation');
    expect(el.querySelector('[role="alert"]')!.textContent).toContain('highlighted fields');
    expect(el.querySelector('#c-name')!.getAttribute('aria-invalid')).toBe('true');
    expect(el.querySelector('#c-services-err')).not.toBeNull();
  });

  it('preselects the service a page linked from', async () => {
    const el = await visit('/book-a-consultation?service=seo');
    const boxes = [...el.querySelectorAll<HTMLInputElement>('fieldset input[type="checkbox"]')];
    expect(boxes.map((b) => b.checked)).toEqual(SERVICE_OPTIONS.map((o) => o.value === 'seo'));
  });

  it('sends the request with spam checks and attribution, then confirms', async () => {
    sessionStorage.setItem('ol-visit', JSON.stringify({ landing_page: '/?utm_source=x', utm_source: 'x' }));
    const el = await visit('/book-a-consultation?service=content-marketing');
    type(el, '#c-name', 'Casey');
    type(el, '#c-email', 'casey@example.com');
    type(el, '#c-company', 'Harbour Bakery');
    el.querySelector<HTMLSelectElement>('#c-budget')!.value = '1k-2.5k';
    el.querySelector('#c-budget')!.dispatchEvent(new Event('change'));
    tick(el, 'fieldset label:nth-of-type(1) input');
    await submit(el);

    const req = http().expectOne('/api/public/leads/consultation');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toMatchObject({
      name: 'Casey', email: 'casey@example.com', company: 'Harbour Bakery', budget: '1k-2.5k',
      services: ['seo', 'content-marketing'], nickname: '',
      attribution: { utm_source: 'x', landing_page: '/?utm_source=x', page: '/' },
    });
    expect(typeof req.request.body.elapsed_ms).toBe('number');
    req.flush({ received: true }, { status: 201, statusText: 'Created' });
    await settle();
    TestBed.tick();
    expect(el.textContent).toContain('We’ve received your request');
    expect(el.textContent).toContain('casey@example.com');
    expect(el.querySelector('form')).toBeNull();
  });

  it('explains rate limits and keeps what was typed', async () => {
    const el = await visit('/book-a-consultation?service=seo');
    type(el, '#c-name', 'Casey');
    type(el, '#c-email', 'casey@example.com');
    await submit(el);
    http().expectOne('/api/public/leads/consultation').flush(
      { error: { code: 'rate_limited', message: 'x', details: null } }, { status: 429, statusText: 'Too Many' });
    await settle();
    TestBed.tick();
    expect(el.querySelector('[role="alert"]')!.textContent).toContain('wait a few minutes');
    expect(el.querySelector<HTMLInputElement>('#c-name')!.value).toBe('Casey');
  });

  it('has a hidden spam trap people cannot reach', async () => {
    const el = await visit('/book-a-consultation');
    const trap = el.querySelector('mk-honeypot')!;
    expect(trap.getAttribute('aria-hidden')).toBe('true');
    expect(trap.querySelector('input')!.getAttribute('tabindex')).toBe('-1');
  });
});

describe('Contact', () => {
  it('requires a message and sends the topic', async () => {
    const el = await visit('/contact');
    type(el, '#m-name', 'Pat');
    type(el, '#m-email', 'pat@example.com');
    await submit(el);
    http().expectNone('/api/public/leads/contact');
    expect(el.querySelector('#m-message-err')).not.toBeNull();

    type(el, '#m-message', 'Hello');
    el.querySelector<HTMLSelectElement>('#m-topic')!.value = 'press';
    el.querySelector('#m-topic')!.dispatchEvent(new Event('change'));
    await submit(el);
    const req = http().expectOne('/api/public/leads/contact');
    expect(req.request.body).toMatchObject({ name: 'Pat', topic: 'press', message: 'Hello' });
    req.flush({ received: true });
    await settle();
    TestBed.tick();
    expect(el.textContent).toContain('We’ve received your message');
  });
});

describe('Newsletter sign-up', () => {
  async function render() {
    setupMarketing();
    const fixture = TestBed.createComponent(Newsletter);
    fixture.detectChanges();
    return { el: fixture.nativeElement as HTMLElement, fixture };
  }

  it('shows the consent wording, unticked, and requires it', async () => {
    const { el, fixture } = await render();
    expect(el.textContent).toContain(NEWSLETTER_CONSENT_TEXT);
    expect(el.querySelector<HTMLInputElement>('input[type="checkbox"]')!.checked).toBe(false);
    type(el, '#nl-email', 'reader@example.com');
    el.querySelector<HTMLButtonElement>('button')!.click();
    fixture.detectChanges();
    http().expectNone('/api/public/newsletter');
    expect(el.textContent).toContain('tick the box');
  });

  it('subscribes and asks the reader to confirm by email', async () => {
    const { el, fixture } = await render();
    type(el, '#nl-email', 'reader@example.com');
    tick(el, 'input[type="checkbox"]');
    el.querySelector<HTMLButtonElement>('button')!.click();
    const req = http().expectOne('/api/public/newsletter');
    expect(req.request.body).toMatchObject({ email: 'reader@example.com', consent: true, nickname: '' });
    req.flush({ received: true }, { status: 202, statusText: 'Accepted' });
    await settle();
    fixture.detectChanges();
    expect(el.textContent).toContain('Check your inbox');
  });
});

describe('Newsletter links', () => {
  it('confirms only when the button is clicked, and is hidden from search engines', async () => {
    const el = await visit('/newsletter/confirm?token=abcdefghijklmnop');
    http().expectNone('/api/public/newsletter/confirm');
    expect(TestBed.inject(Meta).getTag('name="robots"')!.content).toBe('noindex');
    el.querySelector<HTMLButtonElement>('button')!.click();
    const req = http().expectOne('/api/public/newsletter/confirm');
    expect(req.request.body).toEqual({ token: 'abcdefghijklmnop' });
    req.flush({ received: true });
    await settle();
    TestBed.tick();
    expect(el.querySelector('h1')!.textContent).toContain('You’re subscribed');
  });

  it('shows the API’s message for an expired link', async () => {
    const el = await visit('/newsletter/unsubscribe?token=abcdefghijklmnop');
    el.querySelector<HTMLButtonElement>('button')!.click();
    http().expectOne('/api/public/newsletter/unsubscribe').flush(
      { error: { code: 'invalid_link', message: 'This unsubscribe link is invalid.', details: null } },
      { status: 400, statusText: 'Bad Request' });
    await settle();
    TestBed.tick();
    expect(el.querySelector('[role="alert"]')!.textContent).toContain('link is invalid');
  });

  it('explains an incomplete link', async () => {
    const el = await visit('/newsletter/confirm');
    expect(el.textContent).toContain('link is incomplete');
    expect(el.querySelector('button')).toBeNull();
  });
});

describe('Visit attribution', () => {
  beforeEach(() => sessionStorage.clear());

  it('keeps the first page of the visit and its UTM tags, without cookies', () => {
    setupMarketing();
    history.replaceState(null, '', '/pricing?utm_source=linkedin&utm_campaign=spring&other=1');
    const a = TestBed.inject(VisitAttribution);
    a.record();
    history.replaceState(null, '', '/contact');
    a.record(); // later pages don't overwrite the first one
    expect(a.forForm()).toEqual({
      landing_page: '/pricing?utm_source=linkedin&utm_campaign=spring&other=1',
      utm_source: 'linkedin', utm_campaign: 'spring', page: '/contact',
    });
    expect(document.cookie).toBe('');
    history.replaceState(null, '', '/');
  });
});
