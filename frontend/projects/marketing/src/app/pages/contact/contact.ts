import {
  ChangeDetectionStrategy, Component, ElementRef, afterNextRender, inject, signal, viewChild,
} from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { CONTACT_TOPICS } from '../../config/forms';
import { CONSULTATION_PATH, LOGIN_URL } from '../../config/site';
import { SiteData } from '../../config/site-data';
import { FormError, Honeypot } from '../../shared/form-status';
import { LeadApi } from '../../shared/lead-api';
import { pageDescription } from '../../seo/seo';
import { PageHero } from '../../shared/page-hero';

/** /contact: a message form, plus contact details once they're set in the admin area. */
@Component({
  selector: 'mk-contact',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, Icon, PageHero, FormError, Honeypot],
  templateUrl: './contact.html',
})
export class Contact {
  private readonly api = inject(LeadApi);
  protected readonly site = inject(SiteData);
  protected readonly settings = this.site.settings;
  protected readonly topics = CONTACT_TOPICS;
  protected readonly consultationPath = CONSULTATION_PATH;
  protected readonly loginUrl = LOGIN_URL;

  protected readonly form = new FormGroup({
    name: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.maxLength(120)] }),
    email: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.email] }),
    company: new FormControl('', { nonNullable: true, validators: [Validators.maxLength(160)] }),
    topic: new FormControl('general', { nonNullable: true }),
    message: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.maxLength(5000)] }),
    nickname: new FormControl('', { nonNullable: true }),
  });

  protected readonly sending = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly sentTo = signal<string | null>(null);
  private readonly done = viewChild<ElementRef<HTMLElement>>('done');
  private openedAt = 0;

  constructor() {
    pageDescription('Contact Outlogik: questions about our services, existing client support, partnerships and press.');
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
    const { nickname, ...body } = this.form.getRawValue();
    this.sending.set(true);
    const result = await this.api.send('leads/contact', body, this.openedAt, nickname);
    this.sending.set(false);
    if (result.ok) {
      this.sentTo.set(body.email);
      setTimeout(() => this.done()?.nativeElement.focus());
    } else {
      this.error.set(result.message);
      for (const f of result.fields) this.form.get(f)?.setErrors({ server: true });
    }
  }
}
