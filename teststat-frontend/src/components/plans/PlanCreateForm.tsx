import { useMemo } from 'react'
import type { FormEvent } from 'react'
import { enumerateDates } from '../../utils/date'
import {
  buildEvenDaily,
  calculateEndDateByBusinessDays,
  calculateEndDateByDailyCount,
  countBusinessDays,
  displayLabel,
  parseDailyCsv,
} from '../../utils/plans'
import type { PlanFormState, PlanInputMode } from './planFormTypes'

export function PlanCreateForm({
  form,
  formError,
  targetLabel,
  holidays,
  showReason,
  submitting,
  projectStartDate,
  projectEndDate,
  onFormChange,
  onCancel,
  onSubmit,
}: {
  form: PlanFormState
  formError: string | null
  targetLabel: string | null
  holidays: Set<string>
  showReason: boolean
  submitting: boolean
  projectStartDate: string | null
  projectEndDate: string | null
  onFormChange: (form: PlanFormState) => void
  onCancel: () => void
  onSubmit: (event: FormEvent) => void
}) {
  const preview = useMemo(() => buildPreview(form, holidays), [form, holidays])
  const handlePlannedTotalChange = (value: string) => {
    onFormChange(syncDerivedFromDates({ ...form, planned_total_cases: value }, holidays))
  }
  const handleDailyCountChange = (value: string) => {
    const nextForm = { ...form, daily_count_per_day: value }
    const plannedTotal = Number(nextForm.planned_total_cases)
    const dailyCount = Number(value)
    if (
      !Number.isFinite(plannedTotal) ||
      plannedTotal <= 0 ||
      !Number.isFinite(dailyCount) ||
      dailyCount <= 0 ||
      !nextForm.start_date
    ) {
      onFormChange(nextForm)
      return
    }
    const businessDays = Math.ceil(plannedTotal / dailyCount)
    const endDate = calculateEndDateByBusinessDays(nextForm.start_date, businessDays, holidays)
    onFormChange(
      endDate
        ? { ...nextForm, end_date: endDate, business_days: String(businessDays) }
        : nextForm,
    )
  }
  const handleBusinessDaysChange = (value: string) => {
    const nextForm = { ...form, business_days: value }
    const businessDays = Number(value)
    if (!Number.isFinite(businessDays) || businessDays <= 0 || !nextForm.start_date) {
      onFormChange(nextForm)
      return
    }
    const endDate = calculateEndDateByBusinessDays(nextForm.start_date, businessDays, holidays)
    if (!endDate) {
      onFormChange(nextForm)
      return
    }
    const plannedTotal = Number(nextForm.planned_total_cases)
    const dailyCount =
      Number.isFinite(plannedTotal) && plannedTotal > 0
        ? formatDailyCount(plannedTotal / businessDays)
        : nextForm.daily_count_per_day
    onFormChange({ ...nextForm, end_date: endDate, daily_count_per_day: dailyCount })
  }
  const handleStartDateChange = (value: string) => {
    const nextForm = { ...form, start_date: value }
    const syncedForm = syncDerivedFromDates(nextForm, holidays)
    if (syncedForm.daily_count_per_day || !nextForm.daily_count_per_day) {
      onFormChange(syncedForm)
      return
    }

    const plannedTotal = Number(nextForm.planned_total_cases)
    const dailyCount = Number(nextForm.daily_count_per_day)
    const endDate =
      Number.isFinite(plannedTotal) && Number.isFinite(dailyCount) && value
        ? calculateEndDateByDailyCount(value, plannedTotal, dailyCount, holidays)
        : ''
    if (!endDate) {
      onFormChange(nextForm)
      return
    }
    const businessDays = countBusinessDays(value, endDate, holidays)
    onFormChange({
      ...nextForm,
      end_date: endDate,
      business_days: businessDays > 0 ? String(businessDays) : '',
    })
  }
  const handleEndDateChange = (value: string) => {
    onFormChange(syncDerivedFromDates({ ...form, end_date: value }, holidays))
  }

  return (
    <form className="editor-form plan-form wide" onSubmit={onSubmit}>
      <div className="create-target">
        <div>
          <div className="panel-title">対象: {displayLabel(targetLabel)}</div>
        </div>
      </div>
      {formError && <div className="form-error">{formError}</div>}
      <fieldset className="plan-calc-group">
        <legend>計画ボリューム（自動計算）</legend>
        <div className="plan-calc-grid">
          <label>
            <span>項目数</span>
            <input
              type="number"
              min="1"
              value={form.planned_total_cases}
              disabled={submitting}
              onChange={(event) => handlePlannedTotalChange(event.target.value)}
              required
            />
          </label>
          <label>
            <span>営業日数</span>
            <input
              type="number"
              min="1"
              step="1"
              value={form.business_days}
              disabled={submitting}
              onChange={(event) => handleBusinessDaysChange(event.target.value)}
              placeholder="20日"
            />
          </label>
          <label>
            <span>1日あたり項目数</span>
            <input
              type="number"
              min="0.1"
              step="0.1"
              value={form.daily_count_per_day}
              disabled={submitting}
              onChange={(event) => handleDailyCountChange(event.target.value)}
              placeholder="12項目/d"
            />
          </label>
        </div>
      </fieldset>
      <div className="form-grid">
        <label>
          <span>入力方法</span>
          <select
            value={form.inputMode}
            disabled={submitting}
            onChange={(event) =>
              onFormChange({ ...form, inputMode: event.target.value as PlanInputMode })
            }
          >
            <option value="even">均等配分</option>
            <option value="csv">日別/CSV</option>
          </select>
        </label>
      </div>
      <div className="form-grid">
        <label>
          <span>開始日</span>
          <input
            type="date"
            value={form.start_date}
            disabled={submitting}
            onChange={(event) => handleStartDateChange(event.target.value)}
            required
          />
        </label>
        <label>
          <span>終了日</span>
          <input
            type="date"
            value={form.end_date}
            disabled={submitting}
            onChange={(event) => handleEndDateChange(event.target.value)}
            required
          />
        </label>
      </div>
      {projectStartDate && projectEndDate && (
        <div className="project-date-hint">
          予定期間: {formatHintDate(projectStartDate)} ~ {formatHintDate(projectEndDate)}
        </div>
      )}
      {form.inputMode === 'csv' && (
        <label>
          <span>日別計画</span>
          <textarea
            value={form.dailyText}
            disabled={submitting}
            onChange={(event) => onFormChange({ ...form, dailyText: event.target.value })}
            placeholder={'date,planned_count\n2026-06-01,40\n2026-06-02,45'}
            rows={7}
          />
        </label>
      )}
      <PlanPreview preview={preview} />
      {showReason && (
        <label>
          <span>変更理由</span>
          <input
            type="text"
            value={form.reason}
            disabled={submitting}
            onChange={(event) => onFormChange({ ...form, reason: event.target.value })}
            placeholder="仕様追加、期間見直しなど"
          />
        </label>
      )}
      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={form.activate}
          disabled={submitting}
          onChange={(event) => onFormChange({ ...form, activate: event.target.checked })}
        />
        <span>作成後に有効化する</span>
      </label>
      <div className="form-actions">
        <button className="primary-button" type="submit" disabled={submitting}>
          {submitting ? '作成中...' : '計画を作成'}
        </button>
        <button className="secondary-button" type="button" disabled={submitting} onClick={onCancel}>
          キャンセル
        </button>
      </div>
    </form>
  )
}

