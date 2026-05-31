import type { PlanItem } from '../../api/types'
import { displayLabel } from '../../utils/plans'

export function PlanVersionTable({
  labels,
  actualLabels,
  plans,
  useOverallPlan,
  submitting,
  onToggleOverall,
  onCreate,
  onManage,
  formatDate,
}: {
  labels: string[]
  actualLabels: string[]
  plans: PlanItem[]
  useOverallPlan: boolean
  submitting: boolean
  onToggleOverall: (checked: boolean) => void
  onCreate: (label: string | null) => void
  onManage: (label: string | null) => void
  formatDate: (value: string) => string
}) {
  const rows = useOverallPlan ? [null] : labels
  const actualLabelSet = new Set(actualLabels)

  return (
    <div className="plan-list-panel">
      <div className="plan-panel-header">
        <div>
          <div className="panel-title">計画バージョン</div>
          <div className="panel-subtitle">
            {useOverallPlan ? '全体計画を1つだけ管理します。' : '実績データのテスト種別ごとに計画を管理します。'}
          </div>
        </div>
        <label className="switch-row">
          <span>全体計画</span>
          <input
            type="checkbox"
            checked={useOverallPlan}
            disabled={submitting}
            onChange={(event) => onToggleOverall(event.target.checked)}
          />
          <span className="switch-track" aria-hidden="true" />
        </label>
      </div>
      {!useOverallPlan && labels.length === 0 && (
        <div className="muted-block">実績データのテスト種別がまだありません。</div>
      )}
      {(useOverallPlan || labels.length > 0) && (
        <div className="plan-table-wrap">
          <table className="plan-table">
            <thead>
              <tr>
                <th>テスト種別</th>
                <th>有効な版</th>
                <th>項目数</th>
                <th>期間</th>
                <th>日別合計</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((label) => {
                const versions = plans.filter((plan) =>
                  label === null ? plan.label === null : plan.label === label,
                )
                const activePlan = versions.find((plan) => plan.is_active) ?? versions[0] ?? null
                return (
                  <tr key={label ?? '__overall'} className={activePlan ? 'active-plan-row' : ''}>
                    <td>
                      <strong>{displayLabel(label)}</strong>
                      {label !== null && !actualLabelSet.has(label) && (
                        <span className="row-note">実績なし / 計画のみ</span>
                      )}
                      {!activePlan && <span className="row-note">未計画</span>}
                      {activePlan?.reason && <span className="row-note">{activePlan.reason}</span>}
                    </td>
                    <td>
                      {activePlan ? (
                        <>
                          v{activePlan.version}
                          {activePlan.is_active && <span className="active-badge">有効</span>}
                        </>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td>{activePlan?.planned_total_cases ?? '-'}</td>
                    <td>
                      {activePlan
                        ? `${formatDate(activePlan.start_date)} - ${formatDate(activePlan.end_date)}`
                        : '-'}
                    </td>
                    <td>{activePlan?.daily_total ?? '-'}</td>
                    <td>
                      <div className="table-actions">
                        {versions.length > 0 && (
                          <button
                            className="secondary-button compact"
                            type="button"
                            disabled={submitting}
                            onClick={() => onManage(label)}
                          >
                            版の変更/削除
                          </button>
                        )}
                        <button
                          className="primary-button compact"
                          type="button"
                          disabled={submitting}
                          onClick={() => onCreate(label)}
                        >
                          作成
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
