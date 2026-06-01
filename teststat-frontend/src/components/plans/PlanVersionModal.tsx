import { useMemo, useState } from 'react'
import type { PlanItem } from '../../api/types'
import { formatDate } from '../../utils/date'
import { displayLabel } from '../../utils/plans'
import { useConfirmDialog } from '../confirmDialogContext'

export interface PlanVersionModalChanges {
  activePlanId: number | null
  deletedPlanIds: number[]
}

export function PlanVersionModal({
  label,
  plans,
  submitting,
  onSave,
  onClose,
}: {
  label: string | null
  plans: PlanItem[]
  submitting: boolean
  onSave: (changes: PlanVersionModalChanges) => void
  onClose: () => void
}) {
  const confirm = useConfirmDialog()
  const initialActivePlanId = useMemo(() => plans.find((plan) => plan.is_active)?.id ?? null, [plans])
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(initialActivePlanId)
  const [deletedPlanIds, setDeletedPlanIds] = useState<number[]>([])

  const deletedPlanIdSet = new Set(deletedPlanIds)
  const visiblePlans = plans.filter((plan) => !deletedPlanIdSet.has(plan.id))
  const hasChanges = selectedPlanId !== initialActivePlanId || deletedPlanIds.length > 0

  const handleDelete = (plan: PlanItem) => {
    const nextDeletedPlanIds = [...deletedPlanIds, plan.id]
    const nextVisiblePlans = plans.filter((item) => !nextDeletedPlanIds.includes(item.id))
    setDeletedPlanIds(nextDeletedPlanIds)
    if (selectedPlanId === plan.id) {
      setSelectedPlanId(nextVisiblePlans[0]?.id ?? null)
    }
  }

  const handleCancel = async () => {
    if (hasChanges) {
      const confirmed = await confirm({
        title: '変更の破棄',
        message: '変更が破棄されますが、よろしいですか？',
        confirmLabel: '破棄',
        danger: true,
      })
      if (!confirmed) {
        return
      }
    }
    onClose()
  }

  const handleSave = () => {
    onSave({ activePlanId: selectedPlanId, deletedPlanIds })
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={handleCancel}>
      <div
        className="modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="plan-version-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <div className="eyebrow">{displayLabel(label)}</div>
            <h2 id="plan-version-modal-title">版の変更/削除</h2>
          </div>
          <button className="icon-button modal-close" type="button" onClick={handleCancel} aria-label="閉じる">
            x
          </button>
        </div>
        <div className="plan-table-wrap">
          <table className="plan-table">
            <thead>
              <tr>
                <th>有効</th>
                <th>版</th>
                <th>項目数</th>
                <th>期間</th>
                <th>理由</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {visiblePlans.map((plan) => (
                <tr key={plan.id} className={selectedPlanId === plan.id ? 'active-plan-row' : ''}>
                  <td>
                    <input
                      className="active-plan-radio"
                      type="radio"
                      name="active-plan-version"
                      checked={selectedPlanId === plan.id}
                      disabled={submitting}
                      aria-label={`v${plan.version}を有効にする`}
                      onChange={() => setSelectedPlanId(plan.id)}
                    />
                  </td>
                  <td>
                    v{plan.version}
                  </td>
                  <td>{plan.planned_total_cases}</td>
                  <td>
                    {formatDate(plan.start_date)} - {formatDate(plan.end_date)}
                  </td>
                  <td>{plan.reason || '-'}</td>
                  <td>
                    <div className="table-actions">
                      <button
                        className="danger-button compact"
                        type="button"
                        disabled={submitting}
                        onClick={() => handleDelete(plan)}
                      >
                        削除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {visiblePlans.length === 0 && (
                <tr>
                  <td colSpan={6}>保存すると、計画がすべて削除されます。</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="modal-actions">
          <button className="primary-button" type="button" disabled={submitting || !hasChanges} onClick={handleSave}>
            {submitting ? '保存中...' : '保存'}
          </button>
          <button className="secondary-button" type="button" disabled={submitting} onClick={handleCancel}>
            キャンセル
          </button>
        </div>
      </div>
    </div>
  )
}
