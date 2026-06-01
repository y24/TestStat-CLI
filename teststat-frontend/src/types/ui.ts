export type ApiStatus = 'checking' | 'ok' | 'error'

export type ViewMode = 'overview' | 'new' | 'edit' | 'plans' | 'settings'

export interface ChartLayers {
  plannedLine: boolean
  actualLine: boolean
  dailyBars: boolean
  pastPlans: boolean
  bugs: boolean
}
