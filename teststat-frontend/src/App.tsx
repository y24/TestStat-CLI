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
import { Dashboard } from './components/Dashboard'
import { PlanEditor } from './components/PlanEditor'
import type { PlanEditorMode } from './components/PlanEditor'
import { ProjectEditor } from './components/ProjectEditor'
import { ProjectOverview } from './components/ProjectOverview'
import { SettingsScreen } from './components/SettingsScreen'
import { Sidebar } from './components/Sidebar'
import type { ApiStatus, ViewMode } from './types/ui'
import { getErrorMessage } from './utils/errors'
import { sortProjects } from './utils/projects'
import { buildDashboardPath, buildProjectPath, readTestingIdFromUrl } from './utils/shareLink'
import {
  DEFAULT_PROGRESS_STATUS_THRESHOLDS,
  type ProgressStatusThresholds,
} from './utils/statusThresholds'
import { setStoredSelectedTestingId } from './utils/uiStateStorage'

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

// アプリ内ロケーション。履歴 state として保存し、popstate で復元する。
interface AppLocation {
  view: ViewMode
  planMode: PlanEditorMode
  testingId: number | null
}

// 個別プロジェクトに紐づく画面（アドレスバーを /tstat/<id> にする）。
const PROJECT_SCOPED_VIEWS: ReadonlySet<ViewMode> = new Set(['overview', 'plans', 'edit'])

