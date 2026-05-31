import type { PlanItem } from '../../api/types'
import { formatDate } from '../../utils/date'
import { PlanVersionModal } from './PlanVersionModal'
import type { PlanVersionModalChanges } from './PlanVersionModal'
import { PlanVersionTable } from './PlanVersionTable'

export function PlanListScreen({
  projectName,
  loading,
  error,
  labels,
  actualLabels,
  plans,
  useOverallPlan,
  submitting,
  modalLabel,
  selectedModalPlans,
  onBack,
  onToggleOverall,
  onCreate,
  onManage,
  onSaveModal,
  onCloseModal,
}: {
  projectName: string
  loading: boolean
  error: string | null | undefined
  labels: string[]
  actualLabels: string[]
  plans: PlanItem[]
  useOverallPlan: boolean
  submitting: boolean
  modalLabel: string | null | undefined
  selectedModalPlans: PlanItem[]
  onBack: () => void
  onToggleOverall: (checked: boolean) => void
  onCreate: (label: string | null) => void
  onManage: (label: string | null) => void
  onSaveModal: (changes: PlanVersionModalChanges) => void
  onCloseModal: () => void
}) {
  return (
    <div className="content-shell">
      <header className="content-header">
        <div>
          <div className="eyebrow">{projectName}</div>
          <h1>テスト計画入力</h1>
        </div>
        <div className="header-actions">
          <button className="secondary-button" type="button" onClick={onBack}>
            PB図
          </button>
        </div>
      </header>

      {loading && <div className="chart-state">計画を読み込み中...</div>}
      {!loading && error && <div className="form-error">計画を取得できませんでした: {error}</div>}
      {!loading && !error && (
        <PlanVersionTable
          labels={labels}
          actualLabels={actualLabels}
          plans={plans}
          useOverallPlan={useOverallPlan}
          submitting={submitting}
          onToggleOverall={onToggleOverall}
          onCreate={onCreate}
          onManage={onManage}
          formatDate={formatDate}
        />
      )}
      {modalLabel !== undefined && (
        <PlanVersionModal
          label={modalLabel}
          plans={selectedModalPlans}
          submitting={submitting}
          onSave={onSaveModal}
          onClose={onCloseModal}
        />
      )}
    </div>
  )
}
