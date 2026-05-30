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

// === 計画系（フロント新設バックエンド。Phase B1〜B3 で実装後に使う） ===

export interface ProjectItem {
  testing_id: number
  name: string
  ticket_ref: string | null
  archived: boolean
  has_actuals: boolean
  actuals_updated_at: string | null
  active_plan_count: number
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
}

export interface PlanDailyItem {
  date: string
  planned_count: number
}

export interface PlanDetail extends PlanItem {
  daily: PlanDailyItem[]
}

export interface PbChartSeries {
  date: string
  planned_remaining: number | null
  actual_remaining: number | null
  planned_completed_daily: number | null
  actual_completed_daily: number | null
}

export interface PbChartPastPlan {
  version: number
  series: Array<{ date: string; planned_remaining: number }>
}

export interface PbChartResponse {
  testing_id: number
  label: string | null
  range: { from: string; to: string }
  actuals_updated_at: string | null
  available_cases: number | null
  planned_total_cases: number | null
  series: PbChartSeries[]
  past_plans: PbChartPastPlan[]
}
