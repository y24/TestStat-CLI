import type { ProjectItem } from '../api/types'
import { formatDateTime } from '../utils/date'
import { PbChartPanel } from './PbChartPanel'

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

  return (
    <div className="content-shell">
      <header className="content-header">
        <div>
          <div className="eyebrow">testing_id: {project.testing_id}</div>
          <h1>{project.name}</h1>
          <div className="header-meta">{project.archived ? 'アーカイブ済み' : '進行中'}</div>
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
