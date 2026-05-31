import type { FormEvent } from 'react'
import type { PlanFormState, PlanInputMode } from '../PlanEditor'

export function PlanCreateForm({
  form,
  formError,
  labels,
  submitting,
  onFormChange,
  onSubmit,
}: {
  form: PlanFormState
  formError: string | null
  labels: string[]
  submitting: boolean
  onFormChange: (form: PlanFormState) => void
  onSubmit: (event: FormEvent) => void
}) {
  return (
    <form className="editor-form plan-form" onSubmit={onSubmit}>
      <div className="panel-title">新バージョン作成</div>
      {formError && <div className="form-error">{formError}</div>}
      <label>
        <span>テスト(label)</span>
        <input
          list="label-candidates"
          type="text"
          value={form.label}
          disabled={submitting}
          onChange={(event) => onFormChange({ ...form, label: event.target.value })}
          placeholder="全体計画の場合は空欄"
        />
        <datalist id="label-candidates">
          {labels.map((label) => (
            <option key={label} value={label} />
          ))}
        </datalist>
      </label>
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
      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={form.activate}
          disabled={submitting}
          onChange={(event) => onFormChange({ ...form, activate: event.target.checked })}
        />
        <span>作成後に有効な計画にする</span>
      </label>
      <div className="actuals-note">
        {labels.length > 0
          ? `実績label候補: ${labels.join(', ')}`
          : '実績label候補はありません。labelは手入力できます。'}
      </div>
      <div className="form-actions">
        <button className="primary-button" type="submit" disabled={submitting}>
          {submitting ? '作成中...' : '計画を作成'}
        </button>
      </div>
    </form>
  )
}
