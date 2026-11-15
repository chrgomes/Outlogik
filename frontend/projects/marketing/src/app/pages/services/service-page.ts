import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { Meta } from '@angular/platform-browser';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { SERVICE_CONTENT, ServiceContent } from '../../config/services-content';
import { CONSULTATION_PATH, SERVICES } from '../../config/site';
import { SiteData } from '../../config/site-data';
import { StatusBadge } from '../../layout/status-badge';
import { CtaBand } from '../../shared/cta-band';
import { Faq } from '../../shared/faq';
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
  /** The service name as it reads mid-sentence ("SEO", "content marketing"). */
  protected readonly topic = this.service.name === 'SEO' ? 'SEO' : this.service.name.toLowerCase();
  protected readonly crumbs = [{ label: 'Services', path: '/services' }, { label: this.service.name }];
  protected readonly related = this.content.related.map((slug) => SERVICES.find((s) => s.slug === slug)!);

  /** Portal features relevant to this service, in the order (and with the status) staff set. */
  protected readonly features = computed(() =>
    this.site.portalFeatures().filter((f) => this.content.portalFeatures.includes(f.slug)));

  constructor() {
    inject(Meta).updateTag({ name: 'description', content: this.content.description });
  }
}
