import { TestBed } from '@angular/core/testing';

import { routes } from '../../app.routes';
import { DEFAULT_SETTINGS } from '../../config/site';
import { sitemapPaths } from '../../seo/sitemap';
import { answerSite, settle, visit } from '../../../testing/marketing';

// The business's own details (the defaults since 2026-11-16).
const LEGAL = {};

async function open(url: string, over: object = {}) {
  const el = await visit(url);
  answerSite({ settings: { ...DEFAULT_SETTINGS, ...over } });
  await settle();
  TestBed.tick();
  return el;
}

const robots = () => document.head.querySelector('meta[name="robots"]')?.getAttribute('content') ?? null;

describe('Legal pages', () => {
  it.each(['/privacy-policy', '/terms', '/payment-policy'])('%s is not published until the legal details are set', async (url) => {
    const el = await open(url, { privacy_email: null, address: null }); // details removed in the admin area
    expect(el.querySelector('h1')!.textContent).toContain('couldn’t find');
    expect(robots()).toBe('noindex');
    expect(document.head.querySelector('link[rel="canonical"]')).toBeNull();
  });

  it('publishes the privacy policy with the business details', async () => {
    const el = await open('/privacy-policy', LEGAL);
    expect(el.querySelector('h1')!.textContent).toContain('Privacy policy');
    const text = el.textContent!;
    expect(text).toContain('Outlogik (“we”) collects');
    expect(text).toContain('Toronto, Ontario, Canada');
    expect(text).toContain('hosted in Toronto, Canada');
    expect(text).toContain('outside Ontario and outside Canada');
    expect(text).toContain('DigitalOcean');
    expect(text).toContain('Office of the Privacy Commissioner of Canada');
    expect(text).not.toContain('Commission d');
    expect(text).toContain('We don’t use them at present'); // no analytics switched on
    expect(el.querySelector('a[href="mailto:privacy@outlogik.com"]')).not.toBeNull();
    expect(robots()).toBeNull();
  });

  it('names the analytics tools in use, and the provincial regulator where there is one', async () => {
    const el = await open('/privacy-policy', { ...LEGAL, province: 'Quebec', ga4_measurement_id: 'G-TEST1234' });
    const text = el.textContent!;
    expect(text).toContain('We use Google Analytics to understand');
    expect(text).toContain("Commission d'accès à l'information du Québec");
  });

  it('publishes the terms with the governing law', async () => {
    const el = await open('/terms', LEGAL);
    expect(el.querySelector('h1')!.textContent).toContain('Terms and conditions');
    expect(el.textContent).toContain('governed by the laws of Ontario');
    expect(el.textContent).toContain('We don’t guarantee particular rankings');
  });

  it('publishes the payment and subscription policy with the agreed terms', async () => {
    const el = await open('/payment-policy', LEGAL);
    expect(el.querySelector('h1')!.textContent).toContain('Payment and subscription policy');
    const text = el.textContent!.replace(/\s+/g, ' ');
    expect(text).toContain('invoiced monthly, at the end of each month, for the work done');
    expect(text).toContain('Invoices are due 15 days after the invoice date');
    expect(text).toContain('more than 30 days overdue, we may pause work');
    expect(text).toContain('We don’t charge interest');
    expect(text).toContain('30 days’ written notice');
    expect(text).toContain('Fees for work already done aren’t refundable');
    expect(el.querySelector('a[href="/terms"]')).not.toBeNull();
    // Billing questions go to the billing alias.
    expect(el.querySelector('a[href="mailto:billings@outlogik.com"]')).not.toBeNull();
  });

  it('are left out of the sitemap until published', () => {
    expect(sitemapPaths(routes)).not.toContain('/privacy-policy');
    expect(sitemapPaths(routes, { legalPublished: true })).toEqual(
      expect.arrayContaining(['/privacy-policy', '/terms', '/payment-policy']));
  });

  it('are linked from the forms once published', async () => {
    const el = await open('/contact', LEGAL);
    expect(el.querySelector('a[href="/privacy-policy"]')).not.toBeNull(); // the form's privacy note
  });
});
