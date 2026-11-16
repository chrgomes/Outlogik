import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { FormArray, FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

import { Icon } from '@brand/icon/icon';
import { apiProblem, applyFieldErrors } from '../../core/api-errors';
import { FieldError, showError } from '../../shared/forms/forms';
import { PageHeader } from '../../shared/page-header/page-header';
import { ErrorState, LoadingState } from '../../shared/states/states';
import { ToastService } from '../../shared/toast/toast';
import { ADMIN_API, AdminApi, PROVINCES, SiteSettings } from './admin-api';

const NETWORKS = [
  { value: 'linkedin', label: 'LinkedIn' }, { value: 'facebook', label: 'Facebook' },
  { value: 'instagram', label: 'Instagram' }, { value: 'x', label: 'X' },
  { value: 'youtube', label: 'YouTube' }, { value: 'tiktok', label: 'TikTok' },
  { value: 'github', label: 'GitHub' },
];

const text = (max: number, required = false) => new FormControl('', {
  nonNullable: true, validators: [Validators.maxLength(max), ...(required ? [Validators.required] : [])],
});

function socialLink(network = 'linkedin', url = '') {
  return new FormGroup({
    network: new FormControl(network, { nonNullable: true }),
    url: new FormControl(url, { nonNullable: true, validators: [Validators.required, Validators.pattern(/^https?:\/\/\S+$/)] }),
  });
}

/**
 * /admin/settings: what the website shows without a release (contact details, social links,
 * the main button's wording, search defaults). Empty fields are simply not shown on the site.
 */
@Component({
  selector: 'ol-site-settings',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, ReactiveFormsModule, Icon, PageHeader, FieldError, ErrorState, LoadingState],
  template: `
    <ol-page-header title="Website settings"
      description="Contact details, social links and wording used across the website. Changes appear within about a minute." />

    @if (settings.error()) {
      <ol-error-state message="We couldn't load the settings." (retry)="settings.reload()" />
    } @else if (settings.hasValue()) {
      <form [formGroup]="form" (ngSubmit)="save()" novalidate class="settings">
        <section class="settings-card">
          <h2 class="h6">About Outlogik</h2>
          <div class="mb-3">
            <label for="s-tagline" class="form-label">Tagline</label>
            <input id="s-tagline" class="form-control" formControlName="tagline" [class.is-invalid]="bad('tagline')" />
            <ol-field-error [control]="form.controls.tagline" />
          </div>
          <div>
            <label for="s-desc" class="form-label">Short description</label>
            <textarea id="s-desc" class="form-control" rows="3" formControlName="company_description"
              [class.is-invalid]="bad('company_description')" aria-describedby="s-desc-hint"></textarea>
            <div id="s-desc-hint" class="form-text">Shown in the footer of every page.</div>
            <ol-field-error [control]="form.controls.company_description" />
          </div>
        </section>

        <section class="settings-card">
          <h2 class="h6">Contact details</h2>
          <p class="text-muted small">Leave a field empty to hide it on the website.</p>
          <div class="row g-3">
            <div class="col-md-6">
              <label for="s-email" class="form-label">Contact email</label>
              <input id="s-email" type="email" class="form-control" formControlName="contact_email" [class.is-invalid]="bad('contact_email')" />
              <ol-field-error [control]="form.controls.contact_email" />
            </div>
            <div class="col-md-6">
              <label for="s-sales" class="form-label">Sales email</label>
              <input id="s-sales" type="email" class="form-control" formControlName="sales_email" [class.is-invalid]="bad('sales_email')"
                aria-describedby="s-sales-hint" />
              <div id="s-sales-hint" class="form-text">Offered on the consultation page.</div>
              <ol-field-error [control]="form.controls.sales_email" />
            </div>
            <div class="col-md-6">
              <label for="s-phone" class="form-label">Phone</label>
              <input id="s-phone" type="tel" class="form-control" formControlName="phone" [class.is-invalid]="bad('phone')" />
              <ol-field-error [control]="form.controls.phone" />
            </div>
            <div class="col-12">
              <label for="s-address" class="form-label">Address</label>
              <textarea id="s-address" class="form-control" rows="2" formControlName="address" [class.is-invalid]="bad('address')"></textarea>
              <ol-field-error [control]="form.controls.address" />
            </div>
          </div>
        </section>

        <section class="settings-card">
          <h2 class="h6">Social links</h2>
          <p class="text-muted small">Shown in the footer.</p>
          <div formArrayName="social_links">
            @for (link of form.controls.social_links.controls; track link; let i = $index) {
              <div class="social-row" [formGroupName]="i">
                <select class="form-select" formControlName="network" [attr.aria-label]="'Network ' + (i + 1)">
                  @for (n of networks; track n.value) { <option [value]="n.value">{{ n.label }}</option> }
                </select>
                <div class="flex-grow-1">
                  <input class="form-control" formControlName="url" placeholder="https://"
                    [attr.aria-label]="'Link ' + (i + 1)" [class.is-invalid]="badLink(i)" />
                  @if (badLink(i)) { <div class="invalid-feedback d-block">Enter a full address starting with https://</div> }
                </div>
                <button type="button" class="icon-action" (click)="removeLink(i)" [attr.aria-label]="'Remove link ' + (i + 1)">
                  <ol-icon name="trash" />
                </button>
              </div>
            }
          </div>
          @if (form.controls.social_links.length < 10) {
            <button type="button" class="btn btn-sm btn-outline-secondary" (click)="addLink()">
              <ol-icon name="plus-lg" /> Add a link
            </button>
          }
        </section>

        <section class="settings-card">
          <h2 class="h6">Wording and search</h2>
          <div class="mb-3">
            <label for="s-cta" class="form-label">Main button</label>
            <input id="s-cta" class="form-control" formControlName="consultation_cta_label" [class.is-invalid]="bad('consultation_cta_label')"
              aria-describedby="s-cta-hint" />
            <div id="s-cta-hint" class="form-text">The call to action in the header and on every page.</div>
            <ol-field-error [control]="form.controls.consultation_cta_label" />
          </div>
          <div class="mb-3">
            <label for="s-suffix" class="form-label">Page title ending</label>
            <input id="s-suffix" class="form-control" formControlName="seo_title_suffix" [class.is-invalid]="bad('seo_title_suffix')" />
            <ol-field-error [control]="form.controls.seo_title_suffix" />
          </div>
          <div>
            <label for="s-seo" class="form-label">Default search description</label>
            <textarea id="s-seo" class="form-control" rows="2" formControlName="seo_default_description"
              [class.is-invalid]="bad('seo_default_description')" aria-describedby="s-seo-hint"></textarea>
            <div id="s-seo-hint" class="form-text">Used by search engines for pages without their own description.</div>
            <ol-field-error [control]="form.controls.seo_default_description" />
          </div>
        </section>

        <section class="settings-card">
          <h2 class="h6">Legal details</h2>
          <p class="text-muted small" id="legal-hint">
            Used in the website's privacy policy and terms and conditions. Those pages are
            published only once all of these <strong>and the address above</strong> are filled
            in; until then they don't appear on the website.
          </p>
          <div class="row g-3">
            <div class="col-12">
              <label for="s-legal-name" class="form-label">Legal business name</label>
              <input id="s-legal-name" class="form-control" formControlName="legal_name" placeholder="For example, Outlogik Inc."
                [class.is-invalid]="bad('legal_name')" />
              <ol-field-error [control]="form.controls.legal_name" />
            </div>
            <div class="col-md-6">
              <label for="s-province" class="form-label">Province or territory</label>
              <select id="s-province" class="form-select" formControlName="province" aria-describedby="s-province-hint">
                <option value="">Not set</option>
                @for (p of provinces; track p) { <option [value]="p">{{ p }}</option> }
              </select>
              <div id="s-province-hint" class="form-text">Whose laws govern the terms.</div>
            </div>
            <div class="col-md-6">
              <label for="s-privacy" class="form-label">Privacy contact email</label>
              <input id="s-privacy" type="email" class="form-control" formControlName="privacy_email"
                [class.is-invalid]="bad('privacy_email')" aria-describedby="s-privacy-hint" />
              <div id="s-privacy-hint" class="form-text">For requests about personal information.</div>
              <ol-field-error [control]="form.controls.privacy_email" />
            </div>
          </div>
          <p class="small mt-3 mb-0" [class.text-success]="legalComplete()" [class.text-muted]="!legalComplete()">
            {{ legalComplete() ? 'Complete: the privacy policy and terms are published.' : 'Not complete: the privacy policy and terms are not published yet.' }}
          </p>
        </section>

        <section class="settings-card">
          <h2 class="h6">Analytics</h2>
          <p class="text-muted small">
            Optional. A tool loads only for visitors who accept analytics cookies in the website's
            banner, which appears only while at least one tool is set. Leave all empty to use none:
            the website then sets no tracking cookies.
          </p>
          <div class="row g-3">
            <div class="col-md-6">
              <label for="s-ga4" class="form-label">Google Analytics 4 measurement ID</label>
              <input id="s-ga4" class="form-control" formControlName="ga4_measurement_id" placeholder="G-XXXXXXXXXX"
                [class.is-invalid]="bad('ga4_measurement_id')" autocomplete="off" />
              <ol-field-error [control]="form.controls.ga4_measurement_id" />
            </div>
            <div class="col-md-6">
              <label for="s-gtm" class="form-label">Google Tag Manager container ID</label>
              <input id="s-gtm" class="form-control" formControlName="gtm_container_id" placeholder="GTM-XXXXXX"
                [class.is-invalid]="bad('gtm_container_id')" autocomplete="off" />
              <ol-field-error [control]="form.controls.gtm_container_id" />
            </div>
            <div class="col-md-6">
              <label for="s-clarity" class="form-label">Microsoft Clarity project ID</label>
              <input id="s-clarity" class="form-control" formControlName="clarity_project_id"
                [class.is-invalid]="bad('clarity_project_id')" autocomplete="off" />
              <ol-field-error [control]="form.controls.clarity_project_id" />
            </div>
          </div>
        </section>

        <div class="save-bar">
          <span class="text-muted small">Last saved {{ settings.value().updated_at | date: 'MMM d, y, h:mm a' }}</span>
          <button type="submit" class="btn btn-primary" [disabled]="busy() || form.pristine">Save changes</button>
        </div>
      </form>
    } @else {
      <ol-loading-state label="Loading settings…" />
    }
  `,
  styles: `
    .settings { display: grid; gap: 1.25rem; max-width: 44rem; }
    .settings-card { padding: 1.5rem; border: 1px solid var(--ol-border);
      border-radius: var(--bs-border-radius-lg); background: var(--ol-surface-raised); }
    .social-row { display: flex; gap: 0.5rem; align-items: flex-start; margin-bottom: 0.75rem; }
    .social-row select { width: 9.5rem; flex: none; }
    .save-bar { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
  `,
})
export class SiteSettingsPage {
  private readonly api = inject(AdminApi);
  private readonly toast = inject(ToastService);
  protected readonly networks = NETWORKS;
  protected readonly provinces = PROVINCES;
  /** Matches the website's rule for publishing the legal pages (based on what's saved). */
  protected readonly legalComplete = computed(() => {
    const d = this.settings.hasValue() ? this.settings.value().data : null;
    return !!(d?.legal_name && d.province && d.privacy_email && d.address);
  });
  protected readonly busy = signal(false);
  protected readonly settings = httpResource<{ data: SiteSettings; updated_at: string }>(
    () => `${ADMIN_API}/site/settings`);

