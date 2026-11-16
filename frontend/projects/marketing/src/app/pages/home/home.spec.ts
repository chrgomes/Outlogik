import { TestBed } from '@angular/core/testing';

import { DEFAULT_PORTAL_FEATURES, SERVICES, TOOLS } from '../../config/site';
import { answerSite, settle, setupMarketing } from '../../../testing/marketing';
import { Home } from './home';

describe('Homepage', () => {
  async function render(features?: object[]) {
    setupMarketing();
    const fixture = TestBed.createComponent(Home);
    fixture.detectChanges();
    if (features) {
      await settle();
      answerSite({ portal_features: features });
      await settle();
      fixture.detectChanges();
    }
    return fixture.nativeElement as HTMLElement;
  }

  it('leads with one h1 and the consultation call to action', async () => {
    const el = await render();
    expect(el.querySelectorAll('h1')).toHaveLength(1);
    const ctas = [...el.querySelectorAll('a[href="/book-a-consultation"]')];
    expect(ctas.length).toBeGreaterThanOrEqual(3);
    expect(el.innerHTML).not.toContain('/register');
  });

  it('shows the four services', async () => {
    const el = await render();
    const hrefs = [...el.querySelectorAll('.mk-card')].map((a) => a.getAttribute('href'));
    for (const s of SERVICES) expect(hrefs).toContain(`/services/${s.slug}`);
  });

  it('labels client-portal features honestly, from the admin area', async () => {
    const el = await render([
      { slug: 'client-portal', name: 'Your own client portal', summary: 'x', status: 'available' },
      { slug: 'monthly-reports', name: 'Monthly reports', summary: 'y', status: 'in_development' },
    ]);
    const items = [...el.querySelectorAll('.mk-features li')];
    expect(items.map((li) => li.querySelector('strong')!.textContent)).toEqual(
      ['Your own client portal', 'Monthly reports']);
    expect(items.map((li) => !!li.querySelector('.mk-badge'))).toEqual([false, true]);
    expect(items[1].classList).toContain('is-soon');
  });

  it('falls back to the default feature list if the API is unavailable', async () => {
    const el = await render();
    expect(el.querySelectorAll('.mk-features li')).toHaveLength(DEFAULT_PORTAL_FEATURES.length);
  });

  it('shows the tools, and no results or testimonials until real ones exist', async () => {
    const el = await render();
    expect([...el.querySelectorAll('.mk-tile')].map((t) => t.textContent!.trim())).toEqual(TOOLS);
    expect(el.textContent!.toLowerCase()).not.toMatch(/testimonial|case stud|% increase|trusted by/);
  });

  it('uses real screenshots with alt text and fixed dimensions', async () => {
    const el = await render();
    const imgs = [...el.querySelectorAll('img')];
    expect(imgs.length).toBe(2);
    for (const img of imgs) {
      expect(img.getAttribute('alt')!.length).toBeGreaterThan(10);
      expect(img.getAttribute('width')).toBe('1440');
      // Phones get the 720 px image, large screens the 1440 or 2880 px one.
      expect(img.getAttribute('srcset')).toMatch(/-720\.webp 720w, .*\.webp 1440w, .*@2x\.webp 2880w/);
      expect(img.getAttribute('sizes')).toBeTruthy();
    }
    expect(imgs[0].getAttribute('loading')).toBe('eager');
    expect(imgs[1].getAttribute('loading')).toBe('lazy');
  });
});
