import type { FormEvent } from 'react'
import { ArrowLeft, Tag, Trash2 } from 'lucide-react'
import { PlanLabelCliOptionsFields } from './PlanLabelCliOptionsFields'
import type { LabelCliOptionsInput } from './PlanLabelCliOptionsFields'

export function PlanLabelEditScreen({
  loading,
  error,
  label,
  sourceUrl,
  cliOptions,
  unchanged,
  formError,
  submitting,
  onLabelChange,
  onSourceUrlChange,
  onCliOptionsChange,
  onCancel,
  onSubmit,
  onDelete,
}: {
  loading: boolean
  error: string | null | undefined
  label: string
  sourceUrl: string
  cliOptions: LabelCliOptionsInput
  unchanged: boolean
  formError: string | null
  submitting: boolean
  onLabelChange: (label: string) => void
  onSourceUrlChange: (sourceUrl: string) => void
  onCliOptionsChange: (cliOptions: LabelCliOptionsInput) => void
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
              <span>識別子の編集</span>
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
          <PlanLabelCliOptionsFields value={cliOptions} disabled={submitting} onChange={onCliOptionsChange} />
          <div className="form-actions">
            <button className="primary-button" type="submit" disabled={submitting || unchanged}>
              {submitting ? '保存中...' : '保存'}
            </button>
            <button className="secondary-button" type="button" disabled={submitting} onClick={onCancel}>
              キャンセル
            </button>
            <div className="form-actions-right">
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
