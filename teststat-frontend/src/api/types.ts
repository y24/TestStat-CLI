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
  completed?: number
  executed?: number
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
  result_na: number
  completed: number
  executed: number
  completed_rate: number
  executed_rate: number
  start_date: string | null
  latest_update: string | null
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

export interface PersonProgressItem {
  date: string
  label: string | null
  person: string
  count: number
  completed?: number
  executed?: number
}

export interface HealthResponse {
  status: string
  db: string
  collect_enabled: boolean
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

export interface PbChartSettings {
  bug_axis_max: number
}

export interface BugStateColorSetting {
  state: string
  background_color: string
  text_color: string
  border_color: string
}

export interface BugStateColorSettings {
  items: BugStateColorSetting[]
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
  bug_count_source: 'azure_devops' | 'test_result'
  bug_parent_work_item_id: number | null
  bug_work_item_type: string | null
  bug_tag: string | null
  pb_chart_range_source: 'plan_actual' | 'project_period'
  bug_axis_max: number | null
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
  actual_vs_plan_delay_days: number | null
  actual_all_completed: boolean
  active_plan_count: number
}

export interface ProjectCreatePayload {
  testing_id: number
  name: string
  ticket_ref?: string | null
  planned_start_date?: string | null
  planned_end_date?: string | null
  bug_count_source?: 'azure_devops' | 'test_result'
  bug_parent_work_item_id?: number | null
  bug_work_item_type?: string | null
  bug_tag?: string | null
  pb_chart_range_source?: 'plan_actual' | 'project_period'
  bug_axis_max?: number | null
}

export interface ProjectUpdatePayload {
  name?: string
  ticket_ref?: string | null
  planned_start_date?: string | null
  planned_end_date?: string | null
  bug_count_source?: 'azure_devops' | 'test_result'
  bug_parent_work_item_id?: number | null
  bug_work_item_type?: string | null
  bug_tag?: string | null
  pb_chart_range_source?: 'plan_actual' | 'project_period'
  bug_axis_max?: number | null
  archived?: boolean
}

export interface ProjectOrderUpdatePayload {
  testing_ids: number[]
}

export interface PlanLabelItem {
  id: number
  testing_id: number
  label: string
  is_disabled: boolean
  use_plan_as_actual_offset: boolean
  source_url: string | null
  subtask_id: number | null
  target_sheets: string[] | null
  ignore_sheets: string[] | null
  include_hidden_sheets: boolean | null
  target_environments: string[] | null
  ignore_environments: string[] | null
  display_order: number
  created_at: string
}

export interface PlanLabelCliOptionsPayload {
  target_sheets?: string[] | null
  ignore_sheets?: string[] | null
  include_hidden_sheets?: boolean | null
  target_environments?: string[] | null
  ignore_environments?: string[] | null
}

export interface PlanLabelCreatePayload extends PlanLabelCliOptionsPayload {
  label: string
  is_disabled?: boolean
  use_plan_as_actual_offset?: boolean
  source_url?: string | null
  subtask_id?: number | null
}

export type PlanLabelUpdatePayload = PlanLabelCreatePayload

export interface PlanLabelOrderUpdatePayload {
  label_ids?: number[]
  labels?: string[]
}

export interface ProjectLabelUpdatePayload extends PlanLabelCliOptionsPayload {
  old_label: string
  label: string
  is_disabled?: boolean
  use_plan_as_actual_offset?: boolean
  source_url?: string | null
  subtask_id?: number | null
}

export interface LabelEditTarget {
  id?: number
  label: string
  is_disabled?: boolean
  use_plan_as_actual_offset?: boolean
  source_url?: string | null
  subtask_id?: number | null
  target_sheets?: string[] | null
  ignore_sheets?: string[] | null
  include_hidden_sheets?: boolean | null
  target_environments?: string[] | null
  ignore_environments?: string[] | null
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
  actual_executed_remaining: number | null
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
  bug_count_source: 'azure_devops' | 'test_result'
  range: { from: string; to: string } | null
  actuals_updated_at: string | null
  available_cases: number
  actual_total_cases: number
  actual_na_cases: number
  undated_result_cases: number
  actual_plan_comparable_cases: number
  planned_total_cases: number | null
  plan_case_mismatch: boolean
  actual_executed_to_latest: number
  planned_completed_to_latest_actual: number
  bug_axis_max: number
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
  is_suspended: boolean
}

// === 識別子の情報更新（SharePoint URL から再集計） ===

export interface CollectFailure {
  testing_id: number
  reason: string
  message: string
}

export interface CollectResult {
  targets: number
  succeeded: number[]
  failed: CollectFailure[]
  auth_error: boolean
  started_at: string
  finished_at: string | null
}
