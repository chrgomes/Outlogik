import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { Question } from '../../config/services-content';
import { CONSULTATION_PATH, TOOLS } from '../../config/site';
import { SiteData } from '../../config/site-data';
import { StatusBadge } from '../../layout/status-badge';
import { CtaBand } from '../../shared/cta-band';
import { Faq } from '../../shared/faq';
import { pageDescription } from '../../seo/seo';
import { PageHero } from '../../shared/page-hero';
import { Screenshot } from '../../shared/screenshot';

/**
 * /how-we-work: the process from consultation to monthly reporting, and the client portal with
 * real screenshots and every portal feature labelled with its status (plan revision 2, section 4).
 */
@Component({
  selector: 'mk-how-we-work',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Icon, PageHero, Faq, CtaBand, Screenshot, StatusBadge],
  templateUrl: './how-we-work.html',
})
export class HowWeWork {
  private readonly site = inject(SiteData);
  protected readonly settings = this.site.settings;
  protected readonly features = this.site.portalFeatures;
  protected readonly consultationPath = CONSULTATION_PATH;
  protected readonly tools = TOOLS;

  protected readonly steps = [
    {
      title: 'Free consultation',
      text: 'A conversation about your business, your customers and what you want from marketing. We’ll look at where you are today and give you our honest view.',
      points: ['No cost and no obligation', 'Your goals, budget and timescales', 'Where we think we can help, and where we can’t'],
    },
    {
      title: 'A clear proposal',
      text: 'A written proposal setting out exactly what we’ll do, what you’ll get and what it costs.',
      points: ['The services and work included', 'The price, monthly and one-off', 'How we’ll measure progress'],
    },
    {
      title: 'Onboarding',
      text: 'We set up your client portal, get access to the tools we need, and agree the first priorities with you.',
      points: ['Your private client portal', 'Access to your accounts, which you keep control of', 'A plan for the first month'],
    },
    {
      title: 'Monthly work and reporting',
      text: 'We do the agreed work each month, report on it in plain English, and adjust the plan as we learn what works.',
      points: ['The work, recorded in your portal', 'A monthly report with recommendations', 'Time to review together, if you’d like it'],
    },
  ];

  protected readonly needs = [
    { title: 'Access to your accounts', text: 'Such as Google Analytics, Search Console and your social media accounts. We’ll list exactly what’s needed.' },
    { title: 'A main contact', text: 'Someone who can answer questions and approve work.' },
    { title: 'Timely approvals', text: 'Nothing goes live without your approval, so quick replies keep the plan on track.' },
    { title: 'Honest feedback', text: 'Tell us what you like and what you don’t. It makes the work better.' },
  ];

  protected readonly questions: Question[] = [
    { q: 'Who will I work with?', a: 'You’ll have one main point of contact, who coordinates all the work we do for you.' },
    { q: 'Is the client portal included?', a: 'Yes. Every client gets their own private portal, at no extra cost.' },
    { q: 'Who owns the accounts and the work?', a: 'You do. We work through access you grant, which you can remove at any time.' },
    { q: 'Can we change the plan later?', a: 'Yes. We review the plan with you regularly and adjust it as your needs change.' },
  ];

  constructor() {
    pageDescription('How Outlogik works with clients: a free consultation, a clear proposal, onboarding, then monthly work and reporting, with your own client portal.');
  }
}
