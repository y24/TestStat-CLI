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
  fetchPlanLabels,
  fetchPlans,
  fetchProgressDaily,
  fetchProgressFiles,
  syncAzureDevOpsBugs,
  updateProject,
} from '../api/client'
import type {
  DailyProgressItem,
  FileProgressItem,
  OpenBugItem,
  BugStateColorSettings,
  BugStateColorSetting,
  PbChartSettings,
  PbChartPastPlan,
  PbChartResponse,
  PlanItem,
  PlanLabelItem,
  ProjectItem,
} from '../api/types'
import { buildPbChartOption } from '../charts/pbChartOptions'
import type { ChartLayers } from '../types/ui'
import { displayLabel } from '../utils/plans'
import { Bug, ClipboardList, FileSpreadsheet, Filter, TriangleAlert, X } from 'lucide-react'
import { enumerateDates, formatDateTime, formatDateTimeWithRelative } from '../utils/date'
import {
  getProgressStatusLevel,
  type ProgressStatusLevel,
  type ProgressStatusThresholds,
} from '../utils/statusThresholds'
import { getErrorMessage } from '../utils/errors'
import { getStoredSelectedLabels, setStoredSelectedLabels } from '../utils/uiStateStorage'

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
  labels: string[]
  includePastPlans: boolean
  chart: PbChartResponse | null
  files: FileProgressItem[]
  daily: DailyProgressItem[]
  plans: PlanItem[]
  planLabels: PlanLabelItem[]
  openBugs: OpenBugItem[]
  error: string | null
}

interface ChartData {
  charts: PbChartResponse[]
  files: FileProgressItem[]
  daily: DailyProgressItem[]
  plans: PlanItem[]
  planLabels: PlanLabelItem[]
  openBugs: OpenBugItem[]
}

// React Strict Mode re-runs effects in development. Share only requests that are
// currently in flight so the verification pass does not send the same API set twice.
const inFlightChartData = new Map<string, Promise<ChartData>>()

