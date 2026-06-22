import type { FormEvent } from 'react'
import { ArrowLeft, Tag, Trash2 } from 'lucide-react'
import type { LabelEditTarget } from '../../api/types'

export function PlanLabelEditScreen({
  loading,
  error,
  planLabel,
  label,
  sourceUrl,
  formError,
  submitting,
  onLabelChange,
  onSourceUrlChange,
  onCancel,
  onSubmit,
  onDelete,
}: {
  loading: boolean
  error: string | null | undefined
  planLabel: LabelEditTarget
  label: string
  sourceUrl: string
  formError: string | null
  submitting: boolean
  onLabelChange: (label: string) => void
  onSourceUrlChange: (sourceUrl: string) => void
  onCancel: () => void
  onSubmit: (event: FormEvent) => void
  onDelete: () => void
}) {
  const unchanged = label.trim() === planLabel.label && sourceUrl.trim() === (planLabel.source_url ?? '')

  return (
    <div className="content-shell plan-screen">
      <header className="content-header">
        <div className="header-title-row">
          <button
            className="icon-button header-back-button"
            type="button"
            onClick={onCancel}
            aria-label="テスト計画入力に戻る"
            title="テスト計画入力に戻る"
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
            <span>SharePoint 共有 URL（任意）</span>
            <input
              type="url"
              value={sourceUrl}
              disabled={submitting}
              onChange={(event) => onSourceUrlChange(event.target.value)}
              maxLength={2048}
              placeholder="https://contoso.sharepoint.com/:x:/s/..."
            />
          </label>
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
