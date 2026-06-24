import { LayoutDashboard, ChevronRight } from 'lucide-react'
import type { ProjectItem } from '../api/types'
import { formatDate } from '../utils/date'

// マネージャー層向けの俯瞰ビュー。アーカイブ済み以外の案件を 1 表で確認する。
// データは App が保持する projects（GET /api/v1/projects）をそのまま利用し、専用 API は持たない。

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

function RateCell({
  value,
  done,
}: {
  value: number | null | undefined
  done: boolean
}) {
  const hasValue = value != null
  const width = hasValue ? Math.max(0, Math.min(100, value)) : 0
  return (
    <div className="dashboard-rate-cell">
      <div className="dashboard-rate-top">
        <span className={`dashboard-rate-value${hasValue ? '' : ' empty'}`}>{formatRate(value)}</span>
      </div>
      <div className="dashboard-rate-bar">
        <span className={done ? 'done' : ''} style={{ width: `${width}%` }} />
      </div>
    </div>
  )
}

export function Dashboard({
  projects,
  onOpenProject,
  onCreate,
}: {
  projects: ProjectItem[]
  onOpenProject: (testingId: number) => void
  onCreate: () => void
}) {
  const activeProjects = projects.filter((project) => !project.archived)

  if (activeProjects.length === 0) {
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

  return (
    <div className="content-shell dashboard">
      <header className="content-header">
        <div>
          <div className="title-with-icon">
            <LayoutDashboard className="title-icon" aria-hidden="true" />
            <h1>プロジェクト一覧</h1>
          </div>
        </div>
      </header>

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
            {activeProjects.map((project) => {
              const status = getProjectStatus(project)
              const plannedPeriod = formatPlannedPeriod(project)
              const completed = project.actual_all_completed
              return (
                <tr
                  key={project.testing_id}
                  onClick={() => onOpenProject(project.testing_id)}
                  title={`${project.name} (#${project.testing_id})`}
                >
                  <td className="dashboard-testing-id">{project.testing_id}</td>
                  <td className="dashboard-name-cell">
                    <span className="dashboard-proj-name">
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
                  <td className={`dashboard-period${plannedPeriod ? '' : ' empty'}`}>
                    {plannedPeriod ?? '-'}
                  </td>
                  <td className="num">
                    <RateCell value={project.actual_completed_rate} done={completed} />
                  </td>
                  <td className="num">
                    <RateCell value={project.actual_vs_plan_rate} done={completed} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
