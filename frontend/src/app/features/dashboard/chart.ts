import {
  ChangeDetectionStrategy, Component, DestroyRef, ElementRef, afterNextRender, effect, inject, input,
} from '@angular/core';

import { ThemeService } from '../../core/theme.service';

/** Chart colours, read from the theme's CSS custom properties so both modes are right. */
export interface ChartColors {
  primary: string; compare: string; search: string; error: string; warning: string;
  grid: string; text: string; muted: string; surface: string;
}

/** Builds ECharts options from the current colours. */
export type ChartOptions = (c: ChartColors) => Record<string, unknown>;

type ECharts = typeof import('./echarts');

/**
 * One ECharts chart. ECharts is loaded on first use, so it isn't in the app's first download.
 * Redraws when the options or the light/dark mode change, and on resize.
 * The chart is drawn as SVG and hidden from screen readers: `label` describes it, and the
 * numbers are always also shown as text on the page.
 */
@Component({
  selector: 'ol-chart',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="chart" role="img" [attr.aria-label]="label()" [style.height]="height()"></div>`,
  styles: `:host { display: block; } .chart { width: 100%; }`,
})
export class Chart {
  readonly options = input.required<ChartOptions>();
  readonly label = input.required<string>();
  readonly height = input('240px');

  private readonly host = inject(ElementRef<HTMLElement>);
  private readonly theme = inject(ThemeService);
  private chart: ReturnType<ECharts['init']> | null = null;
  private lib: ECharts | null = null;

  constructor() {
    const destroy = inject(DestroyRef);
    afterNextRender(async () => {
      if (typeof ResizeObserver === 'undefined') return; // very old browsers and unit tests
      this.lib = await import('./echarts');
      const el = this.host.nativeElement.querySelector('.chart') as HTMLElement;
      this.chart = this.lib.init(el, undefined, { renderer: 'svg' });
      this.draw();
      const resize = new ResizeObserver(() => this.chart?.resize());
      resize.observe(el);
      destroy.onDestroy(() => { resize.disconnect(); this.chart?.dispose(); });
    });
    effect(() => {
      this.options();
      this.theme.resolved();
      // Wait a frame so the new mode's CSS variables are in place.
      requestAnimationFrame(() => this.draw());
    });
  }

  private draw(): void {
    if (!this.chart) return;
    const css = getComputedStyle(document.documentElement);
    const v = (name: string) => css.getPropertyValue(name).trim();
    const colors: ChartColors = {
      primary: v('--ol-chart-primary'), compare: v('--ol-chart-compare'), search: v('--ol-chart-search'),
      error: v('--ol-chart-error'), warning: v('--ol-chart-warning'), grid: v('--ol-chart-grid'),
      text: v('--ol-text'), muted: v('--ol-text-muted'), surface: v('--ol-surface-raised'),
    };
    const font = getComputedStyle(this.host.nativeElement).fontFamily;
    this.chart.setOption({
      animation: false,
      textStyle: { fontFamily: font, color: colors.muted },
      aria: { enabled: false },
      tooltip: { trigger: 'axis', backgroundColor: colors.surface, borderColor: colors.grid,
        textStyle: { color: colors.text, fontFamily: font } },
      ...this.options()(colors),
    }, true);
  }
}
