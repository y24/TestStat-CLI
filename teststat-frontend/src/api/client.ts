import type {
  HealthResponse,
  TestingItem,
  ProgressSummaryResponse,
  FileProgressItem,
  DailyProgressItem,
  ProjectCreatePayload,
  ProjectItem,
  ProjectOrderUpdatePayload,
  ProjectUpdatePayload,
  PbChartResponse,
  PlanCreatePayload,
  PlanLabelCreatePayload,
  PlanLabelItem,
  PlanLabelUpdatePayload,
  ProjectLabelUpdatePayload,
  PlanDetail,
  PlanItem,
  HolidayItem,
  HolidayCreatePayload,
  HolidaySyncResult,
  ProgressStatusThresholds,
  AzureDevOpsWorkItem,
  BugSyncResult,
  OpenBugItem,
} from './types'

// 本番では IIS の /tstat 配下で同一オリジン配信し、/tstat/api と /tstat/health を
// バックエンドへリバースプロキシする。開発時も vite.config の proxy が同じパスを転送する。
const BASE = (import.meta.env.VITE_API_BASE_PATH || '').replace(/\/$/, '')

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}${text ? ': ' + text : ''}`)
  }
  return res.json() as Promise<T>
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init.headers,
    },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}${text ? ': ' + text : ''}`)
  }
  if (res.status === 204) {
    return undefined as T
  }
  return res.json() as Promise<T>
}

// ヘルスチェック
export const fetchHealth = () => get<HealthResponse>('/health')

// 実績系（既存バックエンド）
export const fetchTestings = () => get<TestingItem[]>('/api/v1/testings')
export const fetchProgressSummary = (testing_id: number) =>
  get<ProgressSummaryResponse>(`/api/v1/progress/${testing_id}`)
export const fetchProgressFiles = (testing_id: number) =>
  get<FileProgressItem[]>(`/api/v1/progress/${testing_id}/files`)
export const fetchProgressDaily = (testing_id: number) =>
  get<DailyProgressItem[]>(`/api/v1/progress/${testing_id}/daily`)

function withProjectActualFallback(project: ProjectItem, summary?: ProgressSummaryResponse): ProjectItem {
  return {
    ...project,
    actual_available_cases: project.actual_available_cases ?? summary?.summary.available_cases ?? 0,
    actual_completed: project.actual_completed ?? summary?.summary.completed ?? 0,
    actual_completed_rate: project.actual_completed_rate ?? summary?.summary.completed_rate ?? 0,
    actual_vs_plan_rate: project.actual_vs_plan_rate ?? null,
    actual_all_completed:
      project.actual_all_completed ??
      Boolean(summary && summary.summary.available_cases > 0 && summary.summary.completed_rate >= 100),
  }
}

async function enrichProjectActuals(project: ProjectItem): Promise<ProjectItem> {
  if (
    !project.has_actuals ||
    (project.actual_available_cases != null &&
      project.actual_completed != null &&
      project.actual_completed_rate != null &&
      project.actual_vs_plan_rate !== undefined &&
      project.actual_all_completed != null)
  ) {
    return withProjectActualFallback(project)
  }
  const summary = await fetchProgressSummary(project.testing_id).catch(() => undefined)
  return withProjectActualFallback(project, summary)
}

// プロジェクト系（Phase F1）
export const fetchProjects = async () => {
  const projects = await get<ProjectItem[]>('/api/v1/projects')
  return Promise.all(projects.map(enrichProjectActuals))
}
export const createProject = (payload: ProjectCreatePayload) =>
  request<ProjectItem>('/api/v1/projects', {
    method: 'POST',
    body: JSON.stringify(payload),
  }).then(enrichProjectActuals)
