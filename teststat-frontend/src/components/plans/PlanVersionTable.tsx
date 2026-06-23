import { ChartLine, FileSpreadsheet, Pencil, RefreshCw, TriangleAlert } from 'lucide-react'
import type { LabelEditTarget, PlanItem, PlanLabelItem } from '../../api/types'
import { countBusinessDays, displayPlanLabel } from '../../utils/plans'

export function PlanVersionTable({
  labels,
  actualLabels,
  availableCasesByLabel,
  unlabeledAvailableCases,
  hasUnlabeledData,
  plans,
  planLabels,
  holidays,
  submitting,
  collectEnabled,
  collectingLabel,
  collectErrors,
  onCreate,
  onEditLabel,
  onRefreshLabel,
  onManage,
  formatDate,
}: {
  labels: string[]
  actualLabels: string[]
  availableCasesByLabel: Record<string, number>
  unlabeledAvailableCases: number
  hasUnlabeledData: boolean
  plans: PlanItem[]
  planLabels: PlanLabelItem[]
  holidays: Set<string>
  submitting: boolean
  collectEnabled: boolean
  collectingLabel: string | null
  collectErrors: Record<string, string>
  onCreate: (label: string | null) => void
  onEditLabel: (planLabel: LabelEditTarget) => void
  onRefreshLabel: (label: string) => void
  onManage: (label: string | null) => void
  formatDate: (value: string) => string
}) {
  // label なし（未設定）のデータ／計画があれば、識別子別の行と並べて最上段に表示する。
  const showUnlabeledRow = hasUnlabeledData || plans.some((plan) => plan.label === null)
  const rows: (string | null)[] = showUnlabeledRow ? [null, ...labels] : labels
  const actualLabelSet = new Set(actualLabels)
  const registeredLabelMap = new Map(planLabels.map((item) => [item.label, item]))

  return (
    <div className="plan-list-panel">
      <div className="plan-panel-header">
        <div>
          <div className="panel-title">テスト一覧</div>
          <div className="panel-subtitle">識別子ごとに計画を管理します。</div>
        </div>
      </div>
      {rows.length === 0 && (
        <div className="muted-block">送信されたデータがまだありません。</div>
      )}
      {rows.length > 0 && (
        <div className="plan-table-wrap">
          <table className="plan-table">
            <thead>
              <tr>
                <th className="plan-table-icon-column" aria-label="編集"></th>
                <th>識別子(label)</th>
                <th className="plan-table-centered-value">版</th>
                <th className="plan-table-centered-value">項目数</th>
                <th className="plan-table-centered-value">営業日数</th>
                <th className="plan-table-centered-value">項目数/1d</th>
                <th>期間</th>
                <th>計画</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((label) => {
                const versions = plans.filter((plan) =>
                  label === null ? plan.label === null : plan.label === label,
                )
                const activePlan = versions.find((plan) => plan.is_active) ?? versions[0] ?? null
                const registeredLabel = label === null ? null : registeredLabelMap.get(label) ?? { label, source_url: null }
                const actualAvailableCases =
                  label === null ? unlabeledAvailableCases : availableCasesByLabel[label]
                const displayedTotalCases =
                  activePlan?.planned_total_cases ?? actualAvailableCases ?? null
                const isPlanOnly = label !== null && !actualLabelSet.has(label)
                const businessDays = activePlan
                  ? countBusinessDays(activePlan.start_date, activePlan.end_date, holidays)
                  : 0
                const dailyCases =
                  activePlan && businessDays > 0
                    ? formatDailyCount(activePlan.planned_total_cases / businessDays)
                    : '-'
                return (
                  <tr key={label ?? '__overall'} className={activePlan ? 'active-plan-row' : ''}>
                    <td className="plan-table-icon-column">
                      {registeredLabel && (
                        <div className="plan-row-actions">
                          <button
                            className="icon-button compact"
                            type="button"
                            disabled={submitting}
                            onClick={() => onEditLabel(registeredLabel)}
                            aria-label={`${registeredLabel.label}を編集`}
                            title="識別子を編集"
                          >
                            <Pencil aria-hidden="true" />
                          </button>
                          {collectEnabled && (
                            <button
                              className={`icon-button compact${
                                collectingLabel === label ? ' is-refreshing' : ''
                              }`}
                              type="button"
                              disabled={
                                submitting ||
                                !registeredLabel.source_url ||
                                collectingLabel !== null
                              }
                              onClick={() => label !== null && onRefreshLabel(label)}
                              aria-label={`${registeredLabel.label}の情報を更新`}
                              title={
                                registeredLabel.source_url
                                  ? '情報を更新（URLのファイルを取得して集計）'
                                  : 'URLが未登録のため更新できません'
                              }
                            >
                              <RefreshCw aria-hidden="true" />
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                    <td>
                      <strong>{displayPlanLabel(label)}</strong>
                      {registeredLabel?.source_url && (
                        <a
                          href={registeredLabel.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="plan-excel-link"
                          title="SharePointのExcelを開く"
                          aria-label={`${registeredLabel.label} のExcelファイルを開く`}
                        >
                          <FileSpreadsheet aria-hidden="true" />
                        </a>
                      )}
                      {isPlanOnly && (
                        <span className="row-note plan-only-note">
                          <TriangleAlert className="plan-only-note-icon" aria-hidden="true" />
                          <span>データがありません</span>
                        </span>
                      )}
                      {label !== null && collectErrors[label] && (
                        <span
                          className="row-note plan-only-note collect-error-note"
                          title={collectErrors[label]}
                        >
                          <TriangleAlert className="plan-only-note-icon" aria-hidden="true" />
                          <span>取得エラー: {collectErrors[label]}</span>
                        </span>
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