function PlanPreview({ preview }: { preview: PreviewState }) {
  if (preview.error) {
    return <div className="plan-preview empty">{preview.error}</div>
  }

  const width = 720
  const height = 240
  const padding = { top: 18, right: 20, bottom: 52, left: 46 }
  const plotWidth = width - padding.left - padding.right
  const plotHeight = height - padding.top - padding.bottom
  const maxValue = Math.max(preview.plannedTotal, ...preview.points.map((point) => point.remaining), 1)
  const xStep = preview.points.length > 1 ? plotWidth / (preview.points.length - 1) : 0
  const xTicks = buildDateTicks(preview.points)
  const path = preview.points
    .map((point, index) => {
      const x = padding.left + xStep * index
      const y = padding.top + (1 - point.remaining / maxValue) * plotHeight
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
    })
    .join(' ')
  const areaPath = `${path} L ${padding.left + xStep * (preview.points.length - 1)} ${padding.top + plotHeight} L ${padding.left} ${padding.top + plotHeight} Z`

  return (
    <div className="plan-preview">
      <div className="plan-preview-header">
        <div>
          <div className="panel-title">計画線プレビュー</div>
        </div>
      </div>
      <svg className="preview-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="計画線プレビュー">
        <line x1={padding.left} y1={padding.top} x2={padding.left} y2={padding.top + plotHeight} />
        <line
          x1={padding.left}
          y1={padding.top + plotHeight}
          x2={padding.left + plotWidth}
          y2={padding.top + plotHeight}
        />
        <text x={padding.left - 8} y={padding.top + 4} textAnchor="end">
          {maxValue}
        </text>
        <text x={padding.left - 8} y={padding.top + plotHeight + 4} textAnchor="end">
          0
        </text>
        {xTicks.map((tick) => {
          const x = padding.left + xStep * tick.index
          return (
            <g key={`${tick.date}-${tick.index}`} className="preview-x-tick">
              <line x1={x} y1={padding.top + plotHeight} x2={x} y2={padding.top + plotHeight + 5} />
              <text x={x} y={padding.top + plotHeight + 22} textAnchor="middle">
                {formatTickDate(tick.date)}
              </text>
            </g>
          )
        })}
        <path className="preview-area" d={areaPath} />
        <path className="preview-line" d={path} />
        {preview.points.map((point, index) => {
          const x = padding.left + xStep * index
          const y = padding.top + (1 - point.remaining / maxValue) * plotHeight
          if (preview.points.length > 20 && index !== 0 && index !== preview.points.length - 1) {
            return null
          }
          return <circle key={point.date} cx={x} cy={y} r="3" />
        })}
      </svg>
    </div>
  )
}

