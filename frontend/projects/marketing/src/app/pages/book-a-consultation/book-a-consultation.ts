import {
  ChangeDetectionStrategy, Component, ElementRef, afterNextRender, inject, signal, viewChild,
} from '@angular/core';
import { FormArray, FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { BUDGET_OPTIONS, SERVICE_OPTIONS } from '../../config/forms';
import { SiteData } from '../../config/site-data';
import { FormError, Honeypot } from '../../shared/form-status';
import { LeadApi } from '../../shared/lead-api';
import { pageDescription } from '../../seo/seo';
import { PageHero } from '../../shared/page-hero';

/**
 * /book-a-consultation: the site's main conversion (plan revision 2). A link can preselect a
 * service, e.g. /book-a-consultation?service=seo from the SEO page.
 */
@Component({
  selector: 'mk-book-a-consultation',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, Icon, PageHero, FormError, Honeypot],
  templateUrl: './book-a-consultation.html',
})
export class BookAConsultation {
  private readonly api = inject(LeadApi);
  protected readonly site = inject(SiteData);
  protected readonly settings = this.site.settings;
  protected readonly serviceOptions = SERVICE_OPTIONS;
  protected readonly budgetOptions = BUDGET_OPTIONS;

  protected readonly form = new FormGroup({
    name: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.maxLength(120)] }),
    email: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.email] }),
    company: new FormControl('', { nonNullable: true, validators: [Validators.maxLength(160)] }),
    website: new FormControl('', { nonNullable: true, validators: [Validators.maxLength(300)] }),
    phone: new FormControl('', { nonNullable: true, validators: [Validators.maxLength(40)] }),
    services: new FormArray(SERVICE_OPTIONS.map(() => new FormControl(false, { nonNullable: true })),
      { validators: (a) => (a.value as boolean[]).some(Boolean) ? null : { required: true } }),
    budget: new FormControl('', { nonNullable: true }),
    message: new FormControl('', { nonNullable: true, validators: [Validators.maxLength(5000)] }),
    preferred_contact: new FormControl('', { nonNullable: true, validators: [Validators.maxLength(160)] }),
    nickname: new FormControl('', { nonNullable: true }),
  });

  protected readonly sending = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly sentTo = signal<string | null>(null);
  private readonly done = viewChild<ElementRef<HTMLElement>>('done');
  private openedAt = 0;
  /** The invisible browser check: started when the visitor first focuses a field. */
  protected readonly proof = this.api.proof();

  constructor() {
    pageDescription('Book a free, no-obligation consultation with Outlogik about SEO, social media, content or analytics for your business.');
    const preselect = inject(ActivatedRoute).snapshot.queryParamMap.get('service');
    const index = SERVICE_OPTIONS.findIndex((o) => o.value === preselect);
    if (index >= 0) this.form.controls.services.at(index).setValue(true);
    afterNextRender(() => (this.openedAt = performance.now()));
  }

  protected invalid(name: keyof typeof this.form.controls): boolean {
    const c = this.form.controls[name];
    return c.invalid && (c.touched || c.dirty);
  }

  protected async submit(): Promise<void> {
    this.error.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.error.set('Please fill in the highlighted fields.');
      return;
    }
    const v = this.form.getRawValue();
    this.sending.set(true);
    const result = await this.api.send('leads/consultation', {
      name: v.name, email: v.email, company: v.company, website: v.website, phone: v.phone,
      services: SERVICE_OPTIONS.filter((_, i) => v.services[i]).map((o) => o.value),
      budget: v.budget || null, message: v.message, preferred_contact: v.preferred_contact,
    }, this.openedAt, v.nickname, this.proof);
    this.sending.set(false);
    if (result.ok) {
      this.sentTo.set(v.email);
      setTimeout(() => this.done()?.nativeElement.focus());
    } else {
      this.error.set(result.message);
      for (const f of result.fields) this.form.get(f)?.setErrors({ server: true });
    }
  }
}
