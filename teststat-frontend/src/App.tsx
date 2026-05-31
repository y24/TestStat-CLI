import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'
import { fetchHealth, fetchProjects } from './api/client'
import type { ProjectItem } from './api/types'
import { ConfirmDialogProvider } from './components/ConfirmDialog'
import { useConfirmDialog } from './components/confirmDialogContext'
import { PlanEditor } from './components/PlanEditor'
import { ProjectEditor } from './components/ProjectEditor'
import { ProjectOverview } from './components/ProjectOverview'
import { SettingsScreen } from './components/SettingsScreen'
import { Sidebar } from './components/Sidebar'
import type { ApiStatus, ViewMode } from './types/ui'
import { getErrorMessage } from './utils/errors'
import { sortProjects } from './utils/projects'

export default function App() {
  return (
    <ConfirmDialogProvider>
      <AppContent />
    </ConfirmDialogProvider>
  )
}

function AppContent() {
  const confirm = useConfirmDialog()
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const [projects, setProjects] = useState<ProjectItem[]>([])
  const [selectedTestingId, setSelectedTestingId] = useState<number | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('overview')
  const [loadingProjects, setLoadingProjects] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

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

  const confirmDiscardChanges = useCallback(async () => {
    if (!hasUnsavedChanges) {
      return true
    }
    return confirm({
      title: '入力内容の破棄',
      message: '編集した内容が保存されていません。画面を離れてもよろしいですか？',
      confirmLabel: 'OK',
      cancelLabel: 'キャンセル',
      danger: true,
    })
  }, [confirm, hasUnsavedChanges])

  const runAfterDiscardConfirmation = useCallback(
    async (action: () => void) => {
      const confirmed = await confirmDiscardChanges()
      if (!confirmed) {
        return
      }
      setHasUnsavedChanges(false)
      action()
    },
    [confirmDiscardChanges],
  )

  useEffect(() => {
    if (!hasUnsavedChanges) {
      return
    }

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [hasUnsavedChanges])

  const handleProjectSaved = (project: ProjectItem) => {
    setHasUnsavedChanges(false)
    handleProjectUpdated(project)
    setViewMode('overview')
  }

  const handleProjectUpdated = (project: ProjectItem) => {
    setProjects((current) => {
      const exists = current.some((item) => item.testing_id === project.testing_id)
      const next = exists
        ? current.map((item) => (item.testing_id === project.testing_id ? project : item))
        : [project, ...current]
      return sortProjects(next)
    })
    setSelectedTestingId(project.testing_id)
  }

  const handleDeleted = (testingId: number) => {
    setHasUnsavedChanges(false)
    setProjects((current) => current.filter((item) => item.testing_id !== testingId))
    setSelectedTestingId((current) => (current === testingId ? null : current))
    setViewMode('overview')
  }

  return (
    <div className="app-layout" aria-busy={loadingProjects}>
      <Sidebar
        apiStatus={apiStatus}
        projects={projects}
        selectedTestingId={selectedTestingId}
        viewMode={viewMode}
        loading={loadingProjects}
        onSelect={(testingId) => {
          void runAfterDiscardConfirmation(() => {
            setSelectedTestingId(testingId)
            setViewMode('overview')
          })
        }}
        onCreate={() => {
          void runAfterDiscardConfirmation(() => setViewMode('new'))
        }}
        onRefresh={loadProjects}
        onPbChart={() => {
          void runAfterDiscardConfirmation(() => setViewMode('overview'))
        }}
        onSettings={() => {
          void runAfterDiscardConfirmation(() => setViewMode('settings'))
        }}
      />
      <main className="main-area">
        {loadingProjects ? (
          <ProjectLoading />
        ) : (
          <>
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
                onCancel={() => {
                  void runAfterDiscardConfirmation(() => setViewMode('overview'))
                }}
                onSaved={handleProjectSaved}
                onDirtyChange={setHasUnsavedChanges}
              />
            )}
            {viewMode === 'edit' && selectedProject && (
              <ProjectEditor
                mode="edit"
                project={selectedProject}
                onCancel={() => {
                  void runAfterDiscardConfirmation(() => setViewMode('overview'))
                }}
                onSaved={handleProjectSaved}
                onProjectUpdated={handleProjectUpdated}
                onDeleted={handleDeleted}
                onDirtyChange={setHasUnsavedChanges}
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
                onBack={() => {
                  void runAfterDiscardConfirmation(() => setViewMode('overview'))
                }}
                onChanged={loadProjects}
                onDirtyChange={setHasUnsavedChanges}
              />
            )}
            {viewMode === 'settings' && <SettingsScreen />}
          </>
        )}
      </main>
    </div>
  )
}

function ProjectLoading() {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <div className="loading-spinner" aria-hidden="true" />
      <div>プロジェクトを読み込み中...</div>
    </div>
  )
}
