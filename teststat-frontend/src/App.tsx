import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import {
  fetchBugStateColorSettings,
  fetchHealth,
  fetchPbChartSettings,
  fetchProgressStatusThresholds,
  fetchProjects,
  updateProjectOrder,
  updateBugStateColorSettings,
  updatePbChartSettings,
  updateProgressStatusThresholds,
} from './api/client'
import type { BugStateColorSettings, PbChartSettings, ProjectItem } from './api/types'
import { ConfirmDialogProvider } from './components/ConfirmDialog'
import { useConfirmDialog } from './components/confirmDialogContext'
import { PlanEditor } from './components/PlanEditor'
import type { PlanEditorMode } from './components/PlanEditor'
import { ProjectEditor } from './components/ProjectEditor'
import { ProjectOverview } from './components/ProjectOverview'
import { SettingsScreen } from './components/SettingsScreen'
import { Sidebar } from './components/Sidebar'
import type { ApiStatus, ViewMode } from './types/ui'
import { getErrorMessage } from './utils/errors'
import { sortProjects } from './utils/projects'
import { normalizeUrlToBase, readTestingIdFromUrl } from './utils/shareLink'
import {
  DEFAULT_PROGRESS_STATUS_THRESHOLDS,
  type ProgressStatusThresholds,
} from './utils/statusThresholds'
import { getStoredSelectedTestingId, setStoredSelectedTestingId } from './utils/uiStateStorage'

const DEFAULT_BUG_STATE_COLOR_SETTINGS: BugStateColorSettings = {
  items: [
    { state: 'New', background_color: '#f7f9fb', text_color: '#5f6b7a', border_color: '#d8dee8' },
    { state: 'In Progress', background_color: '#eef9ff', text_color: '#0369a1', border_color: '#bae6fd' },
    { state: 'Dev In Progress', background_color: '#f5f0ff', text_color: '#6b46c1', border_color: '#ddd0ff' },
    { state: 'Resolved', background_color: '#e9d5ff', text_color: '#581c87', border_color: '#c084fc' },
    { state: 'Done', background_color: '#edf8f3', text_color: '#147d54', border_color: '#bfdacb' },
    { state: 'Suspend', background_color: '#fff8e6', text_color: '#8a5a00', border_color: '#f5d58a' },
  ],
}

