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
import {
  fetchPbChart,
  fetchOpenBugs,
  fetchPlans,
  fetchProgressDaily,
  fetchProgressFiles,
  syncAzureDevOpsBugs,
} from '../api/client'
import type {
  DailyProgressItem,
  FileProgressItem,
  OpenBugItem,
  PbChartResponse,
  PlanItem,
  ProjectItem,
} from '../api/types'
import { buildPbChartOption } from '../charts/pbChartOptions'
import type { ChartLayers } from '../types/ui'
import { Bug, ClipboardList } from 'lucide-react'
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
  daily: DailyProgressItem[]
  plans: PlanItem[]
  openBugs: OpenBugItem[]
  error: string | null
}

type ResultKey = 'Pass' | 'Fixed' | 'Fail' | 'Blocked' | 'Suspend' | 'N/A'

interface BreakdownRow {
  key: string
  file: string
  env: string
  total: number
  results: Record<ResultKey, number>
  notRun: number
  completed: number
  executed: number
  completedRate: number
  executedRate: number
}

const resultKeys: ResultKey[] = ['Pass', 'Fixed', 'Fail', 'Blocked', 'Suspend', 'N/A']

const resultHeaderClassNames: Record<ResultKey, string> = {
  Pass: 'pass',
  Fixed: 'fixed',
  Fail: 'fail',
  Blocked: 'blocked',
  Suspend: 'suspend',
  'N/A': 'na',
}

