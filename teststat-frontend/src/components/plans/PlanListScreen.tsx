import type { LabelEditTarget, PlanItem, PlanLabelItem } from '../../api/types'
import { formatDate } from '../../utils/date'
import { PlanVersionModal } from './PlanVersionModal'
import type { PlanVersionModalChanges } from './PlanVersionModal'
import { PlanVersionTable } from './PlanVersionTable'
import { ArrowLeft, ClipboardList, Plus, RefreshCw } from 'lucide-react'

export function PlanListScreen({
  loading,
  error,
  labels,
  actualLabels,
  availableCasesByLabel,
  unlabeledAvailableCases,
  hasUnlabeledData,
  plans,
  planLabels,
  holidays,
  submitting,
  collectingLabel,
  collectingAll,
  refreshableCount,
  collectErrors,
  modalLabel,
  selectedModalPlans,
  onBack,
  onAddLabel,
  onEditLabel,
  onRefreshLabel,
  onRefreshAll,
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
  unlabeledAvailableCases: number
  hasUnlabeledData: boolean
  plans: PlanItem[]
  planLabels: PlanLabelItem[]
  holidays: Set<string>
  submitting: boolean
  collectingLabel: string | null
  collectingAll: boolean
  refreshableCount: number
  collectErrors: Record<string, string>
  modalLabel: string | null | undefined
  selectedModalPlans: PlanItem[]
  onBack: () => void
  onAddLabel: () => void
  onEditLabel: (planLabel: LabelEditTarget) => void
  onRefreshLabel: (label: string) => void
  onRefreshAll: () => void
  onCreate: (label: string | null) => void
  onManage: (label: string | null) => void
  onSaveModal: (changes: PlanVersionModalChanges) => void
  onCloseModal: () => void
}) {
  const modalResetKey = `${modalLabel ?? 'unlabeled'}:${selectedModalPlans
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
              <span>テスト計画・管理</span>
            </h1>
          </div>
        </div>
        <div className="header-actions">
          {refreshableCount > 0 && (
            <button
              className={`secondary-button icon-text-button${collectingAll ? ' is-refreshing' : ''}`}
              type="button"
              disabled={submitting || collectingLabel !== null || collectingAll}
              onClick={onRefreshAll}
              title="URLが登録されている識別子をすべて取得して集計します"
            >
              <RefreshCw className="button-icon" aria-hidden="true" />
              <span>{collectingAll ? '一括更新中...' : 'すべて更新'}</span>
            </button>
          )}
          <button
            className="primary-button icon-text-button"
            type="button"
            disabled={submitting || collectingAll}
            onClick={onAddLabel}
          >
            <Plus className="button-icon" aria-hidden="true" />
            <span>識別子を追加</span>
          </button>
        </div>
      </header>

      {loading && <div className="chart-state">計画を読み込み中...</div>}
      {!loading && error && <div className="form-error">計画を取得できませんでした: {error}</div>}
      {!loading && !error && (
        <PlanVersionTable
          labels={labels}
          actualLabels={actualLabels}
          availableCasesByLabel={availableCasesByLabel}
          unlabeledAvailableCases={unlabeledAvailableCases}
          hasUnlabeledData={hasUnlabeledData}
          plans={plans}
          planLabels={planLabels}
          holidays={holidays}
          submitting={submitting}
          collectingLabel={collectingLabel}
          collectErrors={collectErrors}
          onCreate={onCreate}
          onEditLabel={onEditLabel}
          onRefreshLabel={onRefreshLabel}
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
