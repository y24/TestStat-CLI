export function formatDateTime(value: string | null) {
  if (!value) {
    return '-'
  }
  const date = parseApiDateTime(value)
  if (!date) {
    return '-'
  }
  return new Intl.DateTimeFormat('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

export function formatDateTimeWithRelative(value: string | null) {
  if (!value) {
    return '-'
  }
  const date = parseApiDateTime(value)
  if (!date) {
    return '-'
  }
  return `${formatMonthDayTime(date)} (${formatRelativePast(date)})`
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(`${value}T00:00:00`))
}

export function getTodayString() {
  const now = new Date()
  return toDateInputValue(now)
}

export function enumerateDates(start: string, end: string) {
  const result: string[] = []
  const current = new Date(`${start}T00:00:00`)
  const last = new Date(`${end}T00:00:00`)
  while (current <= last) {
    result.push(toDateInputValue(current))
    current.setDate(current.getDate() + 1)
  }
  return result
}

export function isWeekend(value: string) {
  const day = new Date(`${value}T00:00:00`).getDay()
  return day === 0 || day === 6
}

function toDateInputValue(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseApiDateTime(value: string) {
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  const date = new Date(hasTimezone ? value : `${value}Z`)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  return date
}

function formatMonthDayTime(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  const hour = String(value.getHours()).padStart(2, '0')
  const minute = String(value.getMinutes()).padStart(2, '0')
  return `${year}/${month}/${day} ${hour}:${minute}`
}

function formatRelativePast(value: Date) {
  const diffMs = Math.max(Date.now() - value.getTime(), 0)
  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  if (diffMinutes < 1) {
    return 'たった今'
  }
  if (diffMinutes < 60) {
    return `${diffMinutes}分前`
  }
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  if (diffHours < 24) {
    return `${diffHours}時間前`
  }
  return `${Math.floor(diffHours / 24)}日前`
}
