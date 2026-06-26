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
const maxDateTickCount = 12

// 不具合の右軸スケールは段階的に: 30 → 50 → 70 → 90 …（少件数で全体を占有しないように）。
function steppedBugMax(peak: number, baseMax: number): number {
  const normalizedBaseMax = Math.max(1, Math.floor(baseMax))
  if (peak <= normalizedBaseMax) return normalizedBaseMax
  return Math.ceil((peak - normalizedBaseMax) / 20) * 20 + normalizedBaseMax
}

function formatAxisDate(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return value
  return `${Number(match[2])}/${Number(match[3])}`
}

function getHiddenDateIndexes(chart: PbChartResponse): Set<number> {
  if (chart.series.length < 2) {
    return new Set()
  }

  const first = chart.series[0]
  const second = chart.series[1]
  const firstHasVisibleValue =
    first.planned_remaining != null ||
    first.actual_remaining != null ||
    first.planned_completed_daily != null ||
    first.actual_completed_daily != null ||
    first.bug_open != null ||
    first.bug_suspended != null ||
    first.bug_resolved != null
  const isLeadingPadding = !firstHasVisibleValue
  const isPlanBaseline =
    first.planned_remaining != null &&
    first.planned_completed_daily === 0 &&
    second.planned_completed_daily != null &&
    second.planned_completed_daily > 0
  const isActualBaseline =
    first.actual_remaining != null &&
    first.actual_completed_daily == null &&
    second.actual_completed_daily != null

  return isLeadingPadding || isPlanBaseline || isActualBaseline ? new Set([0]) : new Set()
}

function getDayOfWeek(value: string): number | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return null
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])).getDay()
}

function selectDateTickIndexes(dates: string[], hiddenIndexes: ReadonlySet<number> = new Set()): Set<number> {
  if (dates.length <= maxDateTickCount) {
    return new Set(dates.map((_, index) => index).filter((index) => !hiddenIndexes.has(index)))
  }

  const minGap = Math.ceil(dates.length / maxDateTickCount)
  const firstVisibleIndex = hiddenIndexes.has(0) ? 1 : 0
  const selected = new Set<number>([firstVisibleIndex, dates.length - 1])
  let lastSelected = firstVisibleIndex

  dates.forEach((date, index) => {
    const isMonday = getDayOfWeek(date) === 1
    const isMonthStart = date.endsWith('-01')
    if (hiddenIndexes.has(index) || (!isMonday && !isMonthStart)) {
      return
    }
    if (index - lastSelected >= minGap && dates.length - 1 - index >= Math.max(1, minGap - 1)) {
      selected.add(index)
      lastSelected = index
    }
  })

  for (let index = 0; index < dates.length; index += minGap) {
    if (
      !hiddenIndexes.has(index) &&
      ![...selected].some((selectedIndex) => Math.abs(selectedIndex - index) < minGap)
    ) {
      selected.add(index)
    }
  }

  return selected
}

