import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { fetchHealth, fetchProjects } from './api/client'
import type { ProjectItem } from './api/types'
import { PlanEditor } from './components/PlanEditor'
import { ProjectEditor } from './components/ProjectEditor'
import { ProjectOverview } from './components/ProjectOverview'
import { SettingsScreen } from './components/SettingsScreen'
import { Sidebar } from './components/Sidebar'
import type { ApiStatus, ViewMode } from './types/ui'
import { getErrorMessage } from './utils/errors'
import { sortProjects } from './utils/projects'

export default function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const [projects, setProjects] = useState<ProjectItem[]>([])
  const [selectedTestingId, setSelectedTestingId] = useState<number | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('overview')
  const [loadingProjects, setLoadingProjects] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

  const handleProjectSaved = (project: ProjectItem) => {
    setProjects((current) => {
      const exists = current.some((item) => item.testing_id === project.testing_id)
      const next = exists
        ? current.map((item) => (item.testing_id === project.testing_id ? project : item))
        : [project, ...current]
      return sortProjects(next)
    })
    setSelectedTestingId(project.testing_id)
    setViewMode('overview')
  }

  const handleDeleted = (testingId: number) => {
    setProjects((current) => current.filter((item) => item.testing_id !== testingId))
    setSelectedTestingId((current) => (current === testingId ? null : current))
    setViewMode('overview')
  }

  return (
    <div className="app-layout">
      <Sidebar
        apiStatus={apiStatus}
        projects={projects}
        selectedTestingId={selectedTestingId}
        loading={loadingProjects}
        onSelect={(testingId) => {
          setSelectedTestingId(testingId)
          setViewMode('overview')
        }}
        onCreate={() => {
          setSelectedTestingId(null)
          setViewMode('new')
        }}
        onRefresh={loadProjects}
        onSettings={() => setViewMode('settings')}
      />
      <main className="main-area">
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
            onCancel={() => setViewMode(selectedProject ? 'overview' : 'new')}
            onSaved={handleProjectSaved}
          />
        )}
        {viewMode === 'edit' && selectedProject && (
          <ProjectEditor
            mode="edit"
            project={selectedProject}
            onCancel={() => setViewMode('overview')}
            onSaved={handleProjectSaved}
            onDeleted={handleDeleted}
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
            onBack={() => setViewMode('overview')}
            onChanged={loadProjects}
          />
        )}
        {viewMode === 'settings' && <SettingsScreen />}
      </main>
    </div>
  )
}