interface PreviewPoint {
  date: string
  remaining: number
}

interface PreviewState {
  points: PreviewPoint[]
  plannedTotal: number
  error: string | null
}

function buildPreview(form: PlanFormState, holidays: Set<string>): PreviewState {
  const total = Number(form.planned_total_cases)
  if (!Number.isInteger(total) || total <= 0 || !form.start_date || !form.end_date) {
    return {
      points: [],
      plannedTotal: 0,
      error: '項目数と期間を入力するとプレビューを表示します。',
    }
  }
  if (form.start_date > form.end_date) {
    return {
      points: [],
      plannedTotal: total,
      error: '開始日と終了日を正しい順序で入力してください。',
    }
  }

  try {
    const daily =
      form.inputMode === 'even'
        ? buildEvenDaily(form.start_date, form.end_date, total, holidays)
        : parseDailyCsv(form.dailyText)
    const dates = enumerateDates(form.start_date, form.end_date)
    const dailyMap = new Map(daily.map((item) => [item.date, item.planned_count]))
    let consumed = 0
    const points = dates.map((date) => {
      consumed += dailyMap.get(date) ?? 0
      return { date, remaining: Math.max(total - consumed, 0) }
    })
    return {
      points,
      plannedTotal: total,
      error: points.length === 0 ? '期間内の日付がありません。' : null,
    }
  } catch (err) {
    return {
      points: [],
      plannedTotal: total,
      error: err instanceof Error ? err.message : 'プレビューを作成できません。',
    }
  }
}

function buildDateTicks(points: PreviewPoint[]) {
  if (points.length <= 6) {
    return points.map((point, index) => ({ date: point.date, index }))
  }

  const lastIndex = points.length - 1
  const tickIndexes = new Set<number>()
  for (let i = 0; i < 6; i += 1) {
    tickIndexes.add(Math.round((lastIndex * i) / 5))
  }
  return [...tickIndexes].sort((a, b) => a - b).map((index) => ({ date: points[index].date, index }))
}

function formatTickDate(value: string) {
  const [, month, day] = value.split('-')
  return `${Number(month)}/${Number(day)}`
}

function syncDerivedFromDates(form: PlanFormState, holidays: Set<string>) {
  const businessDays = countBusinessDays(form.start_date, form.end_date, holidays)
  const businessDaysText = businessDays > 0 ? String(businessDays) : ''
  const plannedTotal = Number(form.planned_total_cases)
  if (!Number.isFinite(plannedTotal) || plannedTotal <= 0 || businessDays === 0) {
    return { ...form, business_days: businessDaysText, daily_count_per_day: '' }
  }

  return {
    ...form,
    business_days: businessDaysText,
    daily_count_per_day: formatDailyCount(plannedTotal / businessDays),
  }
}

function formatHintDate(value: string) {
  return value.replaceAll('-', '/')
}

function formatDailyCount(value: number) {
  if (Number.isInteger(value)) {
    return String(value)
  }
  return value.toFixed(1)
}
