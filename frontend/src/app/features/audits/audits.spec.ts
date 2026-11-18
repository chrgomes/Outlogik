import { ComponentRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { ALL, answer, flushPending, setupOrg } from '../../../testing/org-setup';
import { Audit, AuditDetail, IssueGroup, WebsiteAudits } from '../../core/api.types';
import { AuditDetailPage } from './audit-detail';
import { describeDetails } from './audit-parts';
import { AuditsList } from './audits-list';

const PERMS = [...ALL, 'audits.read', 'audits.run'];

function audit(over: Partial<Audit> = {}): Audit {
  return {
    id: 'a1', workspace_id: 'w1', website_id: 's1', website_name: 'Corner Bakery',
    url: 'https://cornerbakery.example.com', status: 'completed', trigger: 'manual',
    page_limit: 500, pages_crawled: 42, hit_page_limit: false, errors: 2, warnings: 5, notices: 9,
    error: null, created_at: '2026-11-18T10:00:00Z', started_at: '2026-11-18T10:00:01Z',
    finished_at: '2026-11-18T10:03:00Z', ...over,
  };
}

function row(over: Partial<WebsiteAudits> = {}): WebsiteAudits {
  return {
    website_id: 's1', website_name: 'Corner Bakery', url: 'https://cornerbakery.example.com',
    workspace_id: 'w1', workspace_name: 'Acme', audit_frequency: 'off', latest: audit(), ...over,
  };
}

describe('Audits list', () => {
  async function render(perms: string[], rows: WebsiteAudits[]) {
    const http = setupOrg(perms);
    const fixture = TestBed.createComponent(AuditsList);
    fixture.detectChanges();
    await flushPending();
    answer(http, '/api/v1/orgs/acme/audits/websites', rows);
    await flushPending();
    fixture.detectChanges();
    return { http, fixture, el: fixture.nativeElement as HTMLElement };
  }

  it('lists websites with their latest audit and issue counts', async () => {
    const { el } = await render(PERMS, [row(), row({ website_id: 's2', website_name: 'Shop', latest: null })]);
    const rows = [...el.querySelectorAll('tbody tr')];
    expect(rows[0].textContent).toContain('42 pages');
    expect(rows[0].querySelector('a')!.getAttribute('href')).toBe('/o/acme/audits/w1/a1');
    expect(rows[0].querySelector('[aria-label="2 errors"]')).not.toBeNull();
    expect(rows[1].textContent).toContain('Never');
  });

  it('runs an audit and sets a schedule', async () => {
    const { el, http, fixture } = await render(PERMS, [row()]);
    (el.querySelector('tbody .btn') as HTMLButtonElement).click();
    const start = http.expectOne('/api/v1/orgs/acme/workspaces/w1/audits');
    expect(start.request.body).toEqual({ website_id: 's1' });
    start.flush(audit({ status: 'queued' }));
    await flushPending();
    const select = el.querySelector('select') as HTMLSelectElement;
    select.value = 'weekly';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    const patch = http.expectOne((r) => r.method === 'PATCH');
    expect(patch.request.url).toBe('/api/v1/orgs/acme/websites/s1');
    expect(patch.request.body).toEqual({ audit_frequency: 'weekly' });
  });

  it('shows a running audit and offers no second run', async () => {
    const { el } = await render(PERMS, [row({ latest: audit({ status: 'running' }) })]);
    expect(el.textContent).toContain('Running…');
    expect((el.querySelector('tbody .btn') as HTMLButtonElement).disabled).toBe(true);
  });

  it('is read-only for roles that can only view audits', async () => {
    const { el } = await render(ALL.concat('audits.read'), [row({ audit_frequency: 'monthly' })]);
    expect(el.querySelector('select')).toBeNull();
    expect(el.querySelector('tbody .btn')).toBeNull();
    expect(el.textContent).toContain('Monthly');
  });
});

describe('Audit detail', () => {
  const detail: AuditDetail = {
    ...audit(), previous_audit_id: 'a0', new_issues: 3, fixed_issues: 4,
    facts: { https: true, sitemap: false, robots_txt: 200, structured_data_types: ['WebSite'],
      ai_search_crawlers: { Googlebot: true, PerplexityBot: false },
      ai_training_crawlers: { GPTBot: false }, pagespeed: { connected: false } },
  };
  const groups: IssueGroup[] = [
    { check: 'page_broken', title: 'Broken page (4xx)', severity: 'error', area: 'technical',
      why: 'Visitors reach an error page.', fix: 'Fix or remove the links.', count: 1, new: 1,
      items: [{ url: 'https://cornerbakery.example.com/old', is_new: true,
        details: { status: 404, linked_from: 'https://cornerbakery.example.com/' } }] },
    { check: 'ai_search_crawlers_blocked', title: 'AI search crawlers are blocked', severity: 'warning',
      area: 'ai_search', why: 'Why.', fix: 'Fix.', count: 1, new: 0,
      items: [{ url: null, is_new: false, details: { blocked: ['PerplexityBot (Perplexity)'] } }] },
  ];

  async function render() {
    const http = setupOrg(PERMS);
    const fixture = TestBed.createComponent(AuditDetailPage);
    const ref = fixture.componentRef as ComponentRef<AuditDetailPage>;
    ref.setInput('workspaceId', 'w1');
    ref.setInput('auditId', 'a1');
    fixture.detectChanges();
    await flushPending();
    answer(http, '/api/v1/orgs/acme/workspaces/w1/audits/a1', detail);
    await flushPending();
    fixture.detectChanges();
    await flushPending();
    answer(http, '/api/v1/orgs/acme/workspaces/w1/audits/a1/issues', groups);
    answer(http, '/api/v1/orgs/acme/workspaces/w1/audits/a1/fixed', [
      { check: 'title_missing', title: 'Missing page title', url: 'https://cornerbakery.example.com/x' }]);
    answer(http, '/api/v1/orgs/acme/workspaces/w1/audits/a1/pages', []);
    await flushPending();
    fixture.detectChanges();
    return { fixture, el: fixture.nativeElement as HTMLElement };
  }

  it('summarizes the audit and what changed', async () => {
    const { el } = await render();
    const text = el.textContent!.replace(/\s+/g, ' ');
    expect(text).toContain('42 pages checked');
    expect(text).toContain('3 new · 4 fixed since the last audit');
    expect(text).toContain('Fixed since the last audit');
    expect(text).toContain('Missing page title');
  });

  it('shows AI search readiness facts, and page speed as not connected', async () => {
    const { el } = await render();
    const text = el.textContent!.replace(/\s+/g, ' ');
    expect(text).toContain('PerplexityBot Blocked');
    expect(text).toContain('Googlebot Allowed');
    expect(text).toContain('Blocking these is your choice');
    expect(text).toContain('Not connected yet');
  });

  it('lists issues with how to fix them, and filters by area', async () => {
    const { el, fixture } = await render();
    expect(el.querySelectorAll('details.issue').length).toBe(2);
    const first = el.querySelector('details.issue')!;
    expect(first.textContent).toContain('Fix or remove the links.');
    expect(first.textContent).toContain('Linked from: https://cornerbakery.example.com/');
    expect(first.textContent).toContain('New');
    const ai = [...el.querySelectorAll('[role="group"] button')].find((b) => b.textContent!.includes('AI search')) as HTMLButtonElement;
    ai.click();
    fixture.detectChanges();
    expect([...el.querySelectorAll('details.issue')].map((d) => d.querySelector('summary')!.textContent!.trim()))
      .toEqual([expect.stringContaining('AI search crawlers are blocked')]);
  });
});

describe('describeDetails', () => {
  it('reads details as plain text', () => {
    expect(describeDetails({ status: 404, linked_from: '/a' })).toBe('Status: 404 — Linked from: /a');
    expect(describeDetails({ telephone: { '4165550100': ['/a', '/b'], '4165550199': ['/c'] } }))
      .toBe('Phone numbers: "4165550100" (2 pages) · "4165550199" (1 page)');
  });
});
