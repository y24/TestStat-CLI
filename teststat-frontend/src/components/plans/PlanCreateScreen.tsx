import type { FormEvent } from 'react'
import type { PlanFormState } from './planFormTypes'
import { PlanCreateForm } from './PlanCreateForm'
import { ArrowLeft, ChartLine } from 'lucide-react'

export function PlanCreateScreen({
  loading,
  error,
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
  loading: boolean
  error: string | null | undefined
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
              <ChartLine className="title-icon" aria-hidden="true" />
              <span>計画線の作成</span>
            </h1>
          </div>
        </div>
      </header>

      {loading && <div className="chart-state">計画を読み込み中...</div>}
      {!loading && error && <div className="form-error">計画を取得できませんでした: {error}</div>}
      {!loading && !error && (
        <PlanCreateForm
          form={form}
          formError={formError}
          targetLabel={targetLabel}
          holidays={holidays}
          showReason={showReason}
          submitting={submitting}
          projectStartDate={projectStartDate}
          projectEndDate={projectEndDate}
          onFormChange={onFormChange}
          onCancel={onCancel}
          onSubmit={onSubmit}
        />
      )}
    </div>
  )
}
