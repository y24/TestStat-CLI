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
import { GripVertical, FolderKanban, Plus, RefreshCw, Settings } from 'lucide-react'
import type { CSSProperties } from 'react'
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
  onReorder: (testingIds: number[]) => void
  onSettings: () => void
}

export function Sidebar({
  projects,
  selectedTestingId,
  loading,
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
        loading={loading}
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
  loading,
  onSelect,
  onCreate,
  onRefresh,
  onReorder,
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
          onReorder={(testingIds) => {
            onReorder([...testingIds, ...archivedProjects.map((project) => project.testing_id)])
          }}
        />
      )}
      {!loading && archivedProjects.length > 0 && (
        <details className="archived-group">
          <summary>アーカイブ済み ({archivedProjects.length})</summary>
          <ProjectList
            projects={archivedProjects}
            selectedTestingId={selectedTestingId}
            onSelect={onSelect}
            onReorder={(testingIds) => {
              onReorder([...activeProjects.map((project) => project.testing_id), ...testingIds])
            }}
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
      <button className="project-row-main" type="button" onClick={() => onSelect(project.testing_id)}>
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
    </div>
  )
}
