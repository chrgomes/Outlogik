import { DialogRef } from '@angular/cdk/dialog';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';

import { me, membership } from '../../../testing/fixtures';
import { ALL, answer, dialogProviders, flushPending, setupOrg } from '../../../testing/org-setup';
import { Report, Workspace } from '../../core/api.types';
import { AuthService } from '../../core/auth.service';
import { DialogService } from '../../shared/dialog/dialog';
import { NewReportDialog } from './new-report-dialog';
import { ReportsList } from './reports-list';

const BASE = '/api/v1/orgs/acme';
const MAKE = [...ALL, 'reports.read', 'reports.create', 'analytics.read', 'audits.read'];
const ws: Workspace = {
  id: 'w-own', kind: 'own', name: 'Corner Bakery', client_id: null, client_status: null, website_count: 1,
  created_at: '2026-11-01T00:00:00Z', linked: false, organization_name: null, access: null,
};

function report(over: Partial<Report> = {}): Report {
  return {
    id: 'r1', workspace_id: 'w-own', workspace_name: 'Corner Bakery', title: 'November report',
    sections: ['traffic', 'search', 'audit'], period_start: '2026-10-27', period_end: '2026-11-23',
    compare: 'previous', compare_start: '2026-09-29', compare_end: '2026-10-26',
    sources: [{ name: 'Google Analytics 4', detail: 'bakery', through: '2026-11-23' }],
    unavailable: ['Google search figures run to November 21, 2026: Search Console reports 2–3 days behind.'],
    csv_files: [{ name: 'daily', label: 'Daily figures' }, { name: 'searches', label: 'Top Google searches' }],
    created_at: '2026-11-24T10:00:00Z', created_by: 'Olive Owner', ...over,
  };
}

const text = (el: HTMLElement) => el.textContent!.replace(/\s+/g, ' ');

describe('Reports list', () => {
  async function render(perms: string[], reports: Report[], extra: unknown[] = [], query: Record<string, string> = {}) {
    const http = setupOrg(perms, 'owner', [
      { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } }, ...extra as never[]]);
    TestBed.inject(AuthService).me.set(me([membership({ permissions: perms, organization_kind: 'business' })]));
    const fixture = TestBed.createComponent(ReportsList);
    fixture.detectChanges();
    await flushPending();
    answer(http, `${BASE}/workspaces`, [ws]);
    await flushPending();
    fixture.detectChanges();
    const req = http.expectOne((r) => r.url === `${BASE}/reports`);
    req.flush(reports);
    await flushPending();
    fixture.detectChanges();
    return { http, fixture, el: fixture.nativeElement as HTMLElement, req };
  }

  it('lists reports with their period, notes and downloads', async () => {
    const { el, req } = await render(MAKE, [report()]);
    expect(req.request.params.get('workspace_id')).toBe('w-own');
    const t = text(el);
    expect(t).toContain('November report');
    expect(t).toContain('Traffic · Google search · Audit');
    expect(t).toContain('1 note about missing data');
    expect(t).toContain('Search Console reports 2–3 days behind');
    expect(t).toContain('Olive Owner');
    const links = [...el.querySelectorAll('a[download]')].map((a) => a.getAttribute('href'));
    expect(links).toEqual([`${BASE}/reports/r1/pdf`, `${BASE}/reports/r1/csv/daily`, `${BASE}/reports/r1/csv/searches`]);
  });

  it('read-only roles can download but not make or delete', async () => {
    const { el } = await render([...ALL, 'reports.read'], [report()]);
    expect(text(el)).not.toContain('New report');
    expect(text(el)).not.toContain('Delete');
    expect(el.querySelector('a[download]')).not.toBeNull();
  });

  it('explains an empty list', async () => {
    const { el } = await render(MAKE, []);
    expect(text(el)).toContain('No reports yet');
  });

  it('deletes after confirming', async () => {
    const dialog = { provide: DialogService, useValue: { confirm: async () => true, open: async () => undefined } };
    const { el, http } = await render(MAKE, [report()], [dialog]);
    [...el.querySelectorAll('button')].find((b) => b.textContent!.includes('Delete'))!.click();
    await flushPending();
    expect(http.expectOne((r) => r.method === 'DELETE').request.url).toBe(`${BASE}/reports/r1`);
  });

  it('opens a new report for the client chosen on the agency dashboard', async () => {
    const open = vi.fn(async () => undefined);
    await render(MAKE, [], [{ provide: DialogService, useValue: { open, confirm: async () => true } }], { new: 'w9' });
    await flushPending();
    expect(open).toHaveBeenCalledWith(NewReportDialog, { workspaceId: 'w9' });
  });
});

describe('New report dialog', () => {
  async function render(perms = MAKE) {
    const close = vi.fn();
    const http = setupOrg(perms, 'owner', [...dialogProviders({ workspaceId: 'w-own' }),
      { provide: DialogRef, useValue: { close } }]);
    TestBed.inject(AuthService).me.set(me([membership({ permissions: perms, organization_kind: 'business' })]));
    const fixture = TestBed.createComponent(NewReportDialog);
    fixture.detectChanges();
    await flushPending();
    answer(http, `${BASE}/workspaces`, [ws]);
    await flushPending();
    fixture.detectChanges();
    return { http, fixture, el: fixture.nativeElement as HTMLElement, close };
  }
  const submit = (el: HTMLElement) => el.querySelector('form')!.dispatchEvent(new Event('submit'));

  it('makes a report with the chosen sections and period', async () => {
    const { el, http, fixture, close } = await render();
    expect((el.querySelector('#r-title') as HTMLInputElement).placeholder).toBe('Corner Bakery: marketing report');
    (el.querySelector('#r-ai') as HTMLInputElement).click();
    const compare = el.querySelector('#r-compare') as HTMLSelectElement;
    compare.value = 'year';
    compare.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    submit(el);
    const req = http.expectOne(`${BASE}/workspaces/w-own/reports`);
    expect(req.request.body).toEqual({ title: null, sections: ['traffic', 'search', 'audit'], days: 28,
      start: null, end: null, compare: 'year' });
    req.flush(report());
    await flushPending();
    expect(close).toHaveBeenCalled();
  });

  it('checks a custom range and that something is included', async () => {
    const { el, fixture, http } = await render();
    const period = el.querySelector('#r-period') as HTMLSelectElement;
    period.value = 'custom';
    period.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    const set = (id: string, v: string) => {
      const i = el.querySelector(id) as HTMLInputElement; i.value = v; i.dispatchEvent(new Event('input'));
    };
    set('#r-start', '2026-11-10'); set('#r-end', '2026-11-01');
    submit(el);
    fixture.detectChanges();
    expect(text(el)).toContain('The start date is after the end date.');
    for (const key of ['traffic', 'ai', 'search', 'audit']) (el.querySelector(`#r-${key}`) as HTMLInputElement).click();
    set('#r-end', '2026-11-20');
    submit(el);
    fixture.detectChanges();
    expect(text(el)).toContain('Choose at least one thing to include.');
    http.expectNone(`${BASE}/workspaces/w-own/reports`);
  });

  it('only offers the sections the role can see', async () => {
    const { el } = await render([...ALL, 'reports.read', 'reports.create', 'audits.read']);
    expect((el.querySelector('#r-traffic') as HTMLInputElement).disabled).toBe(true);
    expect((el.querySelector('#r-audit') as HTMLInputElement).checked).toBe(true);
    expect(text(el)).toContain('Not part of your role');
  });
});