function fetchChartData(
  testingId: number,
  labels: string[],
  includePastPlans: boolean,
  reloadKey: number,
): Promise<ChartData> {
  const requestKey = JSON.stringify([testingId, labels, includePastPlans, reloadKey])
  const current = inFlightChartData.get(requestKey)
  if (current) {
    return current
  }

  const chartRequests =
    labels.length === 0
      ? [fetchPbChart(testingId, { label: null, includePastPlans })]
      : labels.map((label) => fetchPbChart(testingId, { label, includePastPlans }))
  const request = Promise.all([
    Promise.all(chartRequests),
    fetchProgressFiles(testingId).catch(() => [] as FileProgressItem[]),
    fetchProgressDaily(testingId).catch(() => [] as DailyProgressItem[]),
    fetchPlans(testingId).catch(() => [] as PlanItem[]),
    fetchPlanLabels(testingId).catch(() => [] as PlanLabelItem[]),
    fetchOpenBugs(testingId).catch(() => [] as OpenBugItem[]),
  ]).then(([charts, files, daily, plans, planLabels, openBugs]) => ({
    charts,
    files,
    daily,
    plans,
    planLabels,
    openBugs,
  }))

  inFlightChartData.set(requestKey, request)
  const clearRequest = () => {
    if (inFlightChartData.get(requestKey) === request) {
      inFlightChartData.delete(requestKey)
    }
  }
  void request.then(clearRequest, clearRequest)
  return request
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

interface CompletionSummary {
  availableCases: number
  completed: number
  completedRate: number
  actualVsPlanRate: number | null
  actualVsPlanDelayDays: number | null
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

const EMPTY_SELECTED_LABELS: string[] = []

interface DisplaySettings {
  pb_chart_range_source: 'plan_actual' | 'project_period'
  bug_axis_max: number | null
}

export function PbChartPanel({
  project,
  pbChartSettings,
  bugStateColorSettings,
  progressStatusThresholds,
  onPlans,
  onProjectUpdate,
  layerModalOpen,
  onLayerModalClose,
}: {
  project: ProjectItem
  pbChartSettings: PbChartSettings
  bugStateColorSettings: BugStateColorSettings
  progressStatusThresholds: ProgressStatusThresholds
  onPlans?: () => void
  onProjectUpdate?: (project: ProjectItem) => void
  layerModalOpen?: boolean
  onLayerModalClose?: () => void
}) {
  const [result, setResult] = useState<ChartResult | null>(null)
  const [targetSelection, setTargetSelection] = useState<{ testingId: number; labels: string[] }>(() => ({
    testingId: project.testing_id,
    labels: getStoredSelectedLabels(project.testing_id),
  }))
  const selectedLabels =
    targetSelection.testingId === project.testing_id ? targetSelection.labels : EMPTY_SELECTED_LABELS
  const setSelectedLabels = (labels: string[]) => {
    setStoredSelectedLabels(project.testing_id, labels)
    setTargetSelection({ testingId: project.testing_id, labels })
  }


  const [targetMenuOpen, setTargetMenuOpen] = useState(false)
  const [layers, setLayers] = useState<ChartLayers>({
    plannedLine: true,
    actualCompletedLine: true,
    actualExecutedLine: false,
    dailyBars: true,
    pastPlans: false,
    bugs: true,
    openBugLine: false,
    todayLine: false,
  })
  // 過去計画は plan_id 単位で非表示にできる。デフォルトは全て表示（=空集合）。
  const [hiddenPastPlanIds, setHiddenPastPlanIds] = useState<Set<number>>(() => new Set())
  const [reloadKey, setReloadKey] = useState(0)
  const [bugSync, setBugSync] = useState<{ loading: boolean; message: string | null; error: string | null }>({
    loading: false,
    message: null,
    error: null,
  })
  const [displaySettings, setDisplaySettings] = useState<DisplaySettings>({
    pb_chart_range_source: project.pb_chart_range_source,
    bug_axis_max: project.bug_axis_max,
  })

  useEffect(() => {
    setDisplaySettings({
      pb_chart_range_source: project.pb_chart_range_source,
      bug_axis_max: project.bug_axis_max,
    })
  }, [project.testing_id, project.pb_chart_range_source, project.bug_axis_max])

  const handleLayerModalClose = (changedSettings?: DisplaySettings) => {
    onLayerModalClose?.()
    if (changedSettings) {
      updateProject(project.testing_id, changedSettings)
        .then((updated) => {
          onProjectUpdate?.(updated)
          setReloadKey((key) => key + 1)
        })
        .catch(() => {})
    }
  }

  const handleSyncBugs = () => {
    setBugSync({ loading: true, message: null, error: null })
    syncAzureDevOpsBugs(project.testing_id)
      .then((res) => {
        setBugSync({
          loading: false,
          message: `課題 ${res.fetched} 件（未解消 ${res.open_count} / 見送り ${res.suspended_count} / 完了 ${res.resolved_count}）`,
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
    const labels = [...selectedLabels].sort()
    fetchChartData(project.testing_id, labels, layers.pastPlans, reloadKey)
      .then(({ charts, files, daily, plans, planLabels, openBugs }) => {
        if (!ignore) {
          setResult({
            testingId: project.testing_id,
            labels,
            includePastPlans: layers.pastPlans,
            chart: labels.length <= 1 ? charts[0] : mergePbCharts(charts, labels, files),
            files,
            daily,
            plans,
            planLabels,
            openBugs,
            error: null,
          })
        }
      })
      .catch((err) => {
        if (!ignore) {
          setResult({
            testingId: project.testing_id,
            labels,
            includePastPlans: layers.pastPlans,
            chart: null,
            files: [],
            daily: [],
            plans: [],
            planLabels: [],
            openBugs: [],
            error: getErrorMessage(err),
          })
        }
      })
    return () => {
      ignore = true
    }
  }, [project.testing_id, selectedLabels, layers.pastPlans, reloadKey])

  const selectedLabelSet = new Set(selectedLabels)
  const usesTestResultBugs = project.bug_count_source === 'test_result'
  // テスト結果ソースは label 別に不具合を保持しているため、表示対象がテスト別でも描画できる。
  // Azure DevOps ソースはチケットがテストに紐付かないため(全て)のときのみ表示する。
  const bugsAllowed = usesTestResultBugs || selectedLabels.length === 0
  const isCurrentResult =
    result?.testingId === project.testing_id &&
    labelsKey(result.labels) === labelsKey(selectedLabels) &&
    result.includePastPlans === layers.pastPlans
  const chart = isCurrentResult ? result.chart : null
  const error = isCurrentResult ? result.error : null
  const files = isCurrentResult ? result.files : []
  const daily = isCurrentResult ? result.daily : []
  const plans = isCurrentResult ? result.plans : []
  const planLabels = isCurrentResult ? result.planLabels : []
  const disabledLabels = new Set(planLabels.filter((item) => item.is_disabled).map((item) => item.label))
  const visibleFiles = files.filter((file) => !file.label || !disabledLabels.has(file.label))
  const visibleDaily = daily.filter((item) => !item.label || !disabledLabels.has(item.label))
  const visiblePlans = plans.filter((plan) => !plan.label || !disabledLabels.has(plan.label))
  const openBugs = isCurrentResult ? result.openBugs : []
  const labelOrder = new Map(planLabels.map((item, index) => [item.label, index]))
  const compareLabels = (left: string, right: string) => {
    const leftOrder = labelOrder.get(left)
    const rightOrder = labelOrder.get(right)
    if (leftOrder !== undefined || rightOrder !== undefined) {
      return (leftOrder ?? Number.MAX_SAFE_INTEGER) - (rightOrder ?? Number.MAX_SAFE_INTEGER)
    }
    return left.localeCompare(right, 'ja')
  }
  const labels = Array.from(
    new Set(
      [
        ...visibleFiles.map((file) => file.label),
        ...visiblePlans.map((plan) => plan.label),
      ].filter((item): item is string => Boolean(item)),
    ),
  ).sort(compareLabels)
  const loading = !isCurrentResult
  const bugSummary = chart ? getBugSummary(chart) : null
  // 不具合レイヤーが許可されない表示対象では強制的にOFFにして描画する。
  const effectiveLayers = bugsAllowed ? layers : { ...layers, bugs: false, openBugLine: false }
  const completionSummary = chart ? buildCompletionSummary(chart, visibleFiles, selectedLabels) : null
  const planStatusLevel = getProgressStatusLevel(completionSummary?.actualVsPlanRate, progressStatusThresholds)
  // Blocked件数はプロジェクト全体（label横断）の Blocked 合計。テスト結果合計の Blocked と同じ集計。
  const blockedCount = visibleDaily
    .filter((item) => selectedLabels.length === 0 || (item.label != null && selectedLabelSet.has(item.label)))
    .reduce((sum, item) => sum + item.Blocked, 0)
  // 未解決チケットは「未解決チケット一覧」と同じ母数（見送りを除く未解決バグ）。
  const bugDataFetched = usesTestResultBugs || Boolean(chart?.has_bugs)
  const openTicketCount = openBugs.filter((bug) => !bug.is_suspended).length

  return (
    <section className="chart-section">
      <section className="summary-grid">
        <StatusTile label="完了率(対全体)" value={formatCompletionSummary(completionSummary)} />
        <StatusTile
          label="完了率(対計画)"
          value={formatRate(completionSummary?.actualVsPlanRate)}
          statusLevel={planStatusLevel}
          delayDays={completionSummary?.actualVsPlanDelayDays}
        />
        <StatusTile label="Blocked件数" value={loading ? '-' : String(blockedCount)} />
        <StatusTile
          label="未解決チケット件数"
          value={loading || !bugDataFetched ? '-' : String(openTicketCount)}
        />
      </section>

      <div className="chart-controls">
        <TargetMultiSelect
          labels={labels}
          selectedLabels={selectedLabels}
          disabled={loading && labels.length === 0}
          open={targetMenuOpen}
          onOpenChange={setTargetMenuOpen}
          onChange={setSelectedLabels}
        />
        <span className="chart-period">
          最終更新: {formatDateTimeWithRelative(project.actuals_updated_at)}
        </span>
        {selectedLabels.length > 0 && (
          <button
            type="button"
            className="target-clear-button"
            onClick={() => {
              setSelectedLabels([])
              setTargetMenuOpen(false)
            }}
          >
            <X className="target-clear-icon" aria-hidden="true" />
            <span>解除</span>
          </button>
        )}
      </div>

      {chart?.plan_case_mismatch && chart.planned_total_cases != null && chart.actual_plan_comparable_cases > 0 && (
        <div className="plan-mismatch-alert" role="status">
          <TriangleAlert className="plan-mismatch-alert-icon" aria-hidden="true" />
          <span>
            計画と実績の項目数が一致していません。計画 {chart.planned_total_cases} / 実績 {chart.actual_plan_comparable_cases}
          </span>
        </div>
      )}

      {chart && chart.undated_result_cases > 0 && (
        <div className="plan-mismatch-alert" role="status">
          <TriangleAlert className="plan-mismatch-alert-icon" aria-hidden="true" />
          <span>{chart.undated_result_cases}件の日付なしデータが含まれています。</span>
        </div>
      )}
      <div className="bug-bar">
        {!usesTestResultBugs && (
          <button
            type="button"
            className="bug-sync-button"
            onClick={handleSyncBugs}
            disabled={bugSync.loading || !bugsAllowed || project.archived}
          >
            <Bug className="bug-sync-icon" aria-hidden="true" />
            {bugSync.loading ? '取得中...' : 'チケットを取得'}
          </button>
        )}
        {bugSync.error ? (
          <span className="bug-meta error">取得失敗: {bugSync.error}</span>
        ) : !bugsAllowed ? null : bugSummary ? (
          <span className="bug-meta">
            課題 <b>{bugSummary.total}</b> 件（{usesTestResultBugs ? 'Fail' : '未解消'}{' '}
            <b className="open">{bugSummary.open}</b> / {usesTestResultBugs ? 'Suspend' : '見送り'}{' '}
            <b className="suspended">{bugSummary.suspended}</b> / {usesTestResultBugs ? 'Fixed' : '完了'}{' '}
            <b className="resolved">{bugSummary.resolved}</b>）
            {chart?.bugs_updated_at
              ? `・${usesTestResultBugs ? '最終更新' : '最終取得'}: ${formatDateTime(chart.bugs_updated_at)}`
              : ''}
          </span>
        ) : (
          <span className="bug-meta">課題データ未取得</span>
        )}
      </div>

      {loading && <div className="chart-state">PB図を読み込み中...</div>}
      {error && <div className="chart-state error">PB図を取得できませんでした: {error}</div>}
      {!loading && !error && chart && chart.series.length === 0 && (
        <div className="chart-state">
          <p>
            {selectedLabels.length > 0
              ? `${formatSelectedTarget(selectedLabels)} の計画または実績データがまだありません。`
              : '計画または実績データがまだありません。'}
          </p>
          {onPlans && (
            <button className="primary-button icon-text-button" type="button" onClick={onPlans}>
              <ClipboardList className="button-icon" aria-hidden="true" strokeWidth={2.2} />
              <span>テスト計画・管理</span>
            </button>
          )}
        </div>
      )}
      {!loading && !error && chart && chart.series.length > 0 && (
        <div className="chart-wrap">
          <PbChart
            chart={chart}
            layers={effectiveLayers}
            bugAxisMax={chart.bug_axis_max ?? pbChartSettings.bug_axis_max}
            hiddenPastPlanIds={hiddenPastPlanIds}
          />
        </div>
      )}
      {!loading && !error && (
        <ProgressBreakdown
          files={visibleFiles}
          daily={visibleDaily}
          selectedLabels={selectedLabels}
          openBugs={bugsAllowed ? openBugs : []}
          bugDataFetched={Boolean(bugsAllowed && (usesTestResultBugs || chart?.has_bugs))}
          bugStateColors={bugStateColorSettings.items}
          labelOrder={labelOrder}
          planLabels={planLabels}
        />
      )}
      {layerModalOpen && (
        <ChartLayerModal
          layers={layers}
          bugsAllowed={bugsAllowed}
          onChange={setLayers}
          onClose={handleLayerModalClose}
          displaySettings={displaySettings}
          pastPlans={chart?.past_plans ?? []}
          hiddenPastPlanIds={hiddenPastPlanIds}
          onHiddenPastPlanIdsChange={setHiddenPastPlanIds}
        />
      )}
    </section>
  )
}

function TargetMultiSelect({
  labels,
  selectedLabels,
  disabled,
  open,
  onOpenChange,
  onChange,
}: {
  labels: string[]
  selectedLabels: string[]
  disabled: boolean
  open: boolean
  onOpenChange: (open: boolean) => void
  onChange: (labels: string[]) => void
}) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [pending, setPending] = useState<string[]>(selectedLabels)
  const pendingSet = new Set(pending)

  useEffect(() => {
    if (open) {
      setPending(selectedLabels)
    }
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!open) {
      return
    }

    const handlePointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        onOpenChange(false)
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [open, onOpenChange])

  const toggleLabel = (label: string) => {
    if (pendingSet.has(label)) {
      setPending(pending.filter((item) => item !== label))
      return
    }
    setPending([...pending, label])
  }

  const apply = () => {
    onChange(pending)
    onOpenChange(false)
  }

  return (
    <div className="target-select target-multi-select" ref={containerRef}>
      <span className="target-select-label">
        <Filter className="target-select-icon" aria-hidden="true" />
        表示対象
      </span>
      <button
        type="button"
        className="target-multi-button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => onOpenChange(!open)}
      >
        <span className="target-multi-button-text">{formatSelectedTarget(selectedLabels)}</span>
        <span className="target-multi-caret" aria-hidden="true" />
      </button>
      {open && (
        <div className="target-multi-menu" role="listbox" aria-multiselectable="true">
          <button
            type="button"
            className={pending.length === 0 ? 'target-multi-option selected' : 'target-multi-option'}
            role="option"
            aria-selected={pending.length === 0}
            onClick={() => setPending([])}
          >
            <input type="checkbox" tabIndex={-1} readOnly checked={pending.length === 0} />
            <span>(全て)</span>
          </button>
          {labels.map((label) => (
            <button
              key={label}
              type="button"
              className={pendingSet.has(label) ? 'target-multi-option selected' : 'target-multi-option'}
              role="option"
              aria-selected={pendingSet.has(label)}
              onClick={() => toggleLabel(label)}
            >
              <input type="checkbox" tabIndex={-1} readOnly checked={pendingSet.has(label)} />
              <span>{label}</span>
            </button>
          ))}
          {labels.length === 0 && <div className="target-multi-empty">選択できるテスト種別がありません</div>}
          <div className="target-multi-footer">
            <button type="button" className="target-multi-apply" onClick={apply}>
              適用
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function labelsKey(labels: string[]) {
  return [...labels].sort().join('\u0000')
}

function PastPlanMultiSelect({
  pastPlans,
  hiddenPastPlanIds,
  onHiddenChange,
}: {
  pastPlans: PbChartPastPlan[]
  hiddenPastPlanIds: Set<number>
  onHiddenChange: (next: Set<number>) => void
}) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [open, setOpen] = useState(false)
  const [pendingHidden, setPendingHidden] = useState<Set<number>>(new Set(hiddenPastPlanIds))
  const sorted = sortPastPlans(pastPlans)
  const pendingVisibleCount = sorted.filter((plan) => !pendingHidden.has(plan.plan_id)).length
  const pendingAllVisible = pendingVisibleCount === sorted.length
  const committedVisibleCount = sorted.filter((plan) => !hiddenPastPlanIds.has(plan.plan_id)).length
  const committedAllVisible = committedVisibleCount === sorted.length

  useEffect(() => {
    if (open) {
      setPendingHidden(new Set(hiddenPastPlanIds))
    }
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!open) {
      return
    }
    const handlePointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [open])

  const toggle = (planId: number) => {
    const next = new Set(pendingHidden)
    if (next.has(planId)) {
      next.delete(planId)
    } else {
      next.add(planId)
    }
    setPendingHidden(next)
  }

  const apply = () => {
    onHiddenChange(pendingHidden)
    setOpen(false)
  }

  const buttonText = committedAllVisible
    ? `全て (${sorted.length}件)`
    : `${committedVisibleCount} / ${sorted.length}件 表示`

  return (
    <div className="target-multi-select past-plan-multi-select" ref={containerRef}>
      <span className="past-plan-select-label">表示する版</span>
      <button
        type="button"
        className="target-multi-button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <span className="target-multi-button-text">{buttonText}</span>
        <span className="target-multi-caret" aria-hidden="true" />
      </button>
      {open && (
        <div className="target-multi-menu" role="listbox" aria-multiselectable="true">
          <button
            type="button"
            className={pendingAllVisible ? 'target-multi-option selected' : 'target-multi-option'}
            role="option"
            aria-selected={pendingAllVisible}
            onClick={() => setPendingHidden(new Set())}
          >
            <input type="checkbox" tabIndex={-1} readOnly checked={pendingAllVisible} />
            <span>(全て)</span>
          </button>
          {sorted.map((plan) => {
            const checked = !pendingHidden.has(plan.plan_id)
            return (
              <button
                key={plan.plan_id}
                type="button"
                className={checked ? 'target-multi-option selected' : 'target-multi-option'}
                role="option"
                aria-selected={checked}
                onClick={() => toggle(plan.plan_id)}
              >
                <input type="checkbox" tabIndex={-1} readOnly checked={checked} />
                <span>
                  {displayLabel(plan.label)} v{plan.version}
                </span>
              </button>
            )
          })}
          <div className="target-multi-footer">
            <button type="button" className="target-multi-apply" onClick={apply}>
              適用
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// 過去計画チェックボックスの並び順: label 昇順 → version 降順（新しい版を上に）。
function sortPastPlans(pastPlans: PbChartPastPlan[]) {
  return [...pastPlans].sort((left, right) => {
    const labelCompare = displayLabel(left.label).localeCompare(displayLabel(right.label), 'ja')
    return labelCompare !== 0 ? labelCompare : right.version - left.version
  })
}

function formatSelectedTarget(labels: string[]) {
  if (labels.length === 0) {
    return '(全て)'
  }
  if (labels.length <= 2) {
    return labels.join(', ')
  }
  return `${labels[0]}, ${labels[1]} 他${labels.length - 2}件`
}

function StatusTile({
  label,
  value,
  statusLevel,
  delayDays,
}: {
  label: string
  value: string
  statusLevel?: ProgressStatusLevel
  delayDays?: number | null
}) {
  return (
    <div className="status-tile">
      <span>{label}</span>
      <strong className={statusLevel ? 'status-value with-indicator' : 'status-value'}>
        {statusLevel && (
          <span
            className={`plan-status-indicator ${statusLevel}`}
            aria-label={getProgressStatusLabel(statusLevel)}
            title={getProgressStatusLabel(statusLevel)}
          >
            ●
          </span>
        )}
        <span>{value}</span>
        {delayDays != null && delayDays > 0 && <span className="status-delay">({delayDays.toFixed(1)}日遅延)</span>}
      </strong>
    </div>
  )
}

function getProgressStatusLabel(level: ProgressStatusLevel) {
  if (level === 'normal') {
    return '正常'
  }
  if (level === 'caution') {
    return '注意'
  }
  if (level === 'warning') {
    return '警告'
  }
  return '状態なし'
}

function formatRate(value: number | null | undefined) {
  if (value == null) {
    return '-'
  }
  return `${value.toFixed(1)}%`
}

function buildCompletionSummary(
  chart: PbChartResponse,
  files: FileProgressItem[],
  selectedLabels: string[],
): CompletionSummary {
  const selectedLabelSet = new Set(selectedLabels)
  const matchingFiles = files.filter(
    (file) => selectedLabels.length === 0 || (file.label != null && selectedLabelSet.has(file.label)),
  )
  const completed = matchingFiles.reduce((sum, file) => sum + file.completed, 0)
  return {
    availableCases: chart.actual_total_cases ?? chart.available_cases,
    completed,
    completedRate: toRate(completed, chart.actual_total_cases ?? chart.available_cases),
    actualVsPlanRate: computeActualVsPlanRate(chart),
    actualVsPlanDelayDays: computeActualVsPlanDelayDays(chart),
  }
}

function computeActualVsPlanRate(chart: PbChartResponse) {
  const planned = chart.planned_completed_to_latest_actual ?? 0
  if (planned <= 0) {
    return null
  }
  return Math.round(((chart.actual_executed_to_latest ?? 0) / planned) * 10000) / 100
}

function computeActualVsPlanDelayDays(chart: PbChartResponse) {
  const actual = chart.actual_executed_to_latest ?? 0
  const planned = chart.planned_completed_to_latest_actual ?? 0
  if (planned <= 0 || actual >= planned) {
    return 0
  }
  const latestActualPoint = [...chart.series]
    .reverse()
    .find((point) => point.actual_remaining != null || point.actual_completed_daily != null)
  if (!latestActualPoint) {
    return null
  }

  let cumulative = 0
  for (const point of chart.series) {
    const plannedDaily = point.planned_completed_daily ?? 0
    if (plannedDaily <= 0) {
      continue
    }
    if (actual <= cumulative + plannedDaily) {
      const fraction = Math.max(0, (actual - cumulative) / plannedDaily)
      const plannedPosition = dateToDayNumber(point.date) + fraction
      const actualPosition = dateToDayNumber(latestActualPoint.date) + 1
      return Math.round(Math.max(0, actualPosition - plannedPosition) * 10) / 10
    }
    cumulative += plannedDaily
  }
  return null
}

function dateToDayNumber(date: string) {
  const [year, month, day] = date.split('-').map(Number)
  return Date.UTC(year, month - 1, day) / 86400000
}
function formatCompletionSummary(summary: CompletionSummary | null) {
  if (!summary) {
    return '-'
  }
  return `${summary.completedRate.toFixed(1)}% (${summary.completed}/${summary.availableCases})`
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

function mergePbCharts(charts: PbChartResponse[], labels: string[], files: FileProgressItem[]): PbChartResponse {
  const base = charts[0]
  const fromDates = charts.map((chart) => chart.range?.from).filter((date): date is string => Boolean(date))
  const toDates = charts.map((chart) => chart.range?.to).filter((date): date is string => Boolean(date))
  const rangeFrom = fromDates.length > 0 ? fromDates.sort()[0] : null
  const rangeTo = toDates.length > 0 ? toDates.sort()[toDates.length - 1] : null
  const dates =
    rangeFrom != null && rangeTo != null
      ? enumerateDates(rangeFrom, rangeTo)
      : [...new Set(charts.flatMap((chart) => chart.series.map((point) => point.date)))].sort()
  const selectedLabelSet = new Set(labels)
  const matchingFiles = files.filter((file) => file.label != null && selectedLabelSet.has(file.label))
  const availableSum = matchingFiles.reduce((sum, file) => sum + file.available_cases, 0)
  const actualNaSum = matchingFiles.reduce((sum, file) => sum + (file.result_na ?? 0), 0)
  const actualPlanComparableSum = availableSum
  const plannedTotals = charts.map((chart) => chart.planned_total_cases)
  const plannedTotalSum = plannedTotals.every((value) => value == null)
    ? null
    : plannedTotals.reduce<number>((sum, value) => sum + (value ?? 0), 0)
  const plannedDates = charts.flatMap((chart) =>
    chart.series
      .filter((point) => point.planned_remaining != null)
      .map((point) => point.date),
  )
  const globalFirstPlannedDate = plannedDates.length > 0 ? plannedDates.sort()[0] : null
  const globalLastPlannedDate = plannedDates.length > 0 ? plannedDates[plannedDates.length - 1] : null
  const pointMaps = charts.map((chart) => new Map(chart.series.map((point) => [point.date, point])))
  const bugPointSeries = charts.map((chart) =>
    chart.series.filter(
      (point) => point.bug_open != null || point.bug_suspended != null || point.bug_resolved != null,
    ),
  )
  const actualDailyDates = charts.flatMap((chart) =>
    chart.series
      .filter((point) => point.actual_completed_daily != null)
      .map((point) => point.date),
  )
  const initialActualDates = charts.flatMap((chart) =>
    chart.series
      .filter((point) => point.actual_remaining != null)
      .map((point) => point.date),
  )
  const globalLastActualDate =
    actualDailyDates.length > 0
      ? actualDailyDates.sort()[actualDailyDates.length - 1]
      : initialActualDates.length > 0
        ? initialActualDates.sort()[initialActualDates.length - 1]
        : null
  let cumulativePlanned = 0
  const series = dates.map((date) => {
    const points = pointMaps.map((pointMap) => pointMap.get(date))
    const withinPlannedRange =
      globalFirstPlannedDate != null && globalLastPlannedDate != null &&
      date >= globalFirstPlannedDate && date <= globalLastPlannedDate
    const plannedCompletedDaily = withinPlannedRange
      ? points.reduce((sum, point) => sum + (point?.planned_completed_daily ?? 0), 0)
      : null
    const actualCompletedDaily = sumNullable(points.map((point) => point?.actual_completed_daily))
    cumulativePlanned += plannedCompletedDaily ?? 0
    return {
      date,
      planned_remaining: plannedTotalSum != null && withinPlannedRange ? plannedTotalSum - cumulativePlanned : null,
      actual_remaining:
        globalLastActualDate != null && date <= globalLastActualDate
          ? sumNullable(
              charts.map((chart) =>
                getActualRemainingAt(
                  chart.series,
                  date,
                  chart.actual_total_cases ?? chart.available_cases,
                ),
              ),
            )
          : null,
      actual_executed_remaining:
        globalLastActualDate != null && date <= globalLastActualDate
          ? sumNullable(
              charts.map((chart) =>
                getActualRemainingAt(
                  chart.series,
                  date,
                  chart.actual_total_cases ?? chart.available_cases,
                  "actual_executed_remaining",
                ),
              ),
            )
          : null,
      planned_completed_daily: plannedCompletedDaily,
      actual_completed_daily: actualCompletedDaily,
      bug_open: sumNullable(bugPointSeries.map((points) => getCumulativeFieldAt(points, date, 'bug_open'))),
      bug_suspended: sumNullable(
        bugPointSeries.map((points) => getCumulativeFieldAt(points, date, 'bug_suspended')),
      ),
      bug_resolved: sumNullable(
        bugPointSeries.map((points) => getCumulativeFieldAt(points, date, 'bug_resolved')),
      ),
    }
  })
  const actualsUpdatedAt = maxDateTime(charts.map((chart) => chart.actuals_updated_at))
  const bugsUpdatedAt = maxDateTime(charts.map((chart) => chart.bugs_updated_at))

  return {
    testing_id: base.testing_id,
    label: labels.join(', '),
    bug_count_source: base.bug_count_source,
    range: rangeFrom != null && rangeTo != null ? { from: rangeFrom, to: rangeTo } : null,
    actuals_updated_at: actualsUpdatedAt,
    available_cases: availableSum,
    actual_total_cases: charts.reduce((sum, chart) => sum + (chart.actual_total_cases ?? chart.available_cases), 0),
    actual_na_cases: actualNaSum,
    undated_result_cases: charts.reduce((sum, chart) => sum + (chart.undated_result_cases ?? 0), 0),
    actual_plan_comparable_cases: actualPlanComparableSum,
    planned_total_cases: plannedTotalSum,
    plan_case_mismatch: charts.some((chart) => chart.plan_case_mismatch),
    actual_executed_to_latest: charts.reduce(
      (sum, chart) => sum + (chart.actual_executed_to_latest ?? 0),
      0,
    ),
    planned_completed_to_latest_actual: charts.reduce(
      (sum, chart) => sum + (chart.planned_completed_to_latest_actual ?? 0),
      0,
    ),
    series,
    past_plans: charts.flatMap((chart) => chart.past_plans),
    has_bugs: charts.some((chart) => chart.has_bugs),
    bugs_updated_at: bugsUpdatedAt,
    bug_axis_max: Math.max(...charts.map((chart) => chart.bug_axis_max)),
  }
}

function getActualRemainingAt(
  points: PbChartResponse['series'],
  date: string,
  initialRemaining: number,
  field: 'actual_remaining' | 'actual_executed_remaining' = 'actual_remaining',
): number | null {
  let latest: number | null = initialRemaining
  for (const point of points) {
    if (point.date > date) {
      break
    }
    if (point[field] != null) {
      latest = point[field]
    }
  }
  return latest
}
function getCumulativeFieldAt(
  points: PbChartResponse['series'],
  date: string,
  field: 'bug_open' | 'bug_suspended' | 'bug_resolved',
) {
  if (points.length === 0) {
    return null
  }
  let value = 0
  for (const point of points) {
    if (point.date > date) {
      break
    }
    value = point[field] ?? value
  }
  return value
}

function sumNullable(values: Array<number | null | undefined>) {
  const numbers = values.filter((value): value is number => value != null)
  return numbers.length > 0 ? numbers.reduce((sum, value) => sum + value, 0) : null
}

function maxDateTime(values: Array<string | null>) {
  const dates = values.filter((value): value is string => Boolean(value))
  return dates.length > 0 ? dates.sort()[dates.length - 1] : null
}

function ChartLayerModal({
  layers,
  onChange,
  bugsAllowed,
  onClose,
  displaySettings,
  pastPlans,
  hiddenPastPlanIds,
  onHiddenPastPlanIdsChange,
}: {
  layers: ChartLayers
  onChange: (layers: ChartLayers) => void
  bugsAllowed: boolean
  onClose: (changedSettings?: DisplaySettings) => void
  displaySettings: DisplaySettings
  pastPlans: PbChartPastPlan[]
  hiddenPastPlanIds: Set<number>
  onHiddenPastPlanIdsChange: (next: Set<number>) => void
}) {
  const [pbRangeSource, setPbRangeSource] = useState(displaySettings.pb_chart_range_source)
  const [bugAxisMaxStr, setBugAxisMaxStr] = useState(
    displaySettings.bug_axis_max == null ? '' : String(displaySettings.bug_axis_max),
  )

  const handleClose = () => {
    const bugAxisMax = bugAxisMaxStr.trim() ? Number(bugAxisMaxStr) : null
    const validBugAxisMax =
      bugAxisMax == null || (Number.isInteger(bugAxisMax) && bugAxisMax >= 1 && bugAxisMax <= 100000)
        ? bugAxisMax
        : displaySettings.bug_axis_max
    const changed =
      pbRangeSource !== displaySettings.pb_chart_range_source ||
      validBugAxisMax !== displaySettings.bug_axis_max
    onClose(changed ? { pb_chart_range_source: pbRangeSource, bug_axis_max: validBugAxisMax } : undefined)
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={handleClose}>
      <div
        className="modal-panel layer-settings-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="layer-settings-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-header">
          <h2 id="layer-settings-title">表示設定</h2>
          <button className="icon-button modal-close" type="button" onClick={handleClose} aria-label="閉じる">
            ×
          </button>
        </div>
        <div className="layer-settings-body">
          <div className="layer-settings-section">
            <div className="layer-settings-section-title">表示レイヤー</div>
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
                checked={layers.actualCompletedLine}
                onChange={(event) => onChange({ ...layers, actualCompletedLine: event.target.checked })}
              />
              実績線（完了数）
            </label>
            <label>
              <input
                type="checkbox"
                checked={layers.actualExecutedLine}
                onChange={(event) => onChange({ ...layers, actualExecutedLine: event.target.checked })}
              />
              実績線（消化数）
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
            {layers.pastPlans && pastPlans.length > 0 && (
              <PastPlanMultiSelect
                pastPlans={pastPlans}
                hiddenPastPlanIds={hiddenPastPlanIds}
                onHiddenChange={onHiddenPastPlanIdsChange}
              />
            )}
            <label
              className={bugsAllowed ? undefined : 'layer-disabled'}
              title={bugsAllowed ? undefined : '課題数グラフは表示対象が(全て)のときのみ表示できます'}
            >
              <input
                type="checkbox"
                checked={bugsAllowed && layers.bugs}
                disabled={!bugsAllowed}
                onChange={(event) => onChange({ ...layers, bugs: event.target.checked })}
              />
              課題数
            </label>
            <label
              className={bugsAllowed ? undefined : 'layer-disabled'}
              title={bugsAllowed ? undefined : '未解決課題件数は表示対象が(全て)のときのみ表示できます'}
            >
              <input
                type="checkbox"
                checked={bugsAllowed && layers.openBugLine}
                disabled={!bugsAllowed}
                onChange={(event) => onChange({ ...layers, openBugLine: event.target.checked })}
              />
              未解決課題件数
            </label>
            <label>
              <input
                type="checkbox"
                checked={layers.todayLine}
                onChange={(event) => onChange({ ...layers, todayLine: event.target.checked })}
              />
              今日の日付
            </label>
          </div>
          <div className="layer-settings-section">
            <div className="layer-settings-section-title">軸・範囲</div>
            <label className="layer-settings-field">
              <span>PB図の表示範囲</span>
              <select
                value={pbRangeSource}
                onChange={(event) =>
                  setPbRangeSource(event.target.value as DisplaySettings['pb_chart_range_source'])
                }
              >
                <option value="plan_actual">計画線・実績線の範囲</option>
                <option value="project_period">テスト全体期間の開始日・終了日</option>
              </select>
            </label>
            <label className="layer-settings-field">
              <span>課題件数の縦軸上限</span>
              <input
                type="number"
                min="1"
                max="100000"
                step="1"
                value={bugAxisMaxStr}
                placeholder="未設定の場合はシステム全体設定"
                onChange={(event) => setBugAxisMaxStr(event.target.value)}
              />
            </label>
          </div>
        </div>
        <div className="modal-actions">
          <button className="secondary-button" type="button" onClick={handleClose}>
            閉じる
          </button>
        </div>
      </div>
    </div>
  )
}

function PbChart({
  chart,
  layers,
  bugAxisMax,
  hiddenPastPlanIds,
}: {
  chart: PbChartResponse
  layers: ChartLayers
  bugAxisMax: number
  hiddenPastPlanIds: Set<number>
}) {
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
    instanceRef.current?.setOption(buildPbChartOption(chart, layers, bugAxisMax, hiddenPastPlanIds), true)
  }, [chart, layers, bugAxisMax, hiddenPastPlanIds])

  return <div className="pb-chart" ref={containerRef} />
}

function ProgressBreakdown({
  files,
  daily,
  selectedLabels,
  openBugs,
  bugDataFetched,
  bugStateColors,
  labelOrder,
  planLabels,
}: {
  files: FileProgressItem[]
  daily: DailyProgressItem[]
  selectedLabels: string[]
  openBugs: OpenBugItem[]
  bugDataFetched: boolean
  bugStateColors: BugStateColorSetting[]
  labelOrder: Map<string, number>
  planLabels: PlanLabelItem[]
}) {
  const rows = buildBreakdownRows(files, daily, selectedLabels, labelOrder)
  const sourceUrlByLabel = new Map(
    planLabels
      .filter((item): item is PlanLabelItem & { source_url: string } => Boolean(item.source_url))
      .map((item) => [item.label, item.source_url]),
  )
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
                      <span className="breakdown-file-label">{row.file}</span>
                      {sourceUrlByLabel.get(row.file) && (
                        <a
                          href={sourceUrlByLabel.get(row.file)}
                          target="_blank"
                          rel="noreferrer"
                          className="plan-excel-link"
                          title="SharePointのExcelを開く"
                          aria-label={`${row.file} のExcelファイルを開く`}
                        >
                          <FileSpreadsheet aria-hidden="true" />
                        </a>
                      )}
                    </td>
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

      {selectedLabels.length === 0 && (
        <OpenBugList bugs={openBugs} bugDataFetched={bugDataFetched} bugStateColors={bugStateColors} />
      )}
    </div>
  )
}

function OpenBugList({
  bugs,
  bugDataFetched,
  bugStateColors,
}: {
  bugs: OpenBugItem[]
  bugDataFetched: boolean
  bugStateColors: BugStateColorSetting[]
}) {
  const openBugs = bugs.filter((bug) => !bug.is_suspended)
  const suspendedBugs = bugs.filter((bug) => bug.is_suspended)
  return (
    <>
      <BugListSection
        title="未解決チケット一覧"
        ariaLabel="未解決のチケット一覧"
        bugs={openBugs}
        emptyText={bugDataFetched ? '未解決のチケットはありません' : '課題データ未取得です'}
        bugStateColors={bugStateColors}
      />
      <BugListSection
        title="対応見送りチケット一覧"
        ariaLabel="対応見送りのチケット一覧"
        bugs={suspendedBugs}
        emptyText={bugDataFetched ? '対応見送りのチケットはありません' : '課題データ未取得です'}
        bugStateColors={bugStateColors}
      />
    </>
  )
}

function BugListSection({
  title,
  ariaLabel,
  bugs,
  emptyText,
  bugStateColors,
}: {
  title: string
  ariaLabel: string
  bugs: OpenBugItem[]
  emptyText: string
  bugStateColors: BugStateColorSetting[]
}) {
  const colorByState = buildBugStateColorMap(bugStateColors)
  return (
    <section className="breakdown-block" aria-label={ariaLabel}>
      <h3>{title}</h3>
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
                  <td className="open-bug-state-cell"><BugStateBadge state={bug.state} color={bug.state ? colorByState.get(bug.state.toLocaleLowerCase()) : undefined} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="breakdown-empty">{emptyText}</div>
      )}
    </section>
  )
}


function BugStateBadge({ state, color }: { state: string | null; color?: BugStateColorSetting }) {
  if (!state) {
    return <span className="bug-state-badge bug-state-badge-empty">-</span>
  }
  const style = color
    ? {
        backgroundColor: color.background_color,
        borderColor: color.border_color,
        color: color.text_color,
      }
    : undefined
  return (
    <span className="bug-state-badge" style={style} title={state}>
      {state}
    </span>
  )
}

function buildBugStateColorMap(settings: BugStateColorSetting[]) {
  return new Map(settings.map((setting) => [setting.state.toLocaleLowerCase(), setting]))
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
  selectedLabels: string[],
  labelOrder: Map<string, number>,
): BreakdownRow[] {
  const selectedLabelSet = new Set(selectedLabels)
  const matchesSelectedLabels = (label: string | null) =>
    selectedLabels.length === 0 || (label != null && selectedLabelSet.has(label))
  const matchingFiles = files.filter((file) => matchesSelectedLabels(file.label))
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
    if (!matchesSelectedLabels(item.label)) {
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
    const aLabelOrder = labelOrder.get(a.file)
    const bLabelOrder = labelOrder.get(b.file)
    if (aLabelOrder !== undefined || bLabelOrder !== undefined) {
      const orderCompare = (aLabelOrder ?? Number.MAX_SAFE_INTEGER) - (bLabelOrder ?? Number.MAX_SAFE_INTEGER)
      if (orderCompare !== 0) {
        return orderCompare
      }
    }
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

