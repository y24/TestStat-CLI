import type { BarSeriesOption, LineSeriesOption } from 'echarts/charts'
import type { ComposeOption } from 'echarts/core'
import type {
  DataZoomComponentOption,
  GridComponentOption,
  LegendComponentOption,
  TooltipComponentOption,
} from 'echarts/components'
import type { PbChartResponse } from '../api/types'
import type { ChartLayers } from '../types/ui'
import { getTodayString } from '../utils/date'
import { displayLabel } from '../utils/plans'

export type PbChartOption = ComposeOption<
  | BarSeriesOption
  | LineSeriesOption
  | DataZoomComponentOption
  | GridComponentOption
  | LegendComponentOption
  | TooltipComponentOption
>

export function buildChartNotices(chart: PbChartResponse) {
  const notices: string[] = []
  const hasPlan = chart.planned_total_cases !== null
  const hasActuals = chart.available_cases > 0 && chart.series.some((item) => item.actual_remaining !== null)
  const hasNegativeDaily = chart.series.some(
    (item) =>
      (item.actual_completed_daily !== null && item.actual_completed_daily < 0) ||
      (item.planned_completed_daily !== null && item.planned_completed_daily < 0),
  )

  if (!hasPlan) {
    notices.push('計画未作成')
  }
  if (!hasActuals) {
    notices.push('実績未受信')
  }
  if (hasNegativeDaily) {
    notices.push('負の日別値あり')
  }
  return notices
}

export function buildPbChartOption(chart: PbChartResponse, layers: ChartLayers): PbChartOption {
  const dates = chart.series.map((item) => item.date)
  const series: PbChartOption['series'] = []
  const plannedLineColor = '#8a94a6'
  const pastPlanLineColor = 'rgba(95, 107, 126, 0.42)'
  const dashedLegendIcon = 'path://M0,4h5v2H0zM8,4h5v2H8z'
  const today = getTodayString()
  const showTodayLine = dates.includes(today)
  const todayMarkLine = showTodayLine
    ? {
        symbol: 'none',
        silent: true,
        lineStyle: { type: 'solid' as const, width: 1.5, color: '#d6456f' },
        label: { formatter: '今日', position: 'insideEndTop' as const, color: '#d6456f' },
        data: [{ xAxis: today }],
      }
    : undefined

  if (layers.dailyBars) {
    series.push({
      name: '日別消化計画',
      type: 'bar',
      data: chart.series.map((item) => item.planned_completed_daily),
      barGap: '-100%',
      barCategoryGap: '42%',
      itemStyle: { color: 'rgba(47, 111, 237, 0.18)' },
      z: 1,
    })
    series.push({
      name: '日別消化実績',
      type: 'bar',
      data: chart.series.map((item) => item.actual_completed_daily),
      barWidth: '30%',
      itemStyle: { color: 'rgba(47, 111, 237, 0.55)' },
      z: 2,
    })
  }

  if (layers.pastPlans) {
    chart.past_plans.forEach((pastPlan) => {
      const remainingByDate = new Map(
        pastPlan.series.map((item) => [item.date, item.planned_remaining]),
      )
      series.push({
        name: `過去計画 ${displayLabel(pastPlan.label)} v${pastPlan.version}`,
        type: 'line',
        data: dates.map((date) => remainingByDate.get(date) ?? null),
        connectNulls: false,
        symbol: 'none',
        lineStyle: { type: 'dashed', width: 1, color: pastPlanLineColor },
        itemStyle: { color: pastPlanLineColor },
        z: 3,
      })
    })
  }

  if (layers.plannedLine) {
    series.push({
      name: '計画未実施',
      type: 'line',
      data: chart.series.map((item) => item.planned_remaining),
      connectNulls: false,
      symbol: 'none',
      lineStyle: { type: 'dashed', width: 2, color: plannedLineColor },
      itemStyle: { color: plannedLineColor },
      z: 5,
      markLine: !layers.actualLine ? todayMarkLine : undefined,
    })
  }

  if (layers.actualLine) {
    series.push({
      name: '実績未実施',
      type: 'line',
      data: chart.series.map((item) => item.actual_remaining),
      connectNulls: false,
      symbol: 'circle',
      symbolSize: 5,
      lineStyle: { width: 2.5, color: '#2f6fed' },
      itemStyle: { color: '#2f6fed' },
      z: 6,
      markLine: todayMarkLine,
    })
  }

  const legendData = Array.isArray(series)
    ? series
        .map((item) => item.name)
        .filter((name): name is string => typeof name === 'string')
        .map((name) => {
          if (name === '計画未実施') {
            return {
              name,
              icon: dashedLegendIcon,
              itemStyle: { color: plannedLineColor },
            }
          }
          if (name.startsWith('過去計画 ')) {
            return {
              name,
              icon: dashedLegendIcon,
              itemStyle: { color: pastPlanLineColor },
            }
          }
          return name
        })
    : undefined

  return {
    animationDuration: 250,
    color: ['#8a94a6', '#2f6fed'],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      valueFormatter: (value) => (value === null || value === undefined ? '-' : `${value} 件`),
    },
    legend: {
      top: 0,
      itemWidth: 14,
      itemHeight: 10,
      textStyle: { color: '#46515f' },
      type: 'scroll',
      data: legendData,
    },
    grid: { left: 58, right: 24, top: 42, bottom: 58 },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: true,
      axisLabel: { formatter: (value: string) => value.slice(5).replace('-', '/') },
      axisLine: { lineStyle: { color: '#c8d0da' } },
      axisTick: { alignWithLabel: true },
    },
    yAxis: {
      type: 'value',
      name: '件数',
      nameTextStyle: { color: '#7b8794' },
      splitLine: { lineStyle: { color: '#e8ebef' } },
      axisLabel: { color: '#687386' },
    },
    dataZoom: [
      { type: 'inside' },
      { type: 'slider', height: 18, bottom: 20 },
    ],
    series,
  }
}
