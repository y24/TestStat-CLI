import type { ProjectItem } from '../api/types'
import { formatDateTime } from '../utils/date'
import { PbChartPanel } from './PbChartPanel'
import { LockIcon } from './icons/LockIcon'

export function ProjectOverview({
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

  const status = getProjectStatus(project)

  return (
    <div className="content-shell project-overview">
      <header className="content-header">
        <div>
          <h1 className="project-title">
            {project.archived && <LockIcon />}
            <span>{project.name}</span>
          </h1>
          <div className={`project-status ${status.className}`}>
            <span className="status-dot" aria-hidden="true" />
            {status.label}
          </div>
        </div>
        <div className="header-actions">
          <button className="secondary-button" type="button" onClick={onEdit}>
            プロジェクト情報編集
          </button>
          <button className="primary-button" type="button" onClick={onPlans}>
            テスト計画入力
          </button>
        </div>
      </header>

      <section className="summary-grid">
        <StatusTile label="完了率(対全体)" value={formatRate(project.actual_completed_rate)} />
        <StatusTile label="完了率(対計画)" value={formatRate(project.actual_vs_plan_rate)} />
        <StatusTile label="最終更新" value={formatDateTime(project.actuals_updated_at)} />
      </section>

      <PbChartPanel key={project.testing_id} project={project} />
    </div>
  )
}

function getProjectStatus(project: ProjectItem): { label: string; className: string } {
  if (!project.has_actuals) {
    return { label: '未開始', className: 'not-started' }
  }
  if (project.actual_all_completed) {
    return { label: '完了', className: 'completed' }
  }
  return { label: '進行中', className: 'active' }
}

function formatRate(value: number | null | undefined) {
  if (value == null) {
    return '-'
  }
  return `${value.toFixed(value % 1 === 0 ? 0 : 2)}%`
}

function StatusTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="status-tile">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
