import { useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts/core'
import type { ECharts } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { fetchPbChart, fetchPlans, fetchProgressFiles } from '../api/client'
import type { FileProgressItem, PbChartResponse, PlanItem, ProjectItem } from '../api/types'
import { buildChartNotices, buildPbChartOption } from '../charts/pbChartOptions'
import type { ChartLayers } from '../types/ui'
import { formatDate, formatDateTime } from '../utils/date'
import { getErrorMessage } from '../utils/errors'

echarts.use([
  BarChart,
  CanvasRenderer,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  LineChart,
  MarkLineComponent,
  TooltipComponent,
])

interface ChartResult {
  testingId: number
  label: string | null
  includePastPlans: boolean
  chart: PbChartResponse | null
  files: FileProgressItem[]
  plans: PlanItem[]
  error: string | null
}

export function PbChartPanel({ project }: { project: ProjectItem }) {
  const [result, setResult] = useState<ChartResult | null>(null)
  const [selectedLabel, setSelectedLabel] = useState<string>('')
  const [layers, setLayers] = useState<ChartLayers>({
    plannedLine: true,
    actualLine: true,
    dailyBars: true,
    pastPlans: false,
  })

  useEffect(() => {
    let ignore = false
    const label = selectedLabel || null
    Promise.all([
      fetchPbChart(project.testing_id, { label, includePastPlans: layers.pastPlans }),
      fetchProgressFiles(project.testing_id).catch(() => [] as FileProgressItem[]),
      fetchPlans(project.testing_id).catch(() => [] as PlanItem[]),
    ])
      .then(([data, files, plans]) => {
        if (!ignore) {
          setResult({
            testingId: project.testing_id,
            label,
            includePastPlans: layers.pastPlans,
            chart: data,
            files,
            plans,
            error: null,
          })
        }
      })
      .catch((err) => {
        if (!ignore) {
          setResult({
            testingId: project.testing_id,
            label,
            includePastPlans: layers.pastPlans,
            chart: null,
            files: [],
            plans: [],
            error: getErrorMessage(err),
          })
        }
      })
    return () => {
      ignore = true
    }
  }, [project.testing_id, selectedLabel, layers.pastPlans])

  const label = selectedLabel || null
  const isCurrentResult =
    result?.testingId === project.testing_id &&
    result.label === label &&
    result.includePastPlans === layers.pastPlans
  const chart = isCurrentResult ? result.chart : null
  const error = isCurrentResult ? result.error : null
  const files = isCurrentResult ? result.files : []
  const plans = isCurrentResult ? result.plans : []
  const labels = Array.from(
    new Set(
      [
        ...files.map((file) => file.label),
        ...plans.map((plan) => plan.label),
      ].filter((item): item is string => Boolean(item)),
    ),
  ).sort((a, b) => a.localeCompare(b))
  const loading = !isCurrentResult
  const rangeText = chart?.range
    ? `${formatDate(chart.range.from)} ～ ${formatDate(chart.range.to)}`
    : '-'
  const notices = chart ? buildChartNotices(chart) : []

  return (
    <section className="chart-section">
      <div className="chart-toolbar">
        <div>
          <h2>PB図</h2>
          <div className="chart-meta">表示期間: {rangeText}</div>
        </div>
        <div className="chart-controls">
          <label className="target-select">
            <span>表示対象</span>
            <select
              value={selectedLabel}
              disabled={loading && labels.length === 0}
              onChange={(event) => setSelectedLabel(event.target.value)}
            >
              <option value="">全テスト種別</option>
              {labels.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <ChartLayerControls layers={layers} onChange={setLayers} />
        </div>
      </div>

      {loading && <div className="chart-state">PB図を読み込み中...</div>}
      {error && <div className="chart-state error">PB図を取得できませんでした: {error}</div>}
      {!loading && !error && chart && chart.series.length === 0 && (
        <div className="chart-state">
          {selectedLabel
            ? `${selectedLabel} の計画または実績データがまだありません。`
            : '計画または実績データがまだありません。'}
        </div>
      )}
      {!loading && !error && chart && chart.series.length > 0 && (
        <>
          {notices.length > 0 && (
            <div className="chart-notices">
              {notices.map((notice) => (
                <span key={notice}>{notice}</span>
              ))}
            </div>
          )}
          <PbChart chart={chart} layers={layers} />
          <div className="chart-foot">
            実績最終更新: {formatDateTime(chart.actuals_updated_at)} / 実績対象件数:{' '}
            {chart.available_cases} / 計画項目数: {chart.planned_total_cases ?? '-'}
          </div>
        </>
      )}
    </section>
  )
}

function ChartLayerControls({
  layers,
  onChange,
}: {
  layers: ChartLayers
  onChange: (layers: ChartLayers) => void
}) {
  return (
    <div className="layer-controls">
      <label>
        <input
          type="checkbox"
          checked={layers.plannedLine}
          onChange={(event) => onChange({ ...layers, plannedLine: event.target.checked })}
        />
        計画線
      </label>
      <label>
        <input
          type="checkbox"
          checked={layers.actualLine}
          onChange={(event) => onChange({ ...layers, actualLine: event.target.checked })}
        />
        実績線
      </label>
      <label>
        <input
          type="checkbox"
          checked={layers.dailyBars}
          onChange={(event) => onChange({ ...layers, dailyBars: event.target.checked })}
        />
        日別消化
      </label>
      <label>
        <input
          type="checkbox"
          checked={layers.pastPlans}
          onChange={(event) => onChange({ ...layers, pastPlans: event.target.checked })}
        />
        過去計画
      </label>
    </div>
  )
}

function PbChart({ chart, layers }: { chart: PbChartResponse; layers: ChartLayers }) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const instanceRef = useRef<ECharts | null>(null)

  useEffect(() => {
    if (!containerRef.current) {
      return
    }
    const instance = echarts.init(containerRef.current)
    instanceRef.current = instance
    const resizeObserver = new ResizeObserver(() => instance.resize())
    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
      instance.dispose()
      instanceRef.current = null
    }
  }, [])

  useEffect(() => {
    instanceRef.current?.setOption(buildPbChartOption(chart, layers), true)
  }, [chart, layers])

  return <div className="pb-chart" ref={containerRef} />
}
