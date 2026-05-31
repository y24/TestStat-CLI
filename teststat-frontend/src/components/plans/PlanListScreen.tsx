import type { PlanItem } from '../../api/types'
import { formatDate } from '../../utils/date'
import { PlanVersionModal } from './PlanVersionModal'
import type { PlanVersionModalChanges } from './PlanVersionModal'
import { PlanVersionTable } from './PlanVersionTable'
import { ArrowLeft } from 'lucide-react'

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
        <div className="header-title-row">
          <button
            className="icon-button header-back-button"
            type="button"
            onClick={onBack}
            aria-label="PB図に戻る"
            title="PB図に戻る"
          >
            <ArrowLeft aria-hidden="true" />
          </button>
          <div>
            <div className="eyebrow">{projectName}</div>
            <h1>テスト計画入力</h1>
          </div>
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
