import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { IconName } from '../../shared/icon/icons';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState } from '../../shared/states/states';

/**
 * Temporary page for sections built in later Phase 1 steps. Inputs come from route data.
 * Says plainly that the page isn't built yet; never shows sample data.
 */
@Component({
  selector: 'ol-coming-soon',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PageHeader, EmptyState],
  template: `
    <ol-page-header [title]="title()" [description]="description()" />
    <ol-empty-state [icon]="icon()" title="This page isn't built yet"
      [message]="'It arrives in step ' + step() + ' of Phase 1.'" />
  `,
})
export class ComingSoon {
  readonly title = input.required<string>();
  readonly description = input<string>();
  readonly icon = input<IconName>('inbox');
  readonly step = input.required<number>();
}
