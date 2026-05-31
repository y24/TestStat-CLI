import type { PlanItem } from '../../api/types'
import { formatDate } from '../../utils/date'
import { displayLabel } from '../../utils/plans'

export function PlanVersionModal({
  label,
  plans,
  submitting,
  onActivate,
  onDelete,
  onClose,
}: {
  label: string | null
  plans: PlanItem[]
  submitting: boolean
  onActivate: (plan: PlanItem) => void
  onDelete: (plan: PlanItem) => void
  onClose: () => void
}) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
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
          <button className="icon-button modal-close" type="button" onClick={onClose} aria-label="閉じる">
            x
          </button>
        </div>
        <div className="plan-table-wrap">
          <table className="plan-table">
            <thead>
              <tr>
                <th>版</th>
                <th>項目数</th>
                <th>期間</th>
                <th>理由</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {plans.map((plan) => (
                <tr key={plan.id} className={plan.is_active ? 'active-plan-row' : ''}>
                  <td>
                    v{plan.version}
                    {plan.is_active && <span className="active-badge">有効</span>}
                  </td>
                  <td>{plan.planned_total_cases}</td>
                  <td>
                    {formatDate(plan.start_date)} - {formatDate(plan.end_date)}
                  </td>
                  <td>{plan.reason || '-'}</td>
                  <td>
                    <div className="table-actions">
                      <button
                        className="secondary-button compact"
                        type="button"
                        disabled={plan.is_active || submitting}
                        onClick={() => onActivate(plan)}
                      >
                        有効化
                      </button>
                      <button
                        className="danger-button compact"
                        type="button"
                        disabled={submitting}
                        onClick={() => onDelete(plan)}
                      >
                        削除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
