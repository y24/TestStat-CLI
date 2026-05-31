import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import * as echarts from 'echarts/core'
import type { ComposeOption, ECharts } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import type { BarSeriesOption, LineSeriesOption } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
} from 'echarts/components'
import type {
  DataZoomComponentOption,
  GridComponentOption,
  LegendComponentOption,
  TooltipComponentOption,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import './App.css'
import {
  activatePlan,
  createProject,
  createPlan,
  deletePlan,
  deleteProject,
  fetchHealth,
  fetchPbChart,
  fetchPlans,
  fetchProgressFiles,
  fetchProjects,
  updateProject,
} from './api/client'
import type { FileProgressItem, PbChartResponse, PlanItem, ProjectItem } from './api/types'

type ApiStatus = 'checking' | 'ok' | 'error'
type ViewMode = 'overview' | 'new' | 'edit' | 'plans'
type PbChartOption = ComposeOption<
  | BarSeriesOption
  | LineSeriesOption
  | DataZoomComponentOption
  | GridComponentOption
  | LegendComponentOption
  | TooltipComponentOption
>

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

interface ProjectFormState {
  testing_id: string
  name: string
  archived: boolean
}

const emptyForm: ProjectFormState = {
  testing_id: '',
  name: '',
  archived: false,
}

export default function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const [projects, setProjects] = useState<ProjectItem[]>([])
  const [selectedTestingId, setSelectedTestingId] = useState<number | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('overview')
  const [loadingProjects, setLoadingProjects] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const selectedProject = useMemo(
    () => projects.find((project) => project.testing_id === selectedTestingId) ?? null,
    [projects, selectedTestingId],
  )

  const loadProjects = () => {
    setLoadingProjects(true)
    setError(null)
    fetchProjects()
      .then((items) => {
        setProjects(items)
        setSelectedTestingId((current) => {
          if (current !== null && items.some((item) => item.testing_id === current)) {
            return current
          }
          return items[0]?.testing_id ?? null
        })
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoadingProjects(false))
  }

  useEffect(() => {
    fetchHealth()
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('error'))
    fetchProjects()
      .then((items) => {
        setProjects(items)
        setSelectedTestingId(items[0]?.testing_id ?? null)
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoadingProjects(false))
  }, [])

  const handleProjectSaved = (project: ProjectItem) => {
    setProjects((current) => {
      const exists = current.some((item) => item.testing_id === project.testing_id)
      const next = exists
        ? current.map((item) => (item.testing_id === project.testing_id ? project : item))
        : [project, ...current]
      return sortProjects(next)
    })
    setSelectedTestingId(project.testing_id)
    setViewMode('overview')
  }

  const handleDeleted = (testingId: number) => {
    setProjects((current) => current.filter((item) => item.testing_id !== testingId))
    setSelectedTestingId((current) => (current === testingId ? null : current))
    setViewMode('overview')
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <SidebarHeader apiStatus={apiStatus} />
        <ProjectNav
          projects={projects}
          selectedTestingId={selectedTestingId}
          loading={loadingProjects}
          onSelect={(testingId) => {
            setSelectedTestingId(testingId)
            setViewMode('overview')
          }}
          onCreate={() => {
            setSelectedTestingId(null)
            setViewMode('new')
          }}
          onRefresh={loadProjects}
        />
      </aside>
      <main className="main-area">
        {error && (
          <div className="error-strip">
            <span>{error}</span>
            <button className="link-button" type="button" onClick={loadProjects}>
              再読込
            </button>
          </div>
        )}
        {viewMode === 'new' && (
          <ProjectEditor
            mode="new"
            project={null}
            onCancel={() => setViewMode(selectedProject ? 'overview' : 'new')}
            onSaved={handleProjectSaved}
          />
        )}
        {viewMode === 'edit' && selectedProject && (
          <ProjectEditor
            mode="edit"
            project={selectedProject}
            onCancel={() => setViewMode('overview')}
            onSaved={handleProjectSaved}
            onDeleted={handleDeleted}
          />
        )}
        {viewMode === 'overview' && (
          <ProjectOverview
            project={selectedProject}
            onCreate={() => setViewMode('new')}
            onEdit={() => setViewMode('edit')}
            onPlans={() => setViewMode('plans')}
          />
        )}
        {viewMode === 'plans' && selectedProject && (
          <PlanEditor
            project={selectedProject}
            onBack={() => setViewMode('overview')}
            onChanged={loadProjects}
          />
        )}
      </main>
    </div>
  )
}

function SidebarHeader({ apiStatus }: { apiStatus: ApiStatus }) {
  return (
    <div className="sidebar-header">
      <div className="app-title">テスト状況</div>
      <div className={`api-status api-status-${apiStatus}`}>
        {apiStatus === 'checking' && 'API 接続確認中...'}
        {apiStatus === 'ok' && 'API 接続OK'}
        {apiStatus === 'error' && 'API 接続失敗'}
      </div>
    </div>
  )
}

function ProjectNav({
  projects,
  selectedTestingId,
  loading,
  onSelect,
  onCreate,
  onRefresh,
}: {
  projects: ProjectItem[]
  selectedTestingId: number | null
  loading: boolean
  onSelect: (testingId: number) => void
  onCreate: () => void
  onRefresh: () => void
}) {
  const activeProjects = projects.filter((project) => !project.archived)
  const archivedProjects = projects.filter((project) => project.archived)

  return (
    <div className="project-nav">
      <div className="nav-actions">
        <button className="primary-button" type="button" onClick={onCreate}>
          + プロジェクト
        </button>
        <button className="icon-button" type="button" onClick={onRefresh} title="再読込">
          ↻
        </button>
      </div>
      {loading && <div className="nav-message">読み込み中...</div>}
      {!loading && projects.length === 0 && <div className="nav-message">プロジェクト未登録</div>}
      {!loading && activeProjects.length > 0 && (
        <ProjectList
          projects={activeProjects}
          selectedTestingId={selectedTestingId}
          onSelect={onSelect}
        />
      )}
      {!loading && archivedProjects.length > 0 && (
        <details className="archived-group">
          <summary>アーカイブ済み ({archivedProjects.length})</summary>
          <ProjectList
            projects={archivedProjects}
            selectedTestingId={selectedTestingId}
            onSelect={onSelect}
          />
        </details>
      )}
    </div>
  )
}

function ProjectList({
  projects,
  selectedTestingId,
  onSelect,
}: {
  projects: ProjectItem[]
  selectedTestingId: number | null
  onSelect: (testingId: number) => void
}) {
  return (
    <div className="project-list">
      {projects.map((project) => (
        <button
          key={project.testing_id}
          className={`project-row ${project.testing_id === selectedTestingId ? 'selected' : ''}`}
          type="button"
          onClick={() => onSelect(project.testing_id)}
        >
          <span className="project-name">{project.name}</span>
          <span className="project-meta">
            #{project.testing_id}
            {project.has_actuals ? ' / 実績あり' : ' / 実績なし'}
          </span>
        </button>
      ))}
    </div>
  )
}

function ProjectOverview({
  project,
  onCreate,
  onEdit,
  onPlans,
}: {
  project: ProjectItem | null
  onCreate: () => void
  onEdit: () => void
  onPlans: () => void
}) {
  if (!project) {
    return (
      <div className="empty-state">
        <h1>プロジェクトを作成してください</h1>
        <p>testing_id を登録すると、CLI から届いた実績と自動で紐付きます。</p>
        <button className="primary-button large" type="button" onClick={onCreate}>
          + プロジェクト
        </button>
      </div>
    )
  }

  return (
    <div className="content-shell">
      <header className="content-header">
        <div>
          <div className="eyebrow">testing_id: {project.testing_id}</div>
          <h1>{project.name}</h1>
          <div className="header-meta">
            {project.archived ? 'アーカイブ済み' : '進行中'}
          </div>
        </div>
        <div className="header-actions">
          <button className="secondary-button" type="button" onClick={onEdit}>
            編集
          </button>
          <button className="primary-button" type="button" onClick={onPlans}>
            計画を編集
          </button>
        </div>
      </header>

      <section className="summary-grid">
        <StatusTile label="実績" value={project.has_actuals ? '受信済み' : '未受信'} />
        <StatusTile label="最終更新" value={formatDateTime(project.actuals_updated_at)} />
        <StatusTile label="有効な計画" value={`${project.active_plan_count} 件`} />
      </section>

      <PbChartPanel key={project.testing_id} project={project} />
    </div>
  )
}

function StatusTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="status-tile">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function PbChartPanel({ project }: { project: ProjectItem }) {
  const [result, setResult] = useState<{
    testingId: number
    label: string | null
    includePastPlans: boolean
    chart: PbChartResponse | null
    files: FileProgressItem[]
    plans: PlanItem[]
    error: string | null
  } | null>(null)
  const [selectedLabel, setSelectedLabel] = useState<string>('')
  const [layers, setLayers] = useState({
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
              <option value="">全テスト</option>
              {labels.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <div className="layer-controls">
            <label>
              <input
                type="checkbox"
                checked={layers.plannedLine}
                onChange={(event) => setLayers({ ...layers, plannedLine: event.target.checked })}
              />
              計画線
            </label>
            <label>
              <input
                type="checkbox"
                checked={layers.actualLine}
                onChange={(event) => setLayers({ ...layers, actualLine: event.target.checked })}
              />
              実績線
            </label>
            <label>
              <input
                type="checkbox"
                checked={layers.dailyBars}
                onChange={(event) => setLayers({ ...layers, dailyBars: event.target.checked })}
              />
              日別消化
            </label>
            <label>
              <input
                type="checkbox"
                checked={layers.pastPlans}
                onChange={(event) => setLayers({ ...layers, pastPlans: event.target.checked })}
              />
              過去計画
            </label>
          </div>
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

function PbChart({
  chart,
  layers,
}: {
  chart: PbChartResponse
  layers: { plannedLine: boolean; actualLine: boolean; dailyBars: boolean; pastPlans: boolean }
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
    instanceRef.current?.setOption(buildPbChartOption(chart, layers), true)
  }, [chart, layers])

  return <div className="pb-chart" ref={containerRef} />
}

type PlanInputMode = 'even' | 'csv'

interface PlanFormState {
  label: string
  reason: string
  planned_total_cases: string
  start_date: string
  end_date: string
  activate: boolean
  inputMode: PlanInputMode
  dailyText: string
}

function PlanEditor({
  project,
  onBack,
  onChanged,
}: {
  project: ProjectItem
  onBack: () => void
  onChanged: () => void
}) {
  const [result, setResult] = useState<{
    testingId: number
    plans: PlanItem[]
    files: FileProgressItem[]
    error: string | null
  } | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [form, setForm] = useState<PlanFormState>(() => {
    const today = getTodayString()
    return {
      label: '',
      reason: '',
      planned_total_cases: '',
      start_date: today,
      end_date: today,
      activate: true,
      inputMode: 'even',
      dailyText: '',
    }
  })

  const loadPlans = () => {
    Promise.all([
      fetchPlans(project.testing_id),
      fetchProgressFiles(project.testing_id).catch(() => [] as FileProgressItem[]),
    ])
      .then(([plans, files]) =>
        setResult({ testingId: project.testing_id, plans, files, error: null }),
      )
      .catch((err) =>
        setResult({
          testingId: project.testing_id,
          plans: [],
          files: [],
          error: getErrorMessage(err),
        }),
      )
  }

  useEffect(() => {
    let ignore = false
    Promise.all([
      fetchPlans(project.testing_id),
      fetchProgressFiles(project.testing_id).catch(() => [] as FileProgressItem[]),
    ])
      .then(([plans, files]) => {
        if (!ignore) {
          setResult({ testingId: project.testing_id, plans, files, error: null })
        }
      })
      .catch((err) => {
        if (!ignore) {
          setResult({
            testingId: project.testing_id,
            plans: [],
            files: [],
            error: getErrorMessage(err),
          })
        }
      })
    return () => {
      ignore = true
    }
  }, [project.testing_id])

  const loading = result?.testingId !== project.testing_id
  const plans = result?.testingId === project.testing_id ? result.plans : []
  const files = result?.testingId === project.testing_id ? result.files : []
  const labels = Array.from(
    new Set(files.map((file) => file.label).filter((label): label is string => Boolean(label))),
  ).sort((a, b) => a.localeCompare(b))
  const planRows = plans.length > 0 ? plans : []

  const submitPlan = (event: FormEvent) => {
    event.preventDefault()
    setFormError(null)

    const plannedTotal = Number(form.planned_total_cases)
    if (!Number.isInteger(plannedTotal) || plannedTotal <= 0) {
      setFormError('項目数は正の整数で入力してください')
      return
    }
    if (!form.start_date || !form.end_date || form.start_date > form.end_date) {
      setFormError('開始日と終了日を正しい順序で入力してください')
      return
    }

    let daily: Array<{ date: string; planned_count: number }>
    try {
      daily =
        form.inputMode === 'even'
          ? buildEvenDaily(form.start_date, form.end_date, plannedTotal)
          : parseDailyCsv(form.dailyText)
    } catch (err) {
      setFormError(getErrorMessage(err))
      return
    }

    if (daily.length === 0) {
      setFormError('日別計画を1件以上入力してください')
      return
    }
    const invalidDaily = daily.find((item) => item.date < form.start_date || item.date > form.end_date)
    if (invalidDaily) {
      setFormError(`日別計画 ${invalidDaily.date} が期間外です`)
      return
    }

    setSubmitting(true)
    createPlan(project.testing_id, {
      label: form.label.trim() || null,
      reason: form.reason.trim() || null,
      planned_total_cases: plannedTotal,
      start_date: form.start_date,
      end_date: form.end_date,
      activate: form.activate,
      daily,
    })
      .then(() => {
        setForm({
          ...form,
          reason: '',
          planned_total_cases: '',
          dailyText: '',
        })
        loadPlans()
        onChanged()
      })
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  const handleActivate = (plan: PlanItem) => {
    setSubmitting(true)
    activatePlan(plan.id)
      .then(() => {
        loadPlans()
        onChanged()
      })
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  const handleDeletePlan = (plan: PlanItem) => {
    const confirmed = window.confirm(`計画 ${displayLabel(plan.label)} v${plan.version} を削除します。`)
    if (!confirmed) {
      return
    }
    setSubmitting(true)
    deletePlan(plan.id)
      .then(() => {
        loadPlans()
        onChanged()
      })
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="content-shell">
      <header className="content-header">
        <div>
          <div className="eyebrow">{project.name}</div>
          <h1>テスト計画</h1>
          <div className="header-meta">testing_id: {project.testing_id}</div>
        </div>
        <div className="header-actions">
          <button className="secondary-button" type="button" onClick={onBack}>
            ダッシュボード
          </button>
        </div>
      </header>

      {loading && <div className="chart-state">計画を読み込み中...</div>}
      {!loading && result?.error && (
        <div className="form-error">計画を取得できませんでした: {result.error}</div>
      )}
      {!loading && !result?.error && (
        <>
          <section className="plan-layout">
            <div className="plan-list-panel">
              <div className="panel-title">計画バージョン</div>
              {planRows.length === 0 && (
                <div className="muted-block">まだ計画がありません。右側で新しい計画を作成してください。</div>
              )}
              {planRows.length > 0 && (
                <div className="plan-table-wrap">
                  <table className="plan-table">
                    <thead>
                      <tr>
                        <th>テスト(label)</th>
                        <th>版</th>
                        <th>項目数</th>
                        <th>期間</th>
                        <th>日別合計</th>
                        <th>操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {planRows.map((plan) => (
                        <tr key={plan.id} className={plan.is_active ? 'active-plan-row' : ''}>
                          <td>
                            <strong>{displayLabel(plan.label)}</strong>
                            {plan.reason && <span className="row-note">{plan.reason}</span>}
                          </td>
                          <td>
                            v{plan.version}
                            {plan.is_active && <span className="active-badge">有効</span>}
                          </td>
                          <td>{plan.planned_total_cases}</td>
                          <td>
                            {formatDate(plan.start_date)} - {formatDate(plan.end_date)}
                          </td>
                          <td>{plan.daily_total}</td>
                          <td>
                            <div className="table-actions">
                              <button
                                className="secondary-button compact"
                                type="button"
                                disabled={plan.is_active || submitting}
                                onClick={() => handleActivate(plan)}
                              >
                                有効化
                              </button>
                              <button
                                className="danger-button compact"
                                type="button"
                                disabled={submitting}
                                onClick={() => handleDeletePlan(plan)}
                              >
                                削除
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <form className="editor-form plan-form" onSubmit={submitPlan}>
              <div className="panel-title">新バージョン作成</div>
              {formError && <div className="form-error">{formError}</div>}
              <label>
                <span>テスト(label)</span>
                <input
                  list="label-candidates"
                  type="text"
                  value={form.label}
                  disabled={submitting}
                  onChange={(event) => setForm({ ...form, label: event.target.value })}
                  placeholder="全体計画の場合は空欄"
                />
                <datalist id="label-candidates">
                  {labels.map((label) => (
                    <option key={label} value={label} />
                  ))}
                </datalist>
              </label>
              <label>
                <span>変更理由</span>
                <input
                  type="text"
                  value={form.reason}
                  disabled={submitting}
                  onChange={(event) => setForm({ ...form, reason: event.target.value })}
                  placeholder="仕様追加、期間見直しなど"
                />
              </label>
              <div className="form-grid">
                <label>
                  <span>項目数</span>
                  <input
                    type="number"
                    min="1"
                    value={form.planned_total_cases}
                    disabled={submitting}
                    onChange={(event) => setForm({ ...form, planned_total_cases: event.target.value })}
                    required
                  />
                </label>
                <label>
                  <span>入力方法</span>
                  <select
                    value={form.inputMode}
                    disabled={submitting}
                    onChange={(event) =>
                      setForm({ ...form, inputMode: event.target.value as PlanInputMode })
                    }
                  >
                    <option value="even">均等配分</option>
                    <option value="csv">日別/CSV</option>
                  </select>
                </label>
              </div>
              <div className="form-grid">
                <label>
                  <span>開始日</span>
                  <input
                    type="date"
                    value={form.start_date}
                    disabled={submitting}
                    onChange={(event) => setForm({ ...form, start_date: event.target.value })}
                    required
                  />
                </label>
                <label>
                  <span>終了日</span>
                  <input
                    type="date"
                    value={form.end_date}
                    disabled={submitting}
                    onChange={(event) => setForm({ ...form, end_date: event.target.value })}
                    required
                  />
                </label>
              </div>
              {form.inputMode === 'csv' && (
                <label>
                  <span>日別計画</span>
                  <textarea
                    value={form.dailyText}
                    disabled={submitting}
                    onChange={(event) => setForm({ ...form, dailyText: event.target.value })}
                    placeholder={'date,planned_count\n2026-06-01,40\n2026-06-02,45'}
                    rows={7}
                  />
                </label>
              )}
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={form.activate}
                  disabled={submitting}
                  onChange={(event) => setForm({ ...form, activate: event.target.checked })}
                />
                <span>作成後に有効な計画にする</span>
              </label>
              <div className="actuals-note">
                {labels.length > 0
                  ? `実績label候補: ${labels.join(', ')}`
                  : '実績label候補はありません。labelは手入力できます。'}
              </div>
              <div className="form-actions">
                <button className="primary-button" type="submit" disabled={submitting}>
                  {submitting ? '作成中...' : '計画を作成'}
                </button>
              </div>
            </form>
          </section>
        </>
      )}
    </div>
  )
}

function ProjectEditor({
  mode,
  project,
  onCancel,
  onSaved,
  onDeleted,
}: {
  mode: 'new' | 'edit'
  project: ProjectItem | null
  onCancel: () => void
  onSaved: (project: ProjectItem) => void
  onDeleted?: (testingId: number) => void
}) {
  const [form, setForm] = useState<ProjectFormState>(() =>
    project
      ? {
          testing_id: String(project.testing_id),
          name: project.name,
          archived: project.archived,
        }
      : emptyForm,
  )
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setFormError(null)

    const testingId = Number(form.testing_id)
    if (!Number.isInteger(testingId) || testingId <= 0) {
      setFormError('testing_id は正の整数で入力してください')
      return
    }
    if (!form.name.trim()) {
      setFormError('表示名を入力してください')
      return
    }

    setSubmitting(true)
    const request =
      mode === 'new'
        ? createProject({
            testing_id: testingId,
            name: form.name.trim(),
          })
        : updateProject(testingId, {
            name: form.name.trim(),
            archived: form.archived,
          })

    request
      .then(onSaved)
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  const handleDelete = () => {
    if (!project || !onDeleted) {
      return
    }
    const confirmed = window.confirm(
      `testing_id ${project.testing_id} のプロジェクトと計画を削除します。実績データは削除されません。`,
    )
    if (!confirmed) {
      return
    }
    setSubmitting(true)
    setFormError(null)
    deleteProject(project.testing_id)
      .then(() => onDeleted(project.testing_id))
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="content-shell narrow">
      <header className="content-header">
        <div>
          <div className="eyebrow">プロジェクト</div>
          <h1>{mode === 'new' ? '新規作成' : '編集'}</h1>
        </div>
      </header>

      <form className="editor-form" onSubmit={submit}>
        {formError && <div className="form-error">{formError}</div>}
        <label>
          <span>testing_id</span>
          <input
            type="number"
            min="1"
            value={form.testing_id}
            disabled={mode === 'edit' || submitting}
            onChange={(event) => setForm({ ...form, testing_id: event.target.value })}
            required
          />
        </label>
        <label>
          <span>表示名</span>
          <input
            type="text"
            maxLength={255}
            value={form.name}
            disabled={submitting}
            onChange={(event) => setForm({ ...form, name: event.target.value })}
            required
          />
        </label>
        {mode === 'edit' && (
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={form.archived}
              disabled={submitting}
              onChange={(event) => setForm({ ...form, archived: event.target.checked })}
            />
            <span>アーカイブ済みにする</span>
          </label>
        )}

        {project && (
          <div className="actuals-note">
            {project.has_actuals
              ? `実績受信済み: ${formatDateTime(project.actuals_updated_at)}`
              : '実績未受信: CLI 送信後に testing_id で紐付きます'}
          </div>
        )}

        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={submitting}>
            {submitting ? '保存中...' : '保存'}
          </button>
          <button className="secondary-button" type="button" onClick={onCancel} disabled={submitting}>
            キャンセル
          </button>
          {mode === 'edit' && (
            <button className="danger-button" type="button" onClick={handleDelete} disabled={submitting}>
              削除
            </button>
          )}
        </div>
      </form>
    </div>
  )
}

function sortProjects(projects: ProjectItem[]) {
  return [...projects].sort((a, b) => {
    if (a.archived !== b.archived) {
      return Number(a.archived) - Number(b.archived)
    }
    return b.updated_at.localeCompare(a.updated_at)
  })
}

function displayLabel(label: string | null) {
  return label || '全体'
}

function buildChartNotices(chart: PbChartResponse) {
  const notices: string[] = []
  const hasPlan = chart.planned_total_cases !== null
  const hasActuals = chart.available_cases > 0 && chart.series.some((item) => item.actual_remaining !== null)
  const hasPastPlans = chart.past_plans.length > 0
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
  if (hasPastPlans) {
    notices.push(`過去計画 ${chart.past_plans.length} 件`)
  }
  if (hasNegativeDaily) {
    notices.push('負の日別値あり')
  }
  return notices
}

function buildEvenDaily(start: string, end: string, total: number) {
  const dates = enumerateDates(start, end)
  if (dates.length === 0) {
    return []
  }
  const base = Math.floor(total / dates.length)
  let rest = total % dates.length
  return dates.map((date) => {
    const planned_count = base + (rest > 0 ? 1 : 0)
    rest -= rest > 0 ? 1 : 0
    return { date, planned_count }
  })
}

function parseDailyCsv(text: string) {
  const rows = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
  const daily: Array<{ date: string; planned_count: number }> = []
  for (const row of rows) {
    if (/^date\s*,\s*planned_count$/i.test(row)) {
      continue
    }
    const [date, countText] = row.split(',').map((item) => item.trim())
    const planned_count = Number(countText)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isInteger(planned_count) || planned_count < 0) {
      throw new Error(`日別計画の形式が不正です: ${row}`)
    }
    daily.push({ date, planned_count })
  }
  return daily
}

function enumerateDates(start: string, end: string) {
  const result: string[] = []
  const current = new Date(`${start}T00:00:00`)
  const last = new Date(`${end}T00:00:00`)
  while (current <= last) {
    result.push(toDateInputValue(current))
    current.setDate(current.getDate() + 1)
  }
  return result
}

function toDateInputValue(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function buildPbChartOption(
  chart: PbChartResponse,
  layers: { plannedLine: boolean; actualLine: boolean; dailyBars: boolean; pastPlans: boolean },
): PbChartOption {
  const dates = chart.series.map((item) => item.date)
  const series: PbChartOption['series'] = []
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
        lineStyle: { type: 'dashed', width: 1, color: 'rgba(95, 107, 126, 0.42)' },
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
      lineStyle: { type: 'dashed', width: 2, color: '#8a94a6' },
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

function formatDateTime(value: string | null) {
  if (!value) {
    return '-'
  }
  return new Intl.DateTimeFormat('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(`${value}T00:00:00`))
}

function getTodayString() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function getErrorMessage(err: unknown) {
  return err instanceof Error ? err.message : '不明なエラーが発生しました'
}
