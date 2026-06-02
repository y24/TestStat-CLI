import type { PlanItem } from '../../api/types'
import { formatDate } from '../../utils/date'
import { PlanVersionModal } from './PlanVersionModal'
import type { PlanVersionModalChanges } from './PlanVersionModal'
import { PlanVersionTable } from './PlanVersionTable'
import { ArrowLeft, ClipboardList } from 'lucide-react'

export function PlanListScreen({
  loading,
  error,
  labels,
  actualLabels,
  availableCasesByLabel,
  overallAvailableCases,
  plans,
  holidays,
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
  loading: boolean
  error: string | null | undefined
  labels: string[]
  actualLabels: string[]
  availableCasesByLabel: Record<string, number>
  overallAvailableCases: number
  plans: PlanItem[]
  holidays: Set<string>
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
  const modalResetKey = `${modalLabel ?? 'overall'}:${selectedModalPlans
    .map((plan) => `${plan.id}:${plan.is_active}`)
    .join(',')}`

  return (
    <div className="content-shell plan-screen">
      <header className="content-header">
        <div className="header-title-row">
          <button
            className="icon-button header-back-button"
            type="button"
            onClick={onBack}
            aria-label="戻る"
            title="戻る"
          >
            <ArrowLeft aria-hidden="true" />
          </button>
          <div>
            <h1 className="title-with-icon">
              <ClipboardList className="title-icon" aria-hidden="true" />
              <span>テスト計画入力</span>
            </h1>
          </div>
        </div>
      </header>

      {loading && <div className="chart-state">計画を読み込み中...</div>}
      {!loading && error && <div className="form-error">計画を取得できませんでした: {error}</div>}
      {!loading && !error && (
        <PlanVersionTable
          labels={labels}
          actualLabels={actualLabels}
          availableCasesByLabel={availableCasesByLabel}
          overallAvailableCases={overallAvailableCases}
          plans={plans}
          holidays={holidays}
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
          key={modalResetKey}
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
