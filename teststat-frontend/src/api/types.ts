// === 実績系（既存バックエンド） ===

export interface TestingItem {
  testing_id: number
  project_name: string
  created_at: string
  updated_at: string
}

export interface SummaryCounts {
  total_cases: number
  available_cases: number
  completed: number
  executed: number
  completed_rate: number
  executed_rate: number
}

export interface ResultCounts {
  Pass: number
  Fixed: number
  Fail: number
  Blocked: number
  Suspend: number
  'N/A': number
}

export interface ProgressSummaryResponse {
  testing_id: number
  project_name: string
  updated_at: string
  summary: SummaryCounts
  results: ResultCounts
}

export interface FileProgressItem {
  file_name: string
  label: string | null
  environment: string | null
  total_cases: number
  available_cases: number
  completed: number
  executed: number
  completed_rate: number
  executed_rate: number
  start_date: string | null
  latest_update: string | null
  sender: string | null
  sent_at: string
}

export interface DailyProgressItem extends ResultCounts {
  date: string
  file_name: string
  label: string | null
  environment: string | null
  completed: number
  executed: number
  planned: number | null
}

export interface HealthResponse {
  status: string
  db: string
}

export interface HolidayItem {
  date: string
  name: string
}

export interface HolidayCreatePayload {
  date: string
  name: string
}

export interface HolidaySyncResult {
  updated: number
  holidays: HolidayItem[]
}

export interface ProgressStatusThresholds {
  caution: number
  warning: number
}

// === Azure DevOps 連携 ===

export interface AzureDevOpsWorkItem {
  work_item_id: number
  name: string
  start_date: string | null
  end_date: string | null
}

// === 計画系（フロント新設バックエンド。Phase B1〜B3 で実装後に使う） ===

export interface ProjectItem {
  testing_id: number
  name: string
  ticket_ref: string | null
  planned_start_date: string | null
  planned_end_date: string | null
  archived: boolean
  display_order: number
  created_at: string
  updated_at: string
  has_actuals: boolean
  actuals_updated_at: string | null
  actual_available_cases: number
  actual_completed: number
  actual_completed_rate: number
  actual_vs_plan_rate: number | null
  actual_all_completed: boolean
  active_plan_count: number
}

export interface ProjectCreatePayload {
  testing_id: number
  name: string
  ticket_ref?: string | null
  planned_start_date?: string | null
  planned_end_date?: string | null
}

export interface ProjectUpdatePayload {
  name?: string
  ticket_ref?: string | null
  planned_start_date?: string | null
  planned_end_date?: string | null
  archived?: boolean
}

export interface ProjectOrderUpdatePayload {
  testing_ids: number[]
}

export interface PlanItem {
  id: number
  testing_id: number
  label: string | null
  version: number
  is_active: boolean
  reason: string | null
  planned_total_cases: number
  start_date: string
  end_date: string
  created_at: string
  created_by: string | null
  daily_total: number
}

export interface PlanDailyItem {
  date: string
  planned_count: number
}

export interface PlanDetail extends PlanItem {
  daily: PlanDailyItem[]
}

export interface PlanCreatePayload {
  label?: string | null
  reason?: string | null
  planned_total_cases: number
  start_date: string
  end_date: string
  activate: boolean
  daily: PlanDailyItem[]
  created_by?: string | null
}

export interface PbChartSeries {
  date: string
  planned_remaining: number | null
  actual_remaining: number | null
  planned_completed_daily: number | null
  actual_completed_daily: number | null
  bug_open: number | null
  bug_suspended: number | null
  bug_resolved: number | null
}

export interface PbChartPastPlan {
  plan_id: number
  version: number
  label: string | null
  reason: string | null
  planned_total_cases: number
  series: Array<{ date: string; planned_remaining: number; planned_completed_daily: number }>
}

export interface PbChartResponse {
  testing_id: number
  label: string | null
  range: { from: string; to: string } | null
  actuals_updated_at: string | null
  available_cases: number
  planned_total_cases: number | null
  series: PbChartSeries[]
  past_plans: PbChartPastPlan[]
  has_bugs: boolean
  bugs_updated_at: string | null
}

export interface BugSyncResult {
  testing_id: number
  fetched: number
  open_count: number
  suspended_count: number
  resolved_count: number
  fetched_at: string
}

export interface OpenBugItem {
  work_item_id: number
  title: string | null
  state: string | null
  url: string | null
}