export function buildPbChartOption(
  chart: PbChartResponse,
  layers: ChartLayers,
  bugAxisMax: number,
  hiddenPastPlanIds?: ReadonlySet<number>,
): PbChartOption {
  const dates = chart.series.map((item) => item.date)
  const hiddenDateIndexes = getHiddenDateIndexes(chart)
  const hiddenDates = new Set([...hiddenDateIndexes].map((index) => dates[index]))
  const firstVisibleDate = dates.find((_, index) => !hiddenDateIndexes.has(index))
  const dateTickIndexes = selectDateTickIndexes(dates, hiddenDateIndexes)
  const series: PbChartOption['series'] = []
  const hasBugData =
    chart.has_bugs && chart.series.some((item) => item.bug_open !== null)
  const showBugs = layers.bugs && hasBugData
  const today = getTodayString()
  // 検出累積(open+suspended+resolved)のピーク。右軸の段階的な上限に使う。
  // 今日以降の未来日付は描画しないため、ピーク計算も今日以前に限定する。
  const bugPeak = showBugs
    ? Math.max(
        0,
        ...chart.series
          .filter((item) => item.date <= today)
          .map(
            (item) => (item.bug_open ?? 0) + (item.bug_suspended ?? 0) + (item.bug_resolved ?? 0),
          ),
      )
    : 0
  const plannedLineColor = '#8a94a6'
  const pastPlanLineColor = 'rgba(95, 107, 126, 0.42)'
  const bugLegendNames =
    chart.bug_count_source === 'test_result'
      ? { resolved: 'Fixed', suspended: 'Suspend', open: 'Fail' }
      : { resolved: '解決済み', suspended: '対応見送り', open: '起票チケット' }
  const dashedLegendIcon = 'path://M0,4h5v2H0zM8,4h5v2H8z'
  const showTodayLine = layers.todayLine && dates.includes(today)
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
      name: bugLegendNames.resolved,
      type: 'line',
      yAxisIndex: 1,
      data: chart.series.map((item) => (item.date <= today ? item.bug_resolved : null)),
      stack: 'bug',
      symbol: 'none',
      lineStyle: { width: 1, color: 'rgba(46, 160, 67, 0.6)' },
      areaStyle: { color: 'rgba(46, 160, 67, 0.18)' },
      itemStyle: { color: 'rgba(46, 160, 67, 0.55)' },
      z: 0,
    })
    series.push({
      name: bugLegendNames.suspended,
      type: 'line',
      yAxisIndex: 1,
      data: chart.series.map((item) => (item.date <= today ? item.bug_suspended : null)),
      stack: 'bug',
      symbol: 'none',
      lineStyle: { width: 1, color: 'rgba(214, 170, 0, 0.7)' },
      areaStyle: { color: 'rgba(214, 170, 0, 0.18)' },
      itemStyle: { color: 'rgba(214, 170, 0, 0.6)' },
      z: 0,
    })
    series.push({
      name: bugLegendNames.open,
      type: 'line',
      yAxisIndex: 1,
      data: chart.series.map((item) => (item.date <= today ? item.bug_open : null)),
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
      name: '計画/d',
      type: 'bar',
      data: chart.series.map((item) => item.planned_completed_daily),
      barGap: '-100%',
      barCategoryGap: '42%',
      itemStyle: { color: 'rgba(47, 111, 237, 0.18)' },
      z: 1,
    })
    series.push({
      name: '実績/d',
      type: 'bar',
      data: chart.series.map((item) => item.actual_completed_daily),
      barWidth: '30%',
      itemStyle: { color: 'rgba(47, 111, 237, 0.55)' },
      z: 2,
    })
  }

  if (layers.pastPlans) {
    chart.past_plans
      .filter((pastPlan) => !hiddenPastPlanIds?.has(pastPlan.plan_id))
      .forEach((pastPlan) => {
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
      name: '残項目(計画)',
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
      name: '残項目(実績)',
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
          if (name === '残項目(計画)') {
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
    backgroundColor: '#ffffff',
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
    grid: { left: 58, right: showBugs ? 52 : 24, top: 42, bottom: 42 },
    xAxis: {
      type: 'category',
      data: dates,
      min: firstVisibleDate,
      boundaryGap: true,
      axisLabel: {
        show: true,
        color: '#687386',
        margin: 10,
        hideOverlap: true,
        showMinLabel: true,
        formatter: (value: string) => (hiddenDates.has(value) ? '' : formatAxisDate(value)),
        interval: (index: number, value: string) => value === firstVisibleDate || dateTickIndexes.has(index),
      },
      axisLine: { show: false },
      axisTick: {
        show: true,
        alignWithLabel: true,
        interval: (index: number, value: string) => value === firstVisibleDate || (dateTickIndexes.has(index) && !hiddenDates.has(value)),
        lineStyle: { color: '#cbd2dc' },
      },
    },
    yAxis: showBugs
      ? [
          {
            type: 'value',
            name: '残件数',
            // 0 を底に固定（負の日別補正値や右軸との目盛合わせで軸が負側へ伸びるのを防ぐ）。
            min: 0,
            nameTextStyle: { color: '#7b8794' },
            splitLine: { lineStyle: { color: '#e8ebef' } },
            axisLabel: { color: '#687386' },
          },
          {
            type: 'value',
            name: '課題件数',
            position: 'right',
            min: 0,
            max: steppedBugMax(bugPeak, bugAxisMax),
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

