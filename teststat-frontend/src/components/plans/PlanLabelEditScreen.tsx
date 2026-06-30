import type { FormEvent } from 'react'
import { ArrowLeft, Eye, EyeOff, Tag, Trash2 } from 'lucide-react'
import { PlanLabelCliOptionsFields } from './PlanLabelCliOptionsFields'
import type { LabelCliOptionsInput } from './PlanLabelCliOptionsFields'

export function PlanLabelEditScreen({
  loading,
  error,
  label,
  sourceUrl,
  subtaskId,
  cliOptions,
  usePlanAsActualOffset,
  usePlanAsActualOffsetDisabled,
  isDisabled,
  unchanged,
  formError,
  submitting,
  onLabelChange,
  onSourceUrlChange,
  onSubtaskIdChange,
  onCliOptionsChange,
  onUsePlanAsActualOffsetChange,
  onToggleDisabled,
  onCancel,
  onSubmit,
  onDelete,
}: {
  loading: boolean
  error: string | null | undefined
  label: string
  sourceUrl: string
  subtaskId: string
  cliOptions: LabelCliOptionsInput
  usePlanAsActualOffset: boolean
  usePlanAsActualOffsetDisabled: boolean
  isDisabled: boolean
  unchanged: boolean
  formError: string | null
  submitting: boolean
  onLabelChange: (label: string) => void
  onSourceUrlChange: (sourceUrl: string) => void
  onSubtaskIdChange: (subtaskId: string) => void
  onCliOptionsChange: (cliOptions: LabelCliOptionsInput) => void
  onUsePlanAsActualOffsetChange: (enabled: boolean) => void
  onToggleDisabled: () => void
  onCancel: () => void
  onSubmit: (event: FormEvent) => void
  onDelete: () => void
}) {
  return (
    <div className="content-shell plan-screen">
      <header className="content-header">
        <div className="header-title-row">
          <button
            className="icon-button header-back-button"
            type="button"
            onClick={onCancel}
            aria-label="テスト計画・管理に戻る"
            title="テスト計画・管理に戻る"
          >
            <ArrowLeft aria-hidden="true" />
          </button>
          <div>
            <h1 className="title-with-icon">
              <Tag className="title-icon" aria-hidden="true" />
              <span>集計設定の編集</span>
            </h1>
          </div>
        </div>
      </header>

      {loading && <div className="chart-state">計画を読み込み中...</div>}
      {!loading && error && <div className="form-error">計画を取得できませんでした: {error}</div>}
      {!loading && !error && (
        <form className="editor-form plan-form label-create-form" onSubmit={onSubmit}>
          {formError && <div className="form-error">{formError}</div>}
          <label>
            <span>識別子(label)</span>
            <input
              type="text"
              value={label}
              disabled={submitting}
              onChange={(event) => onLabelChange(event.target.value)}
              maxLength={255}
              autoFocus
              required
            />
          </label>
          <label>
            <span>SharePoint 共有 URL (path)</span>
            <input
              type="url"
              value={sourceUrl}
              disabled={submitting}
              onChange={(event) => onSourceUrlChange(event.target.value)}
              maxLength={2048}
              placeholder="https://contoso.sharepoint.com/:x:/s/..."
            />
          </label>
          <label>
            <span>サブタスクID (subtask_id)</span>
            <input
              type="number"
              min={0}
              step={1}
              value={subtaskId}
              disabled={submitting}
              onChange={(event) => onSubtaskIdChange(event.target.value)}
              placeholder="WBS連携で更新対象にするサブタスクID"
            />
          </label>
          <PlanLabelCliOptionsFields value={cliOptions} disabled={submitting} onChange={onCliOptionsChange} />
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={usePlanAsActualOffset}
              disabled={submitting || usePlanAsActualOffsetDisabled}
              onChange={(event) => onUsePlanAsActualOffsetChange(event.target.checked)}
            />
            <span>実績データ未送信時、計画項目数を0日目の実績未実施数に加算する</span>
          </label>
          {usePlanAsActualOffsetDisabled && (
            <p className="field-hint">実績データが送信済みのため、この設定は不要です。</p>
          )}


          <div className="form-actions">
            <button className="primary-button" type="submit" disabled={submitting || unchanged}>
              {submitting ? '保存中...' : '保存'}
            </button>
            <button className="secondary-button" type="button" disabled={submitting} onClick={onCancel}>
              キャンセル
            </button>
            <div className="form-actions-right">
              <button
                className="secondary-button icon-text-button"
                type="button"
                disabled={submitting}
                onClick={onToggleDisabled}
              >
                {isDisabled ? (
                  <Eye className="button-icon" aria-hidden="true" />
                ) : (
                  <EyeOff className="button-icon" aria-hidden="true" />
                )}
                <span>{isDisabled ? '有効化' : '無効化'}</span>
              </button>
              <button className="danger-button icon-text-button" type="button" disabled={submitting} onClick={onDelete}>
                <Trash2 className="button-icon" aria-hidden="true" />
                <span>削除</span>
              </button>
            </div>
          </div>
        </form>
      )}
    </div>
  )
}
