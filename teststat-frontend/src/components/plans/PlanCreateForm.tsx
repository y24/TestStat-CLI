import { useMemo } from 'react'
import type { FormEvent } from 'react'
import { enumerateDates, formatDate } from '../../utils/date'
import { buildEvenDaily, displayLabel, parseDailyCsv } from '../../utils/plans'
import type { PlanFormState, PlanInputMode } from './planFormTypes'

export function PlanCreateForm({
  form,
  formError,
  targetLabel,
  holidays,
  showReason,
  submitting,
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
  onFormChange: (form: PlanFormState) => void
  onCancel: () => void
  onSubmit: (event: FormEvent) => void
}) {
  const preview = useMemo(() => buildPreview(form, holidays), [form, holidays])

  return (
    <form className="editor-form plan-form wide" onSubmit={onSubmit}>
      <div className="create-target">
        <div>
          <div className="panel-title">対象: {displayLabel(targetLabel)}</div>
        </div>
      </div>
      {formError && <div className="form-error">{formError}</div>}
      <div className="form-grid">
        <label>
          <span>項目数</span>
          <input
            type="number"
            min="1"
            value={form.planned_total_cases}
            disabled={submitting}
            onChange={(event) => onFormChange({ ...form, planned_total_cases: event.target.value })}
            required
          />
        </label>
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
            onChange={(event) => onFormChange({ ...form, start_date: event.target.value })}
            required
          />
        </label>
        <label>
          <span>終了日</span>
          <input
            type="date"
            value={form.end_date}
            disabled={submitting}
            onChange={(event) => onFormChange({ ...form, end_date: event.target.value })}
            required
          />
        </label>
      </div>
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
  const height = 220
  const padding = { top: 18, right: 20, bottom: 34, left: 46 }
  const plotWidth = width - padding.left - padding.right
  const plotHeight = height - padding.top - padding.bottom
  const maxValue = Math.max(preview.plannedTotal, ...preview.points.map((point) => point.remaining), 1)
  const xStep = preview.points.length > 1 ? plotWidth / (preview.points.length - 1) : 0
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
          <div className="panel-subtitle">
            {formatDate(preview.points[0].date)} - {formatDate(preview.points.at(-1)?.date ?? preview.points[0].date)}
          </div>
        </div>
        <div className="preview-stats">
          <span>合計 {preview.dailyTotal}</span>
          <span>日数 {preview.points.length}</span>
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
  dailyTotal: number
  error: string | null
}

function buildPreview(form: PlanFormState, holidays: Set<string>): PreviewState {
  const total = Number(form.planned_total_cases)
  if (!Number.isInteger(total) || total <= 0 || !form.start_date || !form.end_date) {
    return { points: [], plannedTotal: 0, dailyTotal: 0, error: '項目数と期間を入力するとプレビューを表示します。' }
  }
  if (form.start_date > form.end_date) {
    return { points: [], plannedTotal: total, dailyTotal: 0, error: '開始日と終了日を正しい順序で入力してください。' }
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
      dailyTotal: daily.reduce((sum, item) => sum + item.planned_count, 0),
      error: points.length === 0 ? '期間内の日付がありません。' : null,
    }
  } catch (err) {
    return {
      points: [],
      plannedTotal: total,
      dailyTotal: 0,
      error: err instanceof Error ? err.message : 'プレビューを作成できません。',
    }
  }
}
