import { ChartLine } from 'lucide-react'
import type { PlanItem } from '../../api/types'
import { countBusinessDays, displayLabel } from '../../utils/plans'

export function PlanVersionTable({
  labels,
  actualLabels,
  availableCasesByLabel,
  overallAvailableCases,
  plans,
  holidays,
  useOverallPlan,
  submitting,
  onToggleOverall,
  onCreate,
  onManage,
  formatDate,
}: {
  labels: string[]
  actualLabels: string[]
  availableCasesByLabel: Record<string, number>
  overallAvailableCases: number
  plans: PlanItem[]
  holidays: Set<string>
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
          <div className="panel-title">計画一覧</div>
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
                <th className="plan-table-centered-value">版</th>
                <th className="plan-table-centered-value">項目数</th>
                <th className="plan-table-centered-value">営業日数</th>
                <th className="plan-table-centered-value">1日あたり項目数</th>
                <th>期間</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((label) => {
                const versions = plans.filter((plan) =>
                  label === null ? plan.label === null : plan.label === label,
                )
                const activePlan = versions.find((plan) => plan.is_active) ?? versions[0] ?? null
                const actualAvailableCases =
                  label === null ? overallAvailableCases : availableCasesByLabel[label]
                const displayedTotalCases =
                  activePlan?.planned_total_cases ?? actualAvailableCases ?? null
                const businessDays = activePlan
                  ? countBusinessDays(activePlan.start_date, activePlan.end_date, holidays)
                  : 0
                const dailyCases =
                  activePlan && businessDays > 0
                    ? formatDailyCount(activePlan.planned_total_cases / businessDays)
                    : '-'
                return (
                  <tr key={label ?? '__overall'} className={activePlan ? 'active-plan-row' : ''}>
                    <td>
                      <strong>{displayLabel(label)}</strong>
                      {label !== null && !actualLabelSet.has(label) && (
                        <span className="row-note">実績なし / 計画のみ</span>
                      )}
                      {activePlan?.reason && <span className="row-note">{activePlan.reason}</span>}
                    </td>
                    <td className="plan-table-centered-value">
                      {activePlan ? (
                        `v${activePlan.version}`
                      ) : (
                        <span className="plan-missing-badge" title="計画入力が必要です。">
                          未計画
                        </span>
                      )}
                    </td>
                    <td className="plan-table-centered-value">
                      {displayedTotalCases !== null ? `${displayedTotalCases}` : '-'}
                    </td>
                    <td className="plan-table-centered-value">
                      {activePlan && businessDays > 0 ? `${businessDays}` : '-'}
                    </td>
                    <td className="plan-table-centered-value">
                      {dailyCases !== '-' ? `${dailyCases}` : '-'}
                    </td>
                    <td>
                      {activePlan
                        ? `${formatDate(activePlan.start_date)} - ${formatDate(activePlan.end_date)}`
                        : '-'}
                    </td>
                    <td>
                      <div className="table-actions">
                        <button
                          className="primary-button compact icon-text-button"
                          type="button"
                          disabled={submitting}
                          onClick={() => onCreate(label)}
                        >
                          <ChartLine className="button-icon" aria-hidden="true" strokeWidth={2.2} />
                          <span>作成</span>
                        </button>
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

function formatDailyCount(value: number) {
  if (Number.isInteger(value)) {
    return String(value)
  }
  return value.toFixed(1)
}
