export type ProgressStatusLevel = 'normal' | 'caution' | 'warning' | 'unknown'

export type ProgressStatusThresholds = {
  caution: number
  warning: number
}

export const DEFAULT_PROGRESS_STATUS_THRESHOLDS: ProgressStatusThresholds = {
  caution: 90,
  warning: 60,
}

export function normalizeProgressStatusThresholds(value: unknown): ProgressStatusThresholds {
  const candidate = value as Partial<ProgressStatusThresholds>
  return {
    caution: normalizePercent(candidate?.caution, DEFAULT_PROGRESS_STATUS_THRESHOLDS.caution),
    warning: normalizePercent(candidate?.warning, DEFAULT_PROGRESS_STATUS_THRESHOLDS.warning),
  }
}

export function getProgressStatusLevel(
  value: number | null | undefined,
  thresholds: ProgressStatusThresholds,
): ProgressStatusLevel {
  if (value == null || !Number.isFinite(value)) {
    return 'unknown'
  }
  if (value >= thresholds.caution) {
    return 'normal'
  }
  return value <= thresholds.warning ? 'warning' : 'caution'
}

function normalizePercent(value: unknown, fallback: number) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return fallback
  }
  return Math.min(100, Math.max(0, value))
}