const DISCARD_CONFIRM_OPTIONS = {
  title: '入力内容の破棄',
  message: '編集した内容が保存されていません。画面を離れてもよろしいですか？',
  confirmLabel: 'OK',
  cancelLabel: 'キャンセル',
  danger: true,
} as const

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
  const [collectEnabled, setCollectEnabled] = useState(true)
  const [projects, setProjects] = useState<ProjectItem[]>([])
  const [selectedTestingId, setSelectedTestingId] = useState<number | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('overview')
  const [planMode, setPlanMode] = useState<PlanEditorMode>('list')
  const [loadingProjects, setLoadingProjects] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [progressStatusThresholds, setProgressStatusThresholds] = useState<ProgressStatusThresholds>(
    DEFAULT_PROGRESS_STATUS_THRESHOLDS,
  )
  const [pbChartSettings, setPbChartSettings] = useState<PbChartSettings>({ bug_axis_max: 30 })
  const [bugStateColorSettings, setBugStateColorSettings] = useState<BugStateColorSettings>(
    DEFAULT_BUG_STATE_COLOR_SETTINGS,
  )

  // popstate ハンドラから最新値を同期的に参照するための ref。
  const viewModeRef = useRef(viewMode)
  const planModeRef = useRef(planMode)
  const hasUnsavedChangesRef = useRef(hasUnsavedChanges)

  useEffect(() => {
    viewModeRef.current = viewMode
  }, [viewMode])

  useEffect(() => {
    planModeRef.current = planMode
  }, [planMode])

  const selectedProject = useMemo(
    () => projects.find((project) => project.testing_id === selectedTestingId) ?? null,
    [projects, selectedTestingId],
  )

  // 未保存フラグは state と ref を同時に更新し、popstate から遅延なく読めるようにする。
  const setUnsaved = useCallback((dirty: boolean) => {
    hasUnsavedChangesRef.current = dirty
    setHasUnsavedChanges(dirty)
  }, [])

  // 概要 → サブ画面へ。URL は変えず履歴エントリだけ積む（ブラウザバックで概要へ戻れる）。
  const openSubview = useCallback((view: Exclude<ViewMode, 'overview'>) => {
    const nextPlanMode: PlanEditorMode = 'list'
    const state = view === 'plans' ? { view, planMode: nextPlanMode } : { view }
    if (viewModeRef.current === 'overview') {
      window.history.pushState(state, '')
    } else {
      window.history.replaceState(state, '')
    }
    setViewMode(view)
    setPlanMode(nextPlanMode)
  }, [])

  // 計画一覧 → 計画内サブ画面へ。履歴を一段積み、ブラウザバックで計画一覧へ戻す。
  const openPlanScreen = useCallback((nextPlanMode: Exclude<PlanEditorMode, 'list'>) => {
    if (viewModeRef.current !== 'plans') {
      return
    }
    window.history.pushState({ view: 'plans', planMode: nextPlanMode }, '')
    setPlanMode(nextPlanMode)
  }, [])

  // 現在の画面から一段戻る（計画内サブ画面→計画一覧、計画一覧→概要）。
  const goBackOneLevel = useCallback(() => {
    if (viewModeRef.current === 'overview') {
      return
    }
    window.history.back()
  }, [])

  const goToOverview = useCallback(() => {
    if (viewModeRef.current === 'overview') {
      return
    }
    if (viewModeRef.current === 'plans' && planModeRef.current !== 'list') {
      window.history.go(-2)
      return
    }
    window.history.back()
  }, [])

  const resolveSelectedTestingId = (items: ProjectItem[], preferredTestingId: number | null) => {
    if (preferredTestingId !== null && items.some((item) => item.testing_id === preferredTestingId)) {
      return preferredTestingId
    }
    return items[0]?.testing_id ?? null
  }

  const loadProjects = () => {
    setLoadingProjects(true)
    setError(null)
    fetchProjects()
      .then((items) => {
        setProjects(items)
        const nextSelectedTestingId = resolveSelectedTestingId(items, selectedTestingId)
        setSelectedTestingId(nextSelectedTestingId)
        setStoredSelectedTestingId(nextSelectedTestingId)
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoadingProjects(false))
  }

  useEffect(() => {
    fetchHealth()
      .then((health) => {
        setApiStatus('ok')
        setCollectEnabled(health.collect_enabled)
      })
      .catch(() => setApiStatus('error'))
    // 共有リンク（/tstat/<id>）で開かれた場合は URL の id を初期選択に使う。
    // それ以外は直前選択（localStorage）。判定後、アドレスバーはベースパスへ正規化する。
    const urlTestingId = readTestingIdFromUrl()
    fetchProjects()
      .then((items) => {
        setProjects(items)
        const preferredTestingId = urlTestingId ?? getStoredSelectedTestingId()
        const nextSelectedTestingId = resolveSelectedTestingId(items, preferredTestingId)
        setSelectedTestingId(nextSelectedTestingId)
        setStoredSelectedTestingId(nextSelectedTestingId)
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoadingProjects(false))
    normalizeUrlToBase()
    fetchProgressStatusThresholds()
      .then(setProgressStatusThresholds)
      .catch((err) => setError(getErrorMessage(err)))
    fetchPbChartSettings()
      .then(setPbChartSettings)
      .catch((err) => setError(getErrorMessage(err)))
    fetchBugStateColorSettings()
      .then(setBugStateColorSettings)
      .catch((err) => setError(getErrorMessage(err)))
  }, [])

  // ブラウザの戻る/進む。未保存編集中はここで破棄確認し、キャンセルなら履歴を積み直して留まる。
  useEffect(() => {
    const handlePopState = (event: PopStateEvent) => {
      const targetView = (event.state?.view as ViewMode | undefined) ?? 'overview'
      const targetPlanMode: PlanEditorMode = targetView === 'plans'
        ? (event.state?.planMode as PlanEditorMode | undefined) ?? 'list'
        : 'list'
      const currentView = viewModeRef.current
      const currentPlanMode = planModeRef.current
      if (currentView === targetView && currentPlanMode === targetPlanMode) {
        return
      }
      if (currentView !== 'overview' && hasUnsavedChangesRef.current) {
        void confirm(DISCARD_CONFIRM_OPTIONS).then((confirmed) => {
          if (confirmed) {
            setUnsaved(false)
            setViewMode(targetView)
            setPlanMode(targetPlanMode)
          } else {
            const currentState = currentView === 'plans'
              ? { view: currentView, planMode: currentPlanMode }
              : { view: currentView }
            window.history.pushState(currentState, '')
          }
        })
        return
      }
      setViewMode(targetView)
      setPlanMode(targetPlanMode)
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [confirm, setUnsaved])

  const confirmDiscardChanges = useCallback(async () => {
    if (!hasUnsavedChanges) {
      return true
    }
    return confirm(DISCARD_CONFIRM_OPTIONS)
  }, [confirm, hasUnsavedChanges])

  const runAfterDiscardConfirmation = useCallback(
    async (action: () => void) => {
      const confirmed = await confirmDiscardChanges()
      if (!confirmed) {
        return
      }
      setUnsaved(false)
      action()
    },
    [confirmDiscardChanges, setUnsaved],
  )

  // タブ閉じ・リロード時の警告（ブラウザバックは上の popstate で別途ガード）。
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

  const handleProjectUpdated = (project: ProjectItem) => {
    setProjects((current) => {
      const exists = current.some((item) => item.testing_id === project.testing_id)
      const next = exists
        ? current.map((item) => (item.testing_id === project.testing_id ? project : item))
        : [project, ...current]
      return sortProjects(next)
    })
    setSelectedTestingId(project.testing_id)
    setStoredSelectedTestingId(project.testing_id)
  }

  const handleProjectSaved = (project: ProjectItem) => {
    setUnsaved(false)
    handleProjectUpdated(project)
    goToOverview()
  }

  const handleDeleted = (testingId: number) => {
    setUnsaved(false)
    const nextProjects = projects.filter((item) => item.testing_id !== testingId)
    const nextSelectedTestingId =
      selectedTestingId === testingId
        ? resolveSelectedTestingId(nextProjects, null)
        : resolveSelectedTestingId(nextProjects, selectedTestingId)
    setProjects(nextProjects)
    setSelectedTestingId(nextSelectedTestingId)
    setStoredSelectedTestingId(nextSelectedTestingId)
    goToOverview()
  }

  const handleProjectReorder = (orderedTestingIds: number[]) => {
    const orderedIdSet = new Set(orderedTestingIds)
    const reorderedProjects = orderedTestingIds
      .map((testingId, index) => {
        const project = projects.find((item) => item.testing_id === testingId)
        return project ? { ...project, display_order: index } : null
      })
      .filter((project): project is ProjectItem => project !== null)
    const remainingProjects = projects
      .filter((project) => !orderedIdSet.has(project.testing_id))
      .map((project, index) => ({ ...project, display_order: orderedTestingIds.length + index }))
    const optimisticProjects = sortProjects([...reorderedProjects, ...remainingProjects])

    setProjects(optimisticProjects)
    updateProjectOrder({ testing_ids: optimisticProjects.map((project) => project.testing_id) })
      .then(setProjects)
      .catch((err) => {
        setError(getErrorMessage(err))
        loadProjects()
      })
  }

  const handleProgressStatusThresholdsChange = async (thresholds: ProgressStatusThresholds) => {
    const saved = await updateProgressStatusThresholds(thresholds)
    setProgressStatusThresholds(saved)
    return saved
  }

  const handlePbChartSettingsChange = async (settings: PbChartSettings) => {
    const saved = await updatePbChartSettings(settings)
    setPbChartSettings(saved)
    return saved
  }

  const handleBugStateColorSettingsChange = async (settings: BugStateColorSettings) => {
    const saved = await updateBugStateColorSettings(settings)
    setBugStateColorSettings(saved)
    return saved
  }

  return (
    <div className="app-layout" aria-busy={loadingProjects}>
      <Sidebar
        apiStatus={apiStatus}
        projects={projects}
        selectedTestingId={selectedTestingId}
        loading={loadingProjects}
        onSelect={(testingId) => {
          void runAfterDiscardConfirmation(() => {
            setSelectedTestingId(testingId)
            setStoredSelectedTestingId(testingId)
            goToOverview()
          })
        }}
        onCreate={() => {
          void runAfterDiscardConfirmation(() => openSubview('new'))
        }}
        onRefresh={loadProjects}
        onReorder={handleProjectReorder}
        onSettings={() => {
          void runAfterDiscardConfirmation(() => openSubview('settings'))
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
                  void runAfterDiscardConfirmation(goToOverview)
                }}
                onSaved={handleProjectSaved}
                onDirtyChange={setUnsaved}
              />
            )}
            {viewMode === 'edit' && selectedProject && (
              <ProjectEditor
                mode="edit"
                project={selectedProject}
                onCancel={() => {
                  void runAfterDiscardConfirmation(goToOverview)
                }}
                onSaved={handleProjectSaved}
                onProjectUpdated={handleProjectUpdated}
                onDeleted={handleDeleted}
                onDirtyChange={setUnsaved}
              />
            )}
            {viewMode === 'overview' && (
              <ProjectOverview
                project={selectedProject}
                progressStatusThresholds={progressStatusThresholds}
                pbChartSettings={pbChartSettings}
                bugStateColorSettings={bugStateColorSettings}
                onCreate={() => openSubview('new')}
                onEdit={() => openSubview('edit')}
                onPlans={() => openSubview('plans')}
              />
            )}
            {viewMode === 'plans' && selectedProject && (
              <PlanEditor
                project={selectedProject}
                mode={planMode}
                collectEnabled={collectEnabled}
                onBack={goBackOneLevel}
                onOpenScreen={openPlanScreen}
                onChanged={loadProjects}
                onDirtyChange={setUnsaved}
              />
            )}
            {viewMode === 'settings' && (
              <SettingsScreen
                key={`${progressStatusThresholds.caution}-${progressStatusThresholds.warning}-${pbChartSettings.bug_axis_max}-${JSON.stringify(bugStateColorSettings.items)}`}
                progressStatusThresholds={progressStatusThresholds}
                pbChartSettings={pbChartSettings}
                bugStateColorSettings={bugStateColorSettings}
                onProgressStatusThresholdsChange={handleProgressStatusThresholdsChange}
                onPbChartSettingsChange={handlePbChartSettingsChange}
                onBugStateColorSettingsChange={handleBugStateColorSettingsChange}
              />
            )}
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
