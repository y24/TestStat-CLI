import type { ProjectItem } from '../api/types'
import type { ApiStatus } from '../types/ui'

interface ProjectNavProps {
  projects: ProjectItem[]
  selectedTestingId: number | null
  loading: boolean
  onSelect: (testingId: number) => void
  onCreate: () => void
  onRefresh: () => void
  onSettings: () => void
}

export function Sidebar({
  apiStatus,
  projects,
  selectedTestingId,
  loading,
  onSelect,
  onCreate,
  onRefresh,
  onSettings,
}: ProjectNavProps & { apiStatus: ApiStatus }) {
  return (
    <aside className="sidebar">
      <SidebarHeader apiStatus={apiStatus} />
      <ProjectNav
        projects={projects}
        selectedTestingId={selectedTestingId}
        loading={loading}
        onSelect={onSelect}
        onCreate={onCreate}
        onRefresh={onRefresh}
        onSettings={onSettings}
      />
    </aside>
  )
}

function SidebarHeader({ apiStatus }: { apiStatus: ApiStatus }) {
  return (
    <div className="sidebar-header">
      <div className="app-title">テスト状況</div>
      {apiStatus === 'error' && <div className="api-status api-status-error">API 接続失敗</div>}
    </div>
  )
}

function getProjectStatus(project: ProjectItem) {
  if (!project.has_actuals) {
    return '未開始'
  }
  if (project.actual_all_completed) {
    return '完了'
  }
  return '進行中'
}

function ProjectNav({
  projects,
  selectedTestingId,
  loading,
  onSelect,
  onCreate,
  onRefresh,
  onSettings,
}: ProjectNavProps) {
  const activeProjects = projects.filter((project) => !project.archived)
  const archivedProjects = projects.filter((project) => project.archived)

  return (
    <div className="project-nav">
      <div className="nav-actions">
        <button className="primary-button" type="button" onClick={onCreate} disabled={loading}>
          + プロジェクト追加
        </button>
        <button
          className="icon-button"
          type="button"
          onClick={onRefresh}
          title="再読込"
          disabled={loading}
        >
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
      <div className="sidebar-footer">
        <button className="settings-button" type="button" onClick={onSettings} disabled={loading}>
          <SettingsIcon />
          設定
        </button>
      </div>
    </div>
  )
}

function SettingsIcon() {
  return (
    <svg
      className="settings-button-icon"
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path
        d="M19.4 13.5a7.9 7.9 0 0 0 0-3l2-1.5-2-3.5-2.4 1a8 8 0 0 0-2.6-1.5L14 2.5h-4l-.4 2.5A8 8 0 0 0 7 6.5l-2.4-1-2 3.5 2 1.5a7.9 7.9 0 0 0 0 3l-2 1.5 2 3.5 2.4-1a8 8 0 0 0 2.6 1.5l.4 2.5h4l.4-2.5a8 8 0 0 0 2.6-1.5l2.4 1 2-3.5-2-1.5Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
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
            {' / '}
            {getProjectStatus(project)}
          </span>
        </button>
      ))}
    </div>
  )
}