function locationPath(view: ViewMode, testingId: number | null): string {
  return PROJECT_SCOPED_VIEWS.has(view) && testingId != null
    ? buildProjectPath(testingId)
    : buildDashboardPath()
}

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
  const [viewMode, setViewMode] = useState<ViewMode>('dashboard')
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
  const selectedTestingIdRef = useRef(selectedTestingId)
  const hasUnsavedChangesRef = useRef(hasUnsavedChanges)

  useEffect(() => {
    viewModeRef.current = viewMode
  }, [viewMode])

  useEffect(() => {
    planModeRef.current = planMode
  }, [planMode])

  useEffect(() => {
    selectedTestingIdRef.current = selectedTestingId
  }, [selectedTestingId])

  const selectedProject = useMemo(
    () => projects.find((project) => project.testing_id === selectedTestingId) ?? null,
    [projects, selectedTestingId],
  )

  // 未保存フラグは state と ref を同時に更新し、popstate から遅延なく読めるようにする。
  const setUnsaved = useCallback((dirty: boolean) => {
    hasUnsavedChangesRef.current = dirty
    setHasUnsavedChanges(dirty)
  }, [])

  // ロケーションを React state へ反映する（履歴操作は呼び出し側が行う）。
  const applyLocation = useCallback((loc: AppLocation) => {
    setViewMode(loc.view)
    setPlanMode(loc.planMode)
    setSelectedTestingId(loc.testingId)
    if (loc.testingId != null) {
      setStoredSelectedTestingId(loc.testingId)
    }
  }, [])

  // 履歴エントリを積み（pushState）アドレスバーも更新したうえで画面を切り替える。
  const pushLocation = useCallback(
    (loc: AppLocation) => {
      window.history.pushState(loc, '', locationPath(loc.view, loc.testingId))
      applyLocation(loc)
    },
    [applyLocation],
  )

  // 現在の履歴エントリを置き換えて（replaceState）画面を切り替える。
  const replaceLocation = useCallback(
    (loc: AppLocation) => {
      window.history.replaceState(loc, '', locationPath(loc.view, loc.testingId))
      applyLocation(loc)
    },
    [applyLocation],
  )

  // ダッシュボード（俯瞰ビュー）へ。アドレスバーは /tstat/ になる。
  const goToDashboard = useCallback(() => {
    pushLocation({ view: 'dashboard', planMode: 'list', testingId: null })
  }, [pushLocation])

  // 個別プロジェクトの概要（PB 図）へ。アドレスバーは /tstat/<id> になる。
  const openProjectOverview = useCallback(
    (testingId: number, mode: 'push' | 'replace' = 'push') => {
      const loc: AppLocation = { view: 'overview', planMode: 'list', testingId }
      if (mode === 'replace') {
        replaceLocation(loc)
      } else {
        pushLocation(loc)
      }
    },
    [pushLocation, replaceLocation],
  )

  // 概要/ダッシュボード → サブ画面（新規・編集・計画・設定）へ。現在の選択を引き継ぐ。
  const openSubview = useCallback(
    (view: Exclude<ViewMode, 'overview' | 'dashboard'>) => {
      pushLocation({ view, planMode: 'list', testingId: selectedTestingIdRef.current })
    },
    [pushLocation],
  )

  // 計画一覧 → 計画内サブ画面へ。履歴を一段積み、ブラウザバックで計画一覧へ戻す。
  const openPlanScreen = useCallback(
    (nextPlanMode: Exclude<PlanEditorMode, 'list'>) => {
      if (viewModeRef.current !== 'plans') {
        return
      }
      pushLocation({ view: 'plans', planMode: nextPlanMode, testingId: selectedTestingIdRef.current })
    },
    [pushLocation],
  )

  // 一段戻る（ブラウザの戻ると同じ。popstate で直前のロケーションを復元する）。
  const goBack = useCallback(() => {
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
        // ダッシュボード表示中は特定プロジェクトを選択状態にしない。
        if (viewModeRef.current !== 'dashboard') {
          const nextSelectedTestingId = resolveSelectedTestingId(items, selectedTestingId)
          setSelectedTestingId(nextSelectedTestingId)
          setStoredSelectedTestingId(nextSelectedTestingId)
        }
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
    // /tstat/<id> で開かれ、その id が存在すれば個別プロジェクトの概要を表示。
    // /tstat/（または存在しない id）なら既定でダッシュボードを表示する。
    // 初期ロケーションは replaceState で履歴に記録し、戻る操作で復元できるようにする。
    const urlTestingId = readTestingIdFromUrl()
    fetchProjects()
      .then((items) => {
        setProjects(items)
        const initialLocation: AppLocation =
          urlTestingId != null && items.some((item) => item.testing_id === urlTestingId)
            ? { view: 'overview', planMode: 'list', testingId: urlTestingId }
            : { view: 'dashboard', planMode: 'list', testingId: null }
        window.history.replaceState(
          initialLocation,
          '',
          locationPath(initialLocation.view, initialLocation.testingId),
        )
        setViewMode(initialLocation.view)
        setPlanMode(initialLocation.planMode)
        setSelectedTestingId(initialLocation.testingId)
        if (initialLocation.testingId != null) {
          setStoredSelectedTestingId(initialLocation.testingId)
        }
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoadingProjects(false))
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
      const fallbackTestingId = readTestingIdFromUrl()
      const target: AppLocation = (event.state as AppLocation | null) ?? {
        view: fallbackTestingId != null ? 'overview' : 'dashboard',
        planMode: 'list',
        testingId: fallbackTestingId,
      }
      const current: AppLocation = {
        view: viewModeRef.current,
        planMode: planModeRef.current,
        testingId: selectedTestingIdRef.current,
      }
      if (
        target.view === current.view &&
        target.planMode === current.planMode &&
        target.testingId === current.testingId
      ) {
        return
      }
      if (hasUnsavedChangesRef.current) {
        void confirm(DISCARD_CONFIRM_OPTIONS).then((confirmed) => {
          if (confirmed) {
            setUnsaved(false)
            applyLocation(target)
          } else {
            // 戻る操作を取り消し、現在のロケーションを履歴に積み直す。
            window.history.pushState(current, '', locationPath(current.view, current.testingId))
          }
        })
        return
      }
      applyLocation(target)
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [confirm, setUnsaved, applyLocation])

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
    // 編集画面のエントリを概要で置き換え、保存したプロジェクトの PB 図を表示する。
    openProjectOverview(project.testing_id, 'replace')
  }

  const handleDeleted = (testingId: number) => {
    setUnsaved(false)
    setProjects((current) => current.filter((item) => item.testing_id !== testingId))
    // 削除後は対象が存在しないため、ダッシュボードへ戻す。
    replaceLocation({ view: 'dashboard', planMode: 'list', testingId: null })
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
        selectedTestingId={viewMode === 'dashboard' ? null : selectedTestingId}
        dashboardActive={viewMode === 'dashboard'}
        loading={loadingProjects}
        onDashboard={() => {
          void runAfterDiscardConfirmation(goToDashboard)
        }}
        onSelect={(testingId) => {
          void runAfterDiscardConfirmation(() => openProjectOverview(testingId))
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
            {viewMode === 'dashboard' && (
              <Dashboard
                projects={projects}
                onOpenProject={openProjectOverview}
                onCreate={() => openSubview('new')}
              />
            )}
            {viewMode === 'new' && (
              <ProjectEditor
                mode="new"
                project={null}
                onCancel={() => {
                  void runAfterDiscardConfirmation(goBack)
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
                  void runAfterDiscardConfirmation(goBack)
                }}
                onSaved={handleProjectSaved}
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
                onBack={goToDashboard}
                onCreate={() => openSubview('new')}
                onEdit={() => openSubview('edit')}
                onPlans={() => openSubview('plans')}
                onProjectUpdate={handleProjectUpdated}
              />
            )}
            {viewMode === 'plans' && selectedProject && (
              <PlanEditor
                project={selectedProject}
                mode={planMode}
                collectEnabled={collectEnabled}
                onBack={goBack}
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
