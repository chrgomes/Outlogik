import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { CONSULTATION_PATH, SERVICES } from '../../config/site';
import { SiteData } from '../../config/site-data';
import { CtaBand } from '../../shared/cta-band';
import { pageDescription } from '../../seo/seo';
import { PageHero } from '../../shared/page-hero';

/**
 * /about: the approach and values (plan revision 2, decision C). The founding story and team are
 * added once provided; nothing here is invented.
 */
@Component({
  selector: 'mk-about',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Icon, PageHero, CtaBand],
  templateUrl: './about.html',
})
export class About {
  protected readonly settings = inject(SiteData).settings;
  protected readonly consultationPath = CONSULTATION_PATH;
  protected readonly services = SERVICES;

  protected readonly values = [
    { title: 'Show the work', text: 'You should never have to wonder what you’re paying for. That’s why every client gets a portal.' },
    { title: 'Plain English', text: 'Reports and recommendations you can read without a glossary.' },
    { title: 'Straight answers', text: 'We tell you what we think will work, what won’t, and why, even when it’s not what you hoped to hear.' },
    { title: 'One team, one plan', text: 'Search, social, content and analytics planned together, not in separate silos.' },
  ];

  protected readonly wont = [
    { title: 'Guarantee rankings', text: 'Search engines decide rankings. Anyone who guarantees them is guessing, or worse.' },
    { title: 'Take shortcuts that put you at risk', text: 'No bought links, fake reviews or tricks that could get your site penalised.' },
    { title: 'Hold your accounts hostage', text: 'Your accounts and your content are yours. We work through access you can remove at any time.' },
    { title: 'Hide behind jargon', text: 'If we can’t explain why we’re doing something, we shouldn’t be doing it.' },
  ];

  constructor() {
    pageDescription('Outlogik is a digital marketing agency built on straight answers: one team for SEO, social, content and analytics, with a client portal that keeps the work in view.');
  }
}
