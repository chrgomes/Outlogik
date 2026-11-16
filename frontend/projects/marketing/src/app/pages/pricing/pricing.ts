import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { Question } from '../../config/services-content';
import { CONSULTATION_PATH } from '../../config/site';
import { SiteData } from '../../config/site-data';
import { CtaBand } from '../../shared/cta-band';
import { Faq } from '../../shared/faq';
import { pageDescription } from '../../seo/seo';
import { PageHero } from '../../shared/page-hero';

/**
 * /pricing: how pricing works. There are no public prices (decided 2026-11-15); every price
 * comes in a written proposal after a free consultation.
 */
@Component({
  selector: 'mk-pricing',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Icon, PageHero, Faq, CtaBand],
  templateUrl: './pricing.html',
})
export class Pricing {
  protected readonly settings = inject(SiteData).settings;
  protected readonly consultationPath = CONSULTATION_PATH;

  protected readonly factors = [
    { title: 'Which services', text: 'One service, or several working together.' },
    { title: 'How much work', text: 'For example, how many posts, articles or pages each month.' },
    { title: 'Where you’re starting from', text: 'A site that needs technical work, or one that’s already in good shape.' },
    { title: 'How many places', text: 'The number of websites, locations or social channels.' },
    { title: 'One-off or ongoing', text: 'A single project, monthly work, or both.' },
  ];

  protected readonly included = [
    'The services and work included, written out in plain English',
    'The price: monthly, one-off, or both',
    'How we’ll measure progress and report on it',
    'What we’ll need from you',
    'The terms, explained before you agree to anything',
  ];

  protected readonly questions: Question[] = [
    { q: 'Why don’t you publish prices?', a: 'Because every business needs something different. A fixed package would mean paying for work you don’t need, or missing work you do.' },
    { q: 'Is the consultation really free?', a: 'Yes. It’s free and there’s no obligation to go ahead.' },
    { q: 'Is there a minimum budget?', a: 'There’s no fixed minimum. When you book, you can tell us your budget range (it’s optional). It helps us recommend the work that will make the most difference for what you want to spend.' },
    { q: 'Can I change what’s included later?', a: 'Yes. We review the plan with you and update the proposal when your needs change.' },
    { q: 'How long is the agreement?', a: 'It depends on the work, and it’s set out in your proposal. We’ll explain the terms before you agree to anything.' },
  ];

  constructor() {
    pageDescription('How Outlogik pricing works: no fixed packages, a free consultation, then a clear written proposal with exactly what’s included and what it costs.');
  }
}
