import type { FormEvent } from 'react'
import { ArrowLeft, Tag } from 'lucide-react'

export function PlanLabelCreateScreen({
  loading,
  error,
  label,
  sourceUrl,
  formError,
  submitting,
  onLabelChange,
  onSourceUrlChange,
  onCancel,
  onSubmit,
}: {
  loading: boolean
  error: string | null | undefined
  label: string
  sourceUrl: string
  formError: string | null
  submitting: boolean
  onLabelChange: (label: string) => void
  onSourceUrlChange: (sourceUrl: string) => void
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
            aria-label="テスト計画入力に戻る"
            title="テスト計画入力に戻る"
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
