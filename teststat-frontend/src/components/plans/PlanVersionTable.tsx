import type { PlanItem } from '../../api/types'
import { displayLabel } from '../../utils/plans'

export function PlanVersionTable({
  plans,
  submitting,
  onActivate,
  onDelete,
  formatDate,
}: {
  plans: PlanItem[]
  submitting: boolean
  onActivate: (plan: PlanItem) => void
  onDelete: (plan: PlanItem) => void
  formatDate: (value: string) => string
}) {
  return (
    <div className="plan-list-panel">
      <div className="panel-title">計画バージョン</div>
      {plans.length === 0 && (
        <div className="muted-block">まだ計画がありません。右側で新しい計画を作成してください。</div>
      )}
      {plans.length > 0 && (
        <div className="plan-table-wrap">
          <table className="plan-table">
            <thead>
              <tr>
                <th>テスト(label)</th>
                <th>版</th>
                <th>項目数</th>
                <th>期間</th>
                <th>日別合計</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {plans.map((plan) => (
                <tr key={plan.id} className={plan.is_active ? 'active-plan-row' : ''}>
                  <td>
                    <strong>{displayLabel(plan.label)}</strong>
                    {plan.reason && <span className="row-note">{plan.reason}</span>}
                  </td>
                  <td>
                    v{plan.version}
                    {plan.is_active && <span className="active-badge">有効</span>}
                  </td>
                  <td>{plan.planned_total_cases}</td>
                  <td>
                    {formatDate(plan.start_date)} - {formatDate(plan.end_date)}
                  </td>
                  <td>{plan.daily_total}</td>
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
      )}
    </div>
  )
}
