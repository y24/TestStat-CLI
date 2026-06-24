import {
  closestCenter,
  DndContext,
  type DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical, LayoutDashboard, Plus, RefreshCw, Search, Settings } from 'lucide-react'
import { useMemo, useState, type CSSProperties } from 'react'
import type { ProjectItem } from '../api/types'
import type { ApiStatus } from '../types/ui'
import { LockIcon } from './icons/LockIcon'

interface ProjectNavProps {
  projects: ProjectItem[]
  selectedTestingId: number | null
  dashboardActive: boolean
  loading: boolean
  onDashboard: () => void
  onSelect: (testingId: number) => void
  onCreate: () => void
  onRefresh: () => void
  onReorder: (testingIds: number[]) => void
  onSettings: () => void
}

export function Sidebar({
  projects,
  selectedTestingId,
  dashboardActive,
  loading,
  onDashboard,
  onSelect,
  onCreate,
  onRefresh,
  onReorder,
  onSettings,
}: ProjectNavProps & { apiStatus: ApiStatus }) {
  return (
    <aside className="sidebar">
      <SidebarHeader />
      <ProjectNav
        projects={projects}
        selectedTestingId={selectedTestingId}
        dashboardActive={dashboardActive}
        loading={loading}
        onDashboard={onDashboard}
        onSelect={onSelect}
        onCreate={onCreate}
        onRefresh={onRefresh}
        onReorder={onReorder}
        onSettings={onSettings}
      />
    </aside>
  )
}

function SidebarHeader() {
  return (
    <div className="sidebar-header">
      <h1 className="app-title">TestStat Studio</h1>
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
  dashboardActive,
  loading,
  onDashboard,
  onSelect,
  onCreate,
  onRefresh,
  onReorder,
  onSettings,
}: ProjectNavProps) {
  const [archivedFilter, setArchivedFilter] = useState('')
  const activeProjects = projects.filter((project) => !project.archived)
  const archivedProjects = useMemo(
    () =>
      projects
        .filter((project) => project.archived)
        .sort((a, b) => b.updated_at.localeCompare(a.updated_at)),
    [projects],
  )
  const filteredArchivedProjects = useMemo(() => {
    const query = archivedFilter.trim().toLocaleLowerCase()
    if (!query) {
      return archivedProjects
    }
    return archivedProjects.filter((project) => project.name.toLocaleLowerCase().includes(query))
  }, [archivedFilter, archivedProjects])

  return (
    <div className="project-nav">
      <button
        className={['dashboard-nav-button', dashboardActive ? 'selected' : ''].filter(Boolean).join(' ')}
        type="button"
        onClick={onDashboard}
        aria-current={dashboardActive ? 'page' : undefined}
      >
        <LayoutDashboard className="dashboard-nav-icon" aria-hidden="true" strokeWidth={2.1} />
        <span>プロジェクト一覧</span>
      </button>
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
          onReorder={(testingIds) => {
            onReorder([...testingIds, ...archivedProjects.map((project) => project.testing_id)])
          }}
        />
      )}
      {!loading && archivedProjects.length > 0 && (
        <details className="archived-group">
          <summary>アーカイブ済み ({archivedProjects.length})</summary>
          <label className="archived-filter">
            <Search className="archived-filter-icon" aria-hidden="true" />
            <input
              type="search"
              value={archivedFilter}
              onChange={(event) => setArchivedFilter(event.target.value)}
              placeholder="プロジェクト名でフィルタ"
              aria-label="アーカイブ済みプロジェクトをプロジェクト名でフィルタ"
            />
          </label>
          {filteredArchivedProjects.length > 0 ? (
            <ArchivedProjectList
              projects={filteredArchivedProjects}
              selectedTestingId={selectedTestingId}
              onSelect={onSelect}
            />
          ) : (
            <div className="nav-message">一致するプロジェクトはありません</div>
          )}
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

function ArchivedProjectList({
  projects,
  selectedTestingId,
  onSelect,
}: {
  projects: ProjectItem[]
  selectedTestingId: number | null
  onSelect: (testingId: number) => void
}) {
  return (
    <div className="project-list archived-project-list">
      {projects.map((project) => (
        <button
          key={project.testing_id}
          className={['archived-project-row', project.testing_id === selectedTestingId ? 'selected' : '']
            .filter(Boolean)
            .join(' ')}
          type="button"
          onClick={() => onSelect(project.testing_id)}
          title={`${project.name} (#${project.testing_id})`}
        >
          <LockIcon />
          <span className="archived-project-name">{project.name}</span>
        </button>
      ))}
    </div>
  )
}

function ProjectList({
  projects,
  selectedTestingId,
  onSelect,
  onReorder,
}: {
  projects: ProjectItem[]
  selectedTestingId: number | null
  onSelect: (testingId: number) => void
  onReorder: (testingIds: number[]) => void
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 6,
      },
    }),
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) {
      return
    }
    const sourceIndex = projects.findIndex((project) => project.testing_id === active.id)
    const targetIndex = projects.findIndex((project) => project.testing_id === over.id)
    if (sourceIndex < 0 || targetIndex < 0) {
      return
    }
    const nextProjects = arrayMove(projects, sourceIndex, targetIndex)
    onReorder(nextProjects.map((project) => project.testing_id))
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={projects.map((project) => project.testing_id)} strategy={verticalListSortingStrategy}>
        <div className="project-list">
          {projects.map((project) => (
            <SortableProjectRow
              key={project.testing_id}
              project={project}
              selected={project.testing_id === selectedTestingId}
              onSelect={onSelect}
            />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  )
}

function SortableProjectRow({
  project,
  selected,
  onSelect,
}: {
  project: ProjectItem
  selected: boolean
  onSelect: (testingId: number) => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: project.testing_id,
  })
  const style: CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={setNodeRef}
      className={['project-row', selected ? 'selected' : '', isDragging ? 'dragging' : '']
        .filter(Boolean)
        .join(' ')}
      style={style}
    >
      <span
        className="project-drag-handle"
        title="ドラッグして並び替え"
        {...attributes}
        {...listeners}
      >
        <GripVertical aria-hidden="true" />
      </span>
      <button className="project-row-main" type="button" onClick={() => onSelect(project.testing_id)} title={`${project.name} (#${project.testing_id})`}>
        <span className="project-name-row">
          {project.archived && <LockIcon />}
          <span className="project-name">{project.name}</span>
        </span>
        <span className="project-meta">
          {getProjectStatus(project)}
          {' / '}
          {formatRate(project.actual_completed_rate)}
        </span>
      </button>
    </div>
  )
}
