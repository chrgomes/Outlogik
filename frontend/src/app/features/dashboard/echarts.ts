// Only the ECharts parts the dashboard uses, so the download stays small.
import { BarChart, LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { init, use } from 'echarts/core';
import { SVGRenderer } from 'echarts/renderers';

use([LineChart, BarChart, GridComponent, TooltipComponent, SVGRenderer]);

export { init };