  protected readonly form = new FormGroup({
    tagline: text(300, true),
    company_description: text(300, true),
    contact_email: new FormControl('', { nonNullable: true, validators: [Validators.email] }),
    sales_email: new FormControl('', { nonNullable: true, validators: [Validators.email] }),
    phone: text(40),
    address: text(300),
    social_links: new FormArray<ReturnType<typeof socialLink>>([]),
    consultation_cta_label: text(40, true),
    seo_title_suffix: text(60),
    seo_default_description: text(200),
    legal_name: text(160),
    province: new FormControl('', { nonNullable: true }),
    privacy_email: new FormControl('', { nonNullable: true, validators: [Validators.email] }),
    ga4_measurement_id: new FormControl('', { nonNullable: true, validators: [Validators.pattern(/^G-[A-Z0-9]{4,16}$/)] }),
    gtm_container_id: new FormControl('', { nonNullable: true, validators: [Validators.pattern(/^GTM-[A-Z0-9]{4,12}$/)] }),
    clarity_project_id: new FormControl('', { nonNullable: true, validators: [Validators.pattern(/^[a-z0-9]{6,16}$/)] }),
  });

  constructor() {
    effect(() => {
      if (this.settings.hasValue() && this.form.pristine) this.load(this.settings.value().data);
    });
  }

