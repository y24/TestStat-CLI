import { ChevronRight, LayoutDashboard, LockKeyhole, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { ProjectItem } from '../api/types'
import { formatDate } from '../utils/date'
import {
  getProgressStatusLevel,
  type ProgressStatusLevel,
  type ProgressStatusThresholds,
} from '../utils/statusThresholds'

// マネージャー層向けの俯瞰ビュー。プロジェクトを 1 表で確認する。
// データは App が保持する projects（GET /api/v1/projects）をそのまま利用し、専用 API は持たない。

type DashboardTab = 'active' | 'archived'

function getProjectStatus(project: ProjectItem): { label: string; className: string } {
  if (!project.has_actuals) {
    return { label: '未開始', className: 'not-started' }
  }
  if (project.actual_all_completed) {
    return { label: '完了', className: 'completed' }
  }
  return { label: '進行中', className: 'active' }
}

function formatRate(value: number | null | undefined): string {
  if (value == null) {
    return '-'
  }
  return `${value.toFixed(1)}%`
}

function formatPlannedPeriod(project: ProjectItem): string | null {
  if (project.planned_start_date && project.planned_end_date) {
    return `${formatDate(project.planned_start_date)} ~ ${formatDate(project.planned_end_date)}`
  }
  return null
}

function getProgressStatusLabel(level: ProgressStatusLevel): string {
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

function RateCell({
  value,
  done,
  showBar = true,
  statusLevel,
  delayDays,
}: {
  value: number | null | undefined
  done: boolean
  showBar?: boolean
  statusLevel?: ProgressStatusLevel
  delayDays?: number | null
}) {
  const hasValue = value != null
  const width = hasValue ? Math.max(0, Math.min(100, value)) : 0
  // 未開始（値なし=unknown）のときは丸を出さず - だけ表示する。
  const showDot = statusLevel != null && statusLevel !== 'unknown'
  return (
    <div className={`dashboard-rate-cell${showBar ? '' : ' no-bar'}`}>
      <div className="dashboard-rate-top">
        {showDot && (
          <span
            className={`plan-status-indicator ${statusLevel}`}
            aria-label={getProgressStatusLabel(statusLevel)}
            title={getProgressStatusLabel(statusLevel)}
          >
            ●
          </span>
        )}
        <span className={`dashboard-rate-value${hasValue ? '' : ' empty'}`}>{formatRate(value)}</span>
        {delayDays != null && delayDays > 0 && (
          <span className="dashboard-rate-delay">({delayDays.toFixed(1)}日遅延)</span>
        )}
      </div>
      {showBar && (
        <div className="dashboard-rate-bar">
          <span className={done ? 'done' : ''} style={{ width: `${width}%` }} />
        </div>
      )}
    </div>
  )
}

function ProjectRow({
  project,
  archived,
  progressStatusThresholds,
  onOpenProject,
}: {
  project: ProjectItem
  archived: boolean
  progressStatusThresholds: ProgressStatusThresholds
  onOpenProject: (testingId: number) => void
}) {
  const status = getProjectStatus(project)
  const plannedPeriod = formatPlannedPeriod(project)
  const completed = project.actual_all_completed
  const planStatusLevel = getProgressStatusLevel(project.actual_vs_plan_rate, progressStatusThresholds)
  return (
    <tr onClick={() => onOpenProject(project.testing_id)} title={`${project.name} (#${project.testing_id})`}>
      <td className="dashboard-testing-id">{project.testing_id}</td>
      <td className="dashboard-name-cell">
        <span className="dashboard-proj-name">
          {archived && <LockKeyhole className="dashboard-proj-lock" aria-hidden="true" />}
          <span className="dashboard-proj-name-text">{project.name}</span>
          <ChevronRight className="dashboard-chevron" aria-hidden="true" />
        </span>
      </td>
      <td>
        <span className={`pill ${status.className}`}>
          <span className="status-dot" aria-hidden="true" />
          {status.label}
        </span>
      </td>
      <td className={`dashboard-period${plannedPeriod ? '' : ' empty'}`}>{plannedPeriod ?? '-'}</td>
      <td className="num">
        <RateCell value={project.actual_completed_rate} done={completed} />
      </td>
      <td className="num">
        <RateCell
          value={project.actual_vs_plan_rate}
          done={completed}
          showBar={false}
          statusLevel={planStatusLevel}
          delayDays={project.actual_vs_plan_delay_days}
        />
      </td>
    </tr>
  )
}

export function Dashboard({
  projects,
  progressStatusThresholds,
  onOpenProject,
  onCreate,
}: {
  projects: ProjectItem[]
  progressStatusThresholds: ProgressStatusThresholds
  onOpenProject: (testingId: number) => void
  onCreate: () => void
}) {
  const [tab, setTab] = useState<DashboardTab>('active')
  const [query, setQuery] = useState('')

  // アクティブは App 側のソート（display_order）を踏襲。アーカイブは更新日時の新しい順。
  const activeProjects = useMemo(() => projects.filter((project) => !project.archived), [projects])
  const archivedProjects = useMemo(
    () =>
      projects
        .filter((project) => project.archived)
        .sort((a, b) => b.updated_at.localeCompare(a.updated_at)),
    [projects],
  )

  const tabProjects = tab === 'archived' ? archivedProjects : activeProjects
  const trimmedQuery = query.trim().toLocaleLowerCase()
  const filteredProjects = useMemo(() => {
    if (!trimmedQuery) {
      return tabProjects
    }
    return tabProjects.filter((project) => project.name.toLocaleLowerCase().includes(trimmedQuery))
  }, [tabProjects, trimmedQuery])

  // プロジェクトが 1 件も無いときは作成を促す。
  if (projects.length === 0) {
    return (
      <div className="empty-state">
        <h1>プロジェクトがありません</h1>
        <p>Testing ID を登録すると、CLI から届いた実績と自動で紐付きます。</p>
        <button className="primary-button large" type="button" onClick={onCreate}>
          + プロジェクト作成
        </button>
      </div>
    )
  }

  const emptyMessage = trimmedQuery
    ? '一致するプロジェクトはありません'
    : tab === 'archived'
      ? 'アーカイブ済みプロジェクトはありません'
      : 'プロジェクトがありません'

  return (
    <div className="content-shell dashboard">
      <header className="content-header">
        <div>
          <div className="title-with-icon">
            <LayoutDashboard className="title-icon" aria-hidden="true" />
            <h1>プロジェクト一覧</h1>
          </div>
        </div>
        <label className="dashboard-filter" title="プロジェクト名でフィルタ">
          <Search className="dashboard-filter-icon" aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="プロジェクト名"
            aria-label="プロジェクト名でフィルタ"
          />
        </label>
      </header>

      <div className="dashboard-tabs" role="tablist">
        <button
          className={`dashboard-tab${tab === 'active' ? ' active' : ''}`}
          type="button"
          role="tab"
          aria-selected={tab === 'active'}
          onClick={() => setTab('active')}
        >
          アクティブ <span className="dashboard-tab-count">{activeProjects.length}</span>
        </button>
        <button
          className={`dashboard-tab${tab === 'archived' ? ' active' : ''}`}
          type="button"
          role="tab"
          aria-selected={tab === 'archived'}
          onClick={() => setTab('archived')}
        >
          アーカイブ済み <span className="dashboard-tab-count">{archivedProjects.length}</span>
        </button>
      </div>

      <div className="dashboard-table-card">
        <table className="dashboard-table">
          <thead>
            <tr>
              <th className="dashboard-id-col">ID</th>
              <th className="dashboard-name-col">プロジェクト名</th>
              <th className="dashboard-status-col">ステータス</th>
              <th className="dashboard-period-col">予定期間</th>
              <th className="num dashboard-rate-col">完了率（対全体）</th>
              <th className="num dashboard-rate-col">完了率（対計画）</th>
            </tr>
          </thead>
          <tbody>
            {filteredProjects.length === 0 ? (
              <tr className="dashboard-empty-row">
                <td colSpan={6}>{emptyMessage}</td>
              </tr>
            ) : (
              filteredProjects.map((project) => (
                <ProjectRow
                  key={project.testing_id}
                  project={project}
                  archived={tab === 'archived'}
                  progressStatusThresholds={progressStatusThresholds}
                  onOpenProject={onOpenProject}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
