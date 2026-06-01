import type { ProjectItem } from '../api/types'
import { formatDate, formatDateTime } from '../utils/date'
import {
  getProgressStatusLevel,
  type ProgressStatusLevel,
  type ProgressStatusThresholds,
} from '../utils/statusThresholds'
import { PbChartPanel } from './PbChartPanel'
import { LockIcon } from './icons/LockIcon'
import { ClipboardList, FolderKanban, Pencil } from 'lucide-react'

export function ProjectOverview({
  project,
  progressStatusThresholds,
  onCreate,
  onEdit,
  onPlans,
}: {
  project: ProjectItem | null
  progressStatusThresholds: ProgressStatusThresholds
  onCreate: () => void
  onEdit: () => void
  onPlans: () => void
}) {
  if (!project) {
    return (
      <div className="empty-state">
        <h1>プロジェクトを作成してください</h1>
        <p>Testing ID を登録すると、CLI から届いた実績と自動で紐付きます。</p>
        <button className="primary-button large" type="button" onClick={onCreate}>
          + プロジェクト作成
        </button>
      </div>
    )
  }

  const status = getProjectStatus(project)
  const planStatusLevel = getProgressStatusLevel(project.actual_vs_plan_rate, progressStatusThresholds)
  const needsPlanInput = project.has_actuals && project.active_plan_count === 0
  const plannedPeriod =
    project.planned_start_date && project.planned_end_date
      ? `${formatDate(project.planned_start_date)} ~ ${formatDate(project.planned_end_date)}`
      : null

  return (
    <div className="content-shell project-overview">
      <header className="content-header">
        <div>
          <h1 className="project-title">
            <FolderKanban className="title-icon" aria-hidden="true" />
            {project.archived && <LockIcon />}
            <span>{project.name}</span>
            <button
              className="icon-button project-edit-button"
              type="button"
              onClick={onEdit}
              aria-label="プロジェクト情報を編集"
              title="プロジェクト情報を編集"
            >
              <Pencil aria-hidden="true" />
            </button>
          </h1>
          {plannedPeriod && <div className="project-planned-period">予定期間: {plannedPeriod}</div>}
          <div className="project-status-row">
            <div className={`project-status ${status.className}`}>
              <span className="status-dot" aria-hidden="true" />
              {status.label}
            </div>
            {needsPlanInput && (
              <span className="project-plan-missing-badge" title="テスト計画の入力が必要です。">
                未計画
              </span>
            )}
          </div>
        </div>
        <div className="header-actions">
          <button className="primary-button icon-text-button" type="button" onClick={onPlans}>
            <ClipboardList className="button-icon" aria-hidden="true" strokeWidth={2.2} />
            <span>テスト計画入力</span>
          </button>
        </div>
      </header>

      <section className="summary-grid">
        <StatusTile label="完了率(対全体)" value={formatRate(project.actual_completed_rate)} />
        <StatusTile
          label="完了率(対計画)"
          value={formatRate(project.actual_vs_plan_rate)}
          statusLevel={planStatusLevel}
        />
        <StatusTile label="最終更新" value={formatDateTime(project.actuals_updated_at)} />
      </section>

      <PbChartPanel key={project.testing_id} project={project} onPlans={onPlans} />
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
  return `${value.toFixed(1)}%`
}

function StatusTile({
  label,
  value,
  statusLevel,
}: {
  label: string
  value: string
  statusLevel?: ProgressStatusLevel
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
