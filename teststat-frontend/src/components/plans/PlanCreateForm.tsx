import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { PlanFormState, PlanInputMode } from '../PlanEditor'

export function PlanCreateForm({
  form,
  formError,
  labels,
  availableCasesByLabel,
  submitting,
  onFormChange,
  onSubmit,
}: {
  form: PlanFormState
  formError: string | null
  labels: string[]
  availableCasesByLabel: Record<string, number>
  submitting: boolean
  onFormChange: (form: PlanFormState) => void
  onSubmit: (event: FormEvent) => void
}) {
  const updateLabel = (label: string, fillActualCases = false) => {
    const availableCases = availableCasesByLabel[label]
    onFormChange({
      ...form,
      label,
      planned_total_cases:
        fillActualCases && availableCases !== undefined
          ? String(availableCases)
          : form.planned_total_cases,
    })
  }

  return (
    <form className="editor-form plan-form" onSubmit={onSubmit}>
      <div className="panel-title">新バージョン作成</div>
      {formError && <div className="form-error">{formError}</div>}
      <label>
        <span>テスト(label)</span>
        <LabelCombobox
          value={form.label}
          labels={labels}
          disabled={submitting}
          onChange={(label) => updateLabel(label)}
          onSelectCandidate={(label) => updateLabel(label, true)}
        />
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

function LabelCombobox({
  value,
  labels,
  disabled,
  onChange,
  onSelectCandidate,
}: {
  value: string
  labels: string[]
  disabled: boolean
  onChange: (value: string) => void
  onSelectCandidate: (value: string) => void
}) {
  const [open, setOpen] = useState(false)
  const normalizedValue = value.trim().toLocaleLowerCase()
  const filteredLabels = useMemo(
    () =>
      normalizedValue
        ? labels.filter((label) => label.toLocaleLowerCase().includes(normalizedValue))
        : labels,
    [labels, normalizedValue],
  )

  const showMenu = open && !disabled && labels.length > 0

  return (
    <div
      className="label-combobox"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setOpen(false)
        }
      }}
    >
      <input
        type="text"
        value={value}
        disabled={disabled}
        onFocus={() => setOpen(true)}
        onChange={(event) => {
          onChange(event.target.value)
          setOpen(true)
        }}
        placeholder="全体計画の場合は空欄"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={showMenu}
      />
      <button
        className="label-combobox-button"
        type="button"
        disabled={disabled || labels.length === 0}
        onClick={() => setOpen((current) => !current)}
        aria-label="label候補を開く"
      >
        <span aria-hidden="true" />
      </button>
      {showMenu && (
        <div className="label-combobox-menu" role="listbox">
          {filteredLabels.length > 0 ? (
            filteredLabels.map((label) => (
              <button
                className={label === value ? 'label-combobox-option selected' : 'label-combobox-option'}
                type="button"
                key={label}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  onSelectCandidate(label)
                  setOpen(false)
                }}
                role="option"
                aria-selected={label === value}
              >
                {label}
              </button>
            ))
          ) : (
            <div className="label-combobox-empty">一致する候補はありません</div>
          )}
        </div>
      )}
    </div>
  )
}
