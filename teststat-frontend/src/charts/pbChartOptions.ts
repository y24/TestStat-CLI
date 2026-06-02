import type { BarSeriesOption, LineSeriesOption } from 'echarts/charts'
import type { ComposeOption } from 'echarts/core'
import type {
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
  | GridComponentOption
  | LegendComponentOption
  | TooltipComponentOption
>

const chartFontFamily =
  '"Yu Gothic", "Yu Gothic UI", "Meiryo", "Hiragino Kaku Gothic ProN", "Noto Sans JP", sans-serif'

// 不具合の右軸スケールは段階的に: 30 → 50 → 70 → 90 …（少件数で全体を占有しないように）。
function steppedBugMax(peak: number): number {
  if (peak <= 30) return 30
  return Math.ceil((peak - 30) / 20) * 20 + 30
}

export function buildPbChartOption(chart: PbChartResponse, layers: ChartLayers): PbChartOption {
  const dates = chart.series.map((item) => item.date)
  const series: PbChartOption['series'] = []
  const hasBugData =
    chart.has_bugs && chart.series.some((item) => item.bug_open !== null)
  const showBugs = layers.bugs && hasBugData
  // 検出累積(open+suspended+resolved)のピーク。右軸の段階的な上限に使う。
  const bugPeak = showBugs
    ? Math.max(
        0,
        ...chart.series.map(
          (item) => (item.bug_open ?? 0) + (item.bug_suspended ?? 0) + (item.bug_resolved ?? 0),
        ),
      )
    : 0
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

  if (showBugs) {
    // 下から 緑(完了)→黄(対応見送り)→赤(未解消) の積み上げエリア。右軸・バーンダウン線より背面。
    series.push({
      name: '完了不具合(累積)',
      type: 'line',
      yAxisIndex: 1,
      data: chart.series.map((item) => item.bug_resolved),
      stack: 'bug',
      symbol: 'none',
      lineStyle: { width: 1, color: 'rgba(46, 160, 67, 0.6)' },
      areaStyle: { color: 'rgba(46, 160, 67, 0.18)' },
      itemStyle: { color: 'rgba(46, 160, 67, 0.55)' },
      z: 0,
    })
    series.push({
      name: '対応見送り(累積)',
      type: 'line',
      yAxisIndex: 1,
      data: chart.series.map((item) => item.bug_suspended),
      stack: 'bug',
      symbol: 'none',
      lineStyle: { width: 1, color: 'rgba(214, 170, 0, 0.7)' },
      areaStyle: { color: 'rgba(214, 170, 0, 0.18)' },
      itemStyle: { color: 'rgba(214, 170, 0, 0.6)' },
      z: 0,
    })
    series.push({
      name: '未解消不具合',
      type: 'line',
      yAxisIndex: 1,
      data: chart.series.map((item) => item.bug_open),
      stack: 'bug',
      symbol: 'none',
      lineStyle: { width: 1, color: 'rgba(214, 69, 111, 0.65)' },
      areaStyle: { color: 'rgba(214, 69, 111, 0.16)' },
      itemStyle: { color: 'rgba(214, 69, 111, 0.55)' },
      z: 0,
    })
  }

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
    textStyle: {
      fontFamily: chartFontFamily,
    },
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
    grid: { left: 58, right: showBugs ? 52 : 24, top: 42, bottom: 18 },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: true,
      axisLabel: { show: false },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    yAxis: showBugs
      ? [
          {
            type: 'value',
            name: '件数',
            // 0 を底に固定（負の日別補正値や右軸との目盛合わせで軸が負側へ伸びるのを防ぐ）。
            min: 0,
            nameTextStyle: { color: '#7b8794' },
            splitLine: { lineStyle: { color: '#e8ebef' } },
            axisLabel: { color: '#687386' },
          },
          {
            type: 'value',
            name: '件数（不具合）',
            position: 'right',
            min: 0,
            max: steppedBugMax(bugPeak),
            minInterval: 1,
            nameTextStyle: { color: '#7b8794' },
            splitLine: { show: false },
            axisLabel: { color: '#9aa4b1' },
          },
        ]
      : {
          type: 'value',
          name: '件数',
          nameTextStyle: { color: '#7b8794' },
          splitLine: { lineStyle: { color: '#e8ebef' } },
          axisLabel: { color: '#687386' },
        },
    series,
  }
}
