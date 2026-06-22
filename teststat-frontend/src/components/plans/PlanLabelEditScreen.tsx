import type { FormEvent } from 'react'
import { ArrowLeft, Tag, Trash2 } from 'lucide-react'
import type { PlanLabelItem } from '../../api/types'

export function PlanLabelEditScreen({
  loading,
  error,
  planLabel,
  label,
  formError,
  submitting,
  onLabelChange,
  onCancel,
  onSubmit,
  onDelete,
}: {
  loading: boolean
  error: string | null | undefined
  planLabel: PlanLabelItem
  label: string
  formError: string | null
  submitting: boolean
  onLabelChange: (label: string) => void
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
          <div className="form-actions">
            <button className="primary-button" type="submit" disabled={submitting || label.trim() === planLabel.label}>
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
