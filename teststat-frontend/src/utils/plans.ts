import { enumerateDates } from './date'

export function displayLabel(label: string | null) {
  return label || '全体'
}

export function buildEvenDaily(start: string, end: string, total: number) {
  const dates = enumerateDates(start, end)
  if (dates.length === 0) {
    return []
  }
  const base = Math.floor(total / dates.length)
  let rest = total % dates.length
  return dates.map((date) => {
    const planned_count = base + (rest > 0 ? 1 : 0)
    rest -= rest > 0 ? 1 : 0
    return { date, planned_count }
  })
}

export function parseDailyCsv(text: string) {
  const rows = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
  const daily: Array<{ date: string; planned_count: number }> = []
  for (const row of rows) {
    if (/^date\s*,\s*planned_count$/i.test(row)) {
      continue
    }
    const [date, countText] = row.split(',').map((item) => item.trim())
    const planned_count = Number(countText)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isInteger(planned_count) || planned_count < 0) {
      throw new Error(`日別計画の形式が不正です: ${row}`)
    }
    daily.push({ date, planned_count })
  }
  return daily
}
