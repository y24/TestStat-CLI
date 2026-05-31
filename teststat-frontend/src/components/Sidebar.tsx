import { FolderKanban, Plus, RefreshCw, Settings } from 'lucide-react'
import type { ProjectItem } from '../api/types'
import type { ApiStatus } from '../types/ui'
import { LockIcon } from './icons/LockIcon'

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
      <h1 className="app-title">TestStat Studio</h1>
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

function formatRate(value: number | null | undefined) {
  if (value == null) {
    return '-'
  }
  return `${value.toFixed(1)}%`
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
        <button className="primary-button nav-create-button" type="button" onClick={onCreate} disabled={loading}>
          <Plus className="nav-create-icon" aria-hidden="true" strokeWidth={2.4} />
          <span>プロジェクト作成</span>
        </button>
        <button
          className="icon-button"
          type="button"
          onClick={onRefresh}
          title="再読込"
          disabled={loading}
        >
          <RefreshCw className="nav-refresh-icon" aria-hidden="true" strokeWidth={2.1} />
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
          <Settings className="settings-button-icon" aria-hidden="true" strokeWidth={2.1} />
          設定
        </button>
      </div>
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
          <span className="project-name-row">
            <FolderKanban className="project-list-icon" aria-hidden="true" />
            {project.archived && <LockIcon />}
            <span className="project-name">{project.name}</span>
          </span>
          <span className="project-meta">
            {getProjectStatus(project)}
            {' / '}
            {formatRate(project.actual_completed_rate)}
          </span>
        </button>
      ))}
    </div>
  )
}
