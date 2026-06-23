import type { FormEvent } from 'react'
import { ArrowLeft, Tag } from 'lucide-react'
import { PlanLabelCliOptionsFields } from './PlanLabelCliOptionsFields'
import type { LabelCliOptionsInput } from './PlanLabelCliOptionsFields'

export function PlanLabelCreateScreen({
  loading,
  error,
  label,
  sourceUrl,
  subtaskId,
  cliOptions,
  formError,
  submitting,
  onLabelChange,
  onSourceUrlChange,
  onSubtaskIdChange,
  onCliOptionsChange,
  onCancel,
  onSubmit,
}: {
  loading: boolean
  error: string | null | undefined
  label: string
  sourceUrl: string
  subtaskId: string
  cliOptions: LabelCliOptionsInput
  formError: string | null
  submitting: boolean
  onLabelChange: (label: string) => void
  onSourceUrlChange: (sourceUrl: string) => void
  onSubtaskIdChange: (subtaskId: string) => void
  onCliOptionsChange: (cliOptions: LabelCliOptionsInput) => void
  onCancel: () => void
  onSubmit: (event: FormEvent) => void
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
              <span>識別子の追加</span>
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
            <span>SharePoint 共有 URL</span>
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
            <span>サブタスクID subtask_id</span>
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
          <div className="form-actions">
            <button className="primary-button" type="submit" disabled={submitting}>
              {submitting ? '登録中...' : '登録'}
            </button>
            <button className="secondary-button" type="button" disabled={submitting} onClick={onCancel}>
              キャンセル
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
