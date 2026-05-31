import type { FormEvent } from 'react'
import type { PlanFormState } from './planFormTypes'
import { PlanCreateForm } from './PlanCreateForm'

export function PlanCreateScreen({
  projectName,
  loading,
  error,
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
  projectName: string
  loading: boolean
  error: string | null | undefined
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
  return (
    <div className="content-shell">
      <header className="content-header">
        <div>
          <div className="eyebrow">{projectName}</div>
          <h1>新バージョン作成</h1>
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
          onFormChange={onFormChange}
          onCancel={onCancel}
          onSubmit={onSubmit}
        />
      )}
    </div>
  )
}
