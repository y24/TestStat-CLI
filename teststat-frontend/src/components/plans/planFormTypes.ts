export type PlanInputMode = 'even' | 'csv'

export interface PlanFormState {
  label: string
  reason: string
  planned_total_cases: string
  start_date: string
  end_date: string
  activate: boolean
  inputMode: PlanInputMode
  dailyText: string
}