export function PbChartPanel({ project, onPlans }: { project: ProjectItem; onPlans?: () => void }) {
  const [result, setResult] = useState<ChartResult | null>(null)
  const [selectedLabel, setSelectedLabel] = useState<string>('')
  const [layers, setLayers] = useState<ChartLayers>({
    plannedLine: true,
    actualLine: true,
    dailyBars: true,
    pastPlans: false,
    bugs: true,
  })
  const [reloadKey, setReloadKey] = useState(0)
  const [bugSync, setBugSync] = useState<{ loading: boolean; message: string | null; error: string | null }>({
    loading: false,
    message: null,
    error: null,
  })

  const handleSyncBugs = () => {
    setBugSync({ loading: true, message: null, error: null })
    syncAzureDevOpsBugs(project.testing_id)
      .then((res) => {
        setBugSync({
          loading: false,
          message: `不具合 ${res.fetched} 件（未解消 ${res.open_count} / 見送り ${res.suspended_count} / 完了 ${res.resolved_count}）`,
          error: null,
        })
        setLayers((prev) => ({ ...prev, bugs: true }))
        setReloadKey((key) => key + 1)
      })
      .catch((err) => {
        setBugSync({ loading: false, message: null, error: getErrorMessage(err) })
      })
  }

  useEffect(() => {
    let ignore = false
    const label = selectedLabel || null
    Promise.all([
      fetchPbChart(project.testing_id, { label, includePastPlans: layers.pastPlans }),
      fetchProgressFiles(project.testing_id).catch(() => [] as FileProgressItem[]),
      fetchProgressDaily(project.testing_id).catch(() => [] as DailyProgressItem[]),
      fetchPlans(project.testing_id).catch(() => [] as PlanItem[]),
      fetchOpenBugs(project.testing_id).catch(() => [] as OpenBugItem[]),
    ])
      .then(([data, files, daily, plans, openBugs]) => {
        if (!ignore) {
          setResult({
            testingId: project.testing_id,
            label,
            includePastPlans: layers.pastPlans,
            chart: data,
            files,
            daily,
            plans,
            openBugs,
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
            daily: [],
            plans: [],
            openBugs: [],
            error: getErrorMessage(err),
          })
        }
      })
    return () => {
      ignore = true
    }
  }, [project.testing_id, selectedLabel, layers.pastPlans, reloadKey])

  const label = selectedLabel || null
  // 不具合グラフは表示対象が(全て)のときのみ表示する。
  const bugsAllowed = selectedLabel === ''
  const isCurrentResult =
    result?.testingId === project.testing_id &&
    result.label === label &&
    result.includePastPlans === layers.pastPlans
  const chart = isCurrentResult ? result.chart : null
  const error = isCurrentResult ? result.error : null
  const files = isCurrentResult ? result.files : []
  const daily = isCurrentResult ? result.daily : []
  const plans = isCurrentResult ? result.plans : []
  const openBugs = isCurrentResult ? result.openBugs : []
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
  const bugSummary = chart ? getBugSummary(chart) : null
  const usesTestResultBugs = project.bug_count_source === 'test_result'
  // 表示対象が(全て)以外のときは不具合レイヤーを強制的にOFFにして描画する。
  const effectiveLayers = bugsAllowed ? layers : { ...layers, bugs: false }

  return (
    <section className="chart-section">
      <div className="chart-controls">
        <label className="target-select">
          <span>表示対象</span>
          <select
            value={selectedLabel}
            disabled={loading && labels.length === 0}
            onChange={(event) => setSelectedLabel(event.target.value)}
          >
            <option value="">(全て)</option>
            {labels.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <span className="chart-period">表示期間: {rangeText}</span>
        <ChartLayerControls layers={layers} onChange={setLayers} bugsAllowed={bugsAllowed} />
      </div>

      <div className="bug-bar">
        {!usesTestResultBugs && (
          <button
            type="button"
            className="bug-sync-button"
            onClick={handleSyncBugs}
            disabled={bugSync.loading || !bugsAllowed}
          >
            <Bug className="bug-sync-icon" aria-hidden="true" />
            {bugSync.loading ? '取得中...' : '不具合数を取得'}
          </button>
        )}
        {bugSync.error ? (
          <span className="bug-meta error">取得失敗: {bugSync.error}</span>
        ) : !bugsAllowed ? null : bugSummary ? (
          <span className="bug-meta">
            不具合 <b>{bugSummary.total}</b> 件（{usesTestResultBugs ? 'Fail' : '未解消'}{' '}
            <b className="open">{bugSummary.open}</b> / {usesTestResultBugs ? 'Suspend' : '見送り'}{' '}
            <b className="suspended">{bugSummary.suspended}</b> / {usesTestResultBugs ? 'Fixed' : '完了'}{' '}
            <b className="resolved">{bugSummary.resolved}</b>）
            {chart?.bugs_updated_at
              ? `・${usesTestResultBugs ? '最終更新' : '最終取得'}: ${formatDateTime(chart.bugs_updated_at)}`
              : ''}
          </span>
        ) : (
          <span className="bug-meta">不具合データ未取得</span>
        )}
      </div>

      {loading && <div className="chart-state">PB図を読み込み中...</div>}
      {error && <div className="chart-state error">PB図を取得できませんでした: {error}</div>}
      {!loading && !error && chart && chart.series.length === 0 && (
        <div className="chart-state">
          <p>
            {selectedLabel
              ? `${selectedLabel} の計画または実績データがまだありません。`
              : '計画または実績データがまだありません。'}
          </p>
          {onPlans && (
            <button className="primary-button icon-text-button" type="button" onClick={onPlans}>
              <ClipboardList className="button-icon" aria-hidden="true" strokeWidth={2.2} />
              <span>テスト計画入力</span>
            </button>
          )}
        </div>
      )}
      {!loading && !error && chart && chart.series.length > 0 && (
        <div className="chart-wrap">
          <PbChart chart={chart} layers={effectiveLayers} />
        </div>
      )}
      {!loading && !error && (
        <ProgressBreakdown
          files={files}
          daily={daily}
          selectedLabel={label}
          openBugs={bugsAllowed ? openBugs : []}
          bugDataFetched={Boolean(bugsAllowed && (usesTestResultBugs || chart?.has_bugs))}
        />
      )}
    </section>
  )
}

function getBugSummary(
  chart: PbChartResponse,
): { open: number; suspended: number; resolved: number; total: number } | null {
  if (!chart.has_bugs) {
    return null
  }
  for (let i = chart.series.length - 1; i >= 0; i--) {
    const point = chart.series[i]
    if (point.bug_open != null || point.bug_suspended != null || point.bug_resolved != null) {
      const open = point.bug_open ?? 0
      const suspended = point.bug_suspended ?? 0
      const resolved = point.bug_resolved ?? 0
      return { open, suspended, resolved, total: open + suspended + resolved }
    }
  }
  return { open: 0, suspended: 0, resolved: 0, total: 0 }
}

function ChartLayerControls({
  layers,
  onChange,
  bugsAllowed,
}: {
  layers: ChartLayers
  onChange: (layers: ChartLayers) => void
  bugsAllowed: boolean
}) {
  return (
    <div className="layer-controls">
      <span className="layer-controls-label">表示:</span>
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
      <label
        className={bugsAllowed ? undefined : 'layer-disabled'}
        title={bugsAllowed ? undefined : '不具合グラフは表示対象が(全て)のときのみ表示できます'}
      >
        <input
          type="checkbox"
          checked={bugsAllowed && layers.bugs}
          disabled={!bugsAllowed}
          onChange={(event) => onChange({ ...layers, bugs: event.target.checked })}
        />
        不具合
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

function ProgressBreakdown({
  files,
  daily,
  selectedLabel,
  openBugs,
  bugDataFetched,
}: {
  files: FileProgressItem[]
  daily: DailyProgressItem[]
  selectedLabel: string | null
  openBugs: OpenBugItem[]
  bugDataFetched: boolean
}) {
  const rows = buildBreakdownRows(files, daily, selectedLabel)
  if (rows.length === 0 && !bugDataFetched && openBugs.length === 0) {
    return null
  }

  const total = rows.reduce<BreakdownRow>(
    (acc, row) => {
      acc.total += row.total
      acc.notRun += row.notRun
      acc.completed += row.completed
      acc.executed += row.executed
      for (const key of resultKeys) {
        acc.results[key] += row.results[key]
      }
      return acc
    },
    {
      key: 'total',
      file: 'Total',
      env: '',
      total: 0,
      results: emptyResultCounts(),
      notRun: 0,
      completed: 0,
      executed: 0,
      completedRate: 0,
      executedRate: 0,
    },
  )
  total.completedRate = toRate(total.completed, total.total)
  total.executedRate = toRate(total.executed, total.total)

  return (
    <div className="progress-breakdown">
      <section className="breakdown-block" aria-label="テスト結果合計">
        <h3>テスト結果合計</h3>
        <div className="breakdown-table-wrap">
          <table className="breakdown-table">
            <thead>
              <tr>
                <th>合計</th>
                {resultKeys.map((key) => (
                  <th key={key}>
                    <ResultHeader result={key} />
                  </th>
                ))}
                <th>未実施</th>
                <th>完了数</th>
                <th>消化数</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{total.total}</td>
                {resultKeys.map((key) => (
                  <td key={key}>{total.results[key]}</td>
                ))}
                <td>{total.notRun}</td>
                <td>{formatCountRate(total.completed, total.completedRate)}</td>
                <td>{formatCountRate(total.executed, total.executedRate)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="breakdown-block" aria-label="テスト別内訳">
        <h3>テスト別内訳</h3>
        {rows.length > 0 ? (
          <div className="breakdown-table-wrap">
            <table className="breakdown-table">
              <thead>
                <tr>
                  <th>種別</th>
                  <th>環境</th>
                  <th>合計</th>
                  {resultKeys.map((key) => (
                    <th key={key}>
                      <ResultHeader result={key} />
                    </th>
                  ))}
                  <th>未実施</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.key}>
                    <td className="breakdown-file-cell" title={row.file}>
                      {row.file}
                    </td>
                    <td>{row.env}</td>
                    <td>{row.total}</td>
                    {resultKeys.map((key) => (
                      <td key={key}>{row.results[key]}</td>
                    ))}
                    <td>{row.notRun}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="breakdown-empty">テスト別内訳データがありません。</div>
        )}
      </section>

      <OpenBugList bugs={openBugs} bugDataFetched={bugDataFetched} />
    </div>
  )
}

function OpenBugList({ bugs, bugDataFetched }: { bugs: OpenBugItem[]; bugDataFetched: boolean }) {
  return (
    <section className="breakdown-block" aria-label="未解決の不具合チケット一覧">
      <h3>未解決Bugチケット一覧</h3>
      {bugs.length > 0 ? (
        <div className="breakdown-table-wrap">
          <table className="breakdown-table open-bug-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Title</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {bugs.map((bug) => (
                <tr key={bug.work_item_id}>
                  <td className="open-bug-id-cell">
                    {bug.url ? (
                      <a href={bug.url} target="_blank" rel="noreferrer">
                        {bug.work_item_id}
                      </a>
                    ) : (
                      bug.work_item_id
                    )}
                  </td>
                  <td className="open-bug-title-cell" title={bug.title ?? ''}>
                    {bug.title || '-'}
                  </td>
                  <td className="open-bug-state-cell">{bug.state || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="breakdown-empty">
          {bugDataFetched ? '未解決の不具合チケットはありません' : '不具合データ未取得です'}
        </div>
      )}
    </section>
  )
}

function ResultHeader({ result }: { result: ResultKey }) {
  return (
    <span className={`result-header result-header-${resultHeaderClassNames[result]}`}>
      {result}
    </span>
  )
}

function buildBreakdownRows(
  files: FileProgressItem[],
  daily: DailyProgressItem[],
  selectedLabel: string | null,
): BreakdownRow[] {
  const matchingFiles = files.filter((file) => !selectedLabel || file.label === selectedLabel)
  const rows = new Map<string, BreakdownRow>()

  for (const file of matchingFiles) {
    const key = breakdownKey(file.file_name, file.label, file.environment)
    rows.set(key, {
      key,
      file: file.label || file.file_name,
      env: file.environment || '-',
      total: file.available_cases,
      results: emptyResultCounts(),
      notRun: Math.max(file.available_cases - file.executed, 0),
      completed: file.completed,
      executed: file.executed,
      completedRate: file.completed_rate,
      executedRate: file.executed_rate,
    })
  }

  for (const item of daily) {
    if (selectedLabel && item.label !== selectedLabel) {
      continue
    }
    const key = breakdownKey(item.file_name, item.label, item.environment)
    let row = rows.get(key)
    if (!row) {
      row = {
        key,
        file: item.label || item.file_name,
        env: item.environment || '-',
        total: 0,
        results: emptyResultCounts(),
        notRun: 0,
        completed: 0,
        executed: 0,
        completedRate: 0,
        executedRate: 0,
      }
      rows.set(key, row)
    }
    row.results.Pass += item.Pass
    row.results.Fixed += item.Fixed
    row.results.Fail += item.Fail
    row.results.Blocked += item.Blocked
    row.results.Suspend += item.Suspend
    row.results['N/A'] += item['N/A']
  }

  return [...rows.values()].sort((a, b) => {
    const fileCompare = a.file.localeCompare(b.file, 'ja')
    return fileCompare === 0 ? a.env.localeCompare(b.env, 'ja') : fileCompare
  })
}

function breakdownKey(fileName: string, label: string | null, environment: string | null) {
  return `${fileName}\u0000${label ?? ''}\u0000${environment ?? ''}`
}

function emptyResultCounts(): Record<ResultKey, number> {
  return {
    Pass: 0,
    Fixed: 0,
    Fail: 0,
    Blocked: 0,
    Suspend: 0,
    'N/A': 0,
  }
}

function toRate(count: number, total: number) {
  return total > 0 ? Math.round((count / total) * 10000) / 100 : 0
}

function formatCountRate(count: number, rate: number) {
  return `${count} (${rate.toFixed(1)}%)`
}
