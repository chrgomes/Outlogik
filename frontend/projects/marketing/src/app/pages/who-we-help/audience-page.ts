import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { AUDIENCE_CONTENT, AudienceContent } from '../../config/audiences-content';
import { AUDIENCES, CONSULTATION_PATH, SERVICES } from '../../config/site';
import { SiteData } from '../../config/site-data';
import { CtaBand } from '../../shared/cta-band';
import { Faq } from '../../shared/faq';
import { pageDescription } from '../../seo/seo';
import { PageHero } from '../../shared/page-hero';

/** One page per business type (/who-we-help/<slug>), built from AUDIENCE_CONTENT. */
@Component({
  selector: 'mk-audience-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Icon, PageHero, Faq, CtaBand],
  templateUrl: './audience-page.html',
})
export class AudiencePage {
  protected readonly settings = inject(SiteData).settings;
  protected readonly consultationPath = CONSULTATION_PATH;

  protected readonly content: AudienceContent =
    AUDIENCE_CONTENT[inject(ActivatedRoute).snapshot.data['slug'] as string];
  protected readonly audience = AUDIENCES.find((a) => a.slug === this.content.slug)!;
  protected readonly others = AUDIENCES.filter((a) => a.slug !== this.content.slug);
  protected readonly crumbs = [{ label: 'Who we help', path: '/who-we-help' }, { label: this.audience.name }];
  protected readonly help = this.content.help.map((h) => ({
    ...h, ...SERVICES.find((s) => s.slug === h.service)!,
  }));

  constructor() {
    pageDescription(this.content.description);
  }
}
