import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { SERVICE_CONTENT, ServiceContent } from '../../config/services-content';
import { CONSULTATION_PATH, SERVICES, serviceTopic } from '../../config/site';
import { SiteData } from '../../config/site-data';
import { StatusBadge } from '../../layout/status-badge';
import { CtaBand } from '../../shared/cta-band';
import { Faq } from '../../shared/faq';
import { pageDescription } from '../../shared/meta';
import { PageHero } from '../../shared/page-hero';

/**
 * One page per service (/services/<slug>), built from SERVICE_CONTENT. The route passes the slug
 * in its data; unknown slugs never reach this page (they fall through to the 404 route).
 */
@Component({
  selector: 'mk-service-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Icon, StatusBadge, PageHero, Faq, CtaBand],
  templateUrl: './service-page.html',
})
export class ServicePage {
  private readonly site = inject(SiteData);
  protected readonly settings = this.site.settings;
  protected readonly consultationPath = CONSULTATION_PATH;

  protected readonly content: ServiceContent =
    SERVICE_CONTENT[inject(ActivatedRoute).snapshot.data['slug'] as string];
  protected readonly service = SERVICES.find((s) => s.slug === this.content.slug)!;
  protected readonly topic = serviceTopic(this.service);
  protected readonly crumbs = [{ label: 'Services', path: '/services' }, { label: this.service.name }];
  protected readonly related = this.content.related.map((slug) => SERVICES.find((s) => s.slug === slug)!);

  /** Portal features relevant to this service, in the order (and with the status) staff set. */
  protected readonly features = computed(() =>
    this.site.portalFeatures().filter((f) => this.content.portalFeatures.includes(f.slug)));

  constructor() {
    pageDescription(this.content.description);
  }
}