export const updateProject = (testing_id: number, payload: ProjectUpdatePayload) =>
  request<ProjectItem>(`/api/v1/projects/${testing_id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  }).then(enrichProjectActuals)
export const updateProjectOrder = async (payload: ProjectOrderUpdatePayload) => {
  const projects = await request<ProjectItem[]>('/api/v1/projects/order', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
  return Promise.all(projects.map(enrichProjectActuals))
}
export const deleteProject = (testing_id: number) =>
  request<void>(`/api/v1/projects/${testing_id}`, {
    method: 'DELETE',
  })

// PB図（Phase F2/F4）
export const fetchPbChart = (
  testing_id: number,
  options: { label?: string | null; includePastPlans?: boolean } = {},
) => {
  const params = new URLSearchParams()
  if (options.label) {
    params.set('label', options.label)
  }
  if (options.includePastPlans) {
    params.set('include_past_plans', 'true')
  }
  const query = params.toString()
  return get<PbChartResponse>(`/api/v1/projects/${testing_id}/pb-chart${query ? `?${query}` : ''}`)
}

// 計画編集（Phase F3）
export const fetchPlans = (testing_id: number) =>
  get<PlanItem[]>(`/api/v1/projects/${testing_id}/plans`)
export const fetchPlanLabels = (testing_id: number) =>
  get<PlanLabelItem[]>(`/api/v1/projects/${testing_id}/plan-labels`)
export const createPlanLabel = (testing_id: number, payload: PlanLabelCreatePayload) =>
  request<PlanLabelItem>(`/api/v1/projects/${testing_id}/plan-labels`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
export const updateProjectLabel = (testing_id: number, payload: ProjectLabelUpdatePayload) =>
  request<PlanLabelItem>(`/api/v1/projects/${testing_id}/labels`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
export const deleteProjectLabel = (testing_id: number, label: string) => {
  const params = new URLSearchParams({ label })
  return request<void>(`/api/v1/projects/${testing_id}/labels?${params.toString()}`, {
    method: 'DELETE',
  })
}
export const updatePlanLabel = (label_id: number, payload: PlanLabelUpdatePayload) =>
  request<PlanLabelItem>(`/api/v1/plan-labels/${label_id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
export const deletePlanLabel = (label_id: number) =>
  request<void>(`/api/v1/plan-labels/${label_id}`, {
    method: 'DELETE',
  })
export const createPlan = (testing_id: number, payload: PlanCreatePayload) =>
  request<PlanDetail>(`/api/v1/projects/${testing_id}/plans`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
export const activatePlan = (plan_id: number) =>
  request<PlanItem>(`/api/v1/plans/${plan_id}/activate`, {
    method: 'POST',
  })
export const deletePlan = (plan_id: number) =>
  request<void>(`/api/v1/plans/${plan_id}`, {
    method: 'DELETE',
  })

// 設定: 祝日一覧
export const fetchHolidays = () => get<HolidayItem[]>('/api/v1/holidays')
export const createHoliday = (payload: HolidayCreatePayload) =>
  request<HolidayItem>('/api/v1/holidays', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
export const syncHolidays = () =>
  request<HolidaySyncResult>('/api/v1/holidays/sync', {
    method: 'POST',
  })

// Azure DevOps 連携: Work Item 取得
export const fetchAzureDevOpsWorkItem = (work_item_id: number) =>
  get<AzureDevOpsWorkItem>(`/api/v1/azure-devops/work-items/${work_item_id}`)

// Azure DevOps 連携: 子チケット(Bug)を取得して洗替（Testing ID 単位）
export const syncAzureDevOpsBugs = (testing_id: number) =>
  request<BugSyncResult>(`/api/v1/projects/${testing_id}/bugs/sync`, { method: 'POST' })

export const fetchOpenBugs = (testing_id: number) =>
  get<OpenBugItem[]>(`/api/v1/projects/${testing_id}/bugs/open`)

// 設定: 進捗状態しきい値
export const fetchProgressStatusThresholds = () =>
  get<ProgressStatusThresholds>('/api/v1/settings/progress-status-thresholds')
export const updateProgressStatusThresholds = (payload: ProgressStatusThresholds) =>
  request<ProgressStatusThresholds>('/api/v1/settings/progress-status-thresholds', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
