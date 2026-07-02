export type ApiStatus = 'checking' | 'ok' | 'error'

export type ViewMode = 'dashboard' | 'overview' | 'new' | 'edit' | 'plans' | 'settings'

export interface ChartLayers {
  plannedLine: boolean
  actualCompletedLine: boolean
  actualExecutedLine: boolean
  dailyBars: boolean
  pastPlans: boolean
  bugs: boolean
  openBugLine: boolean
  todayLine: boolean
}