  private load(d: SiteSettings): void {
    const links = this.form.controls.social_links;
    links.clear();
    for (const l of d.social_links) links.push(socialLink(l.network, l.url));
    this.form.reset({
      ...d, contact_email: d.contact_email ?? '', sales_email: d.sales_email ?? '',
      phone: d.phone ?? '', address: d.address ?? '',
      legal_name: d.legal_name ?? '', province: d.province ?? '', privacy_email: d.privacy_email ?? '',
      ga4_measurement_id: d.ga4_measurement_id ?? '', gtm_container_id: d.gtm_container_id ?? '',
      clarity_project_id: d.clarity_project_id ?? '',
      social_links: d.social_links,
    });
  }

  protected bad(name: keyof typeof this.form.controls): boolean {
    return showError(this.form.controls[name]);
  }

  protected badLink(i: number): boolean {
    return showError(this.form.controls.social_links.at(i).controls.url);
  }

  protected addLink(): void {
    this.form.controls.social_links.push(socialLink());
    this.form.markAsDirty();
  }

  protected removeLink(i: number): void {
    this.form.controls.social_links.removeAt(i);
    this.form.markAsDirty();
  }

  protected async save(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    const orNull = (s: string) => s.trim() || null;
    this.busy.set(true);
    try {
      const saved = await this.api.saveSettings({
        ...v, contact_email: orNull(v.contact_email), sales_email: orNull(v.sales_email),
        phone: orNull(v.phone), address: orNull(v.address),
        legal_name: orNull(v.legal_name), province: orNull(v.province), privacy_email: orNull(v.privacy_email),
        ga4_measurement_id: orNull(v.ga4_measurement_id), gtm_container_id: orNull(v.gtm_container_id),
        clarity_project_id: orNull(v.clarity_project_id),
      });
      this.settings.set(saved);
      this.load(saved.data);
      this.toast.success('Website settings saved.');
    } catch (e) {
      const problem = apiProblem(e);
      if (!applyFieldErrors(this.form, problem.fields)) this.toast.error(problem.message);
    } finally {
      this.busy.set(false);
    }
  }
}
