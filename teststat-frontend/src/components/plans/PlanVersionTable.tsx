import {
  closestCenter,
  DndContext,
  type DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { ChartLine, FileSpreadsheet, GripVertical, Pencil, Plus, RefreshCw, TriangleAlert } from 'lucide-react'
import type { CSSProperties, ReactNode } from 'react'
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
  readOnly,
  collectingLabel,
  collectErrors,
  onCreate,
  onAddLabel,
  onEditLabel,
  onRefreshLabel,
  onReorderLabels,
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
  readOnly: boolean
  collectingLabel: string | null
  collectErrors: Record<string, string>
  onCreate: (label: string | null) => void
  onAddLabel: () => void
  onEditLabel: (planLabel: LabelEditTarget) => void
  onRefreshLabel: (label: string) => void
  onReorderLabels: (labels: string[]) => void
  onManage: (label: string | null) => void
  formatDate: (value: string) => string
}) {
  // label なし（未設定）のデータ／計画があれば、識別子別の行と並べて最上段に表示する。
  const showUnlabeledRow = hasUnlabeledData || plans.some((plan) => plan.label === null)
  const rows: (string | null)[] = showUnlabeledRow ? [null, ...labels] : labels
  const actualLabelSet = new Set(actualLabels)
  const registeredLabelMap = new Map(planLabels.map((item) => [item.label, item]))
  const sortableLabels = labels
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 6,
      },
    }),
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id || submitting || readOnly) {
      return
    }
    const sourceIndex = labels.findIndex((label) => label === active.id)
    const targetIndex = labels.findIndex((label) => label === over.id)
    if (sourceIndex < 0 || targetIndex < 0) {
      return
    }
    const nextLabels = arrayMove(labels, sourceIndex, targetIndex)
    onReorderLabels(nextLabels)
  }

  return (
    <div className="plan-list-panel">
      <div className="plan-panel-header">
        <div>
          <div className="panel-title">集計設定一覧</div>
          <div className="panel-subtitle">集計単位ごとの計画を管理します。</div>
          <button
            className="primary-button icon-text-button"
            type="button"
            disabled={submitting || readOnly}
            onClick={onAddLabel}
            style={{ marginBottom: '12px' }}
          >
            <Plus className="button-icon" aria-hidden="true" />
            <span>集計設定を追加</span>
          </button>
        </div>
      </div>
      {rows.length > 0 && (
        <div className="plan-table-wrap">
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <table className="plan-table">
              <thead>
                <tr>
                  <th className="plan-table-drag-column" aria-label="並び替え"></th>
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
              <SortableContext items={sortableLabels} strategy={verticalListSortingStrategy}>
                <tbody>
                  {rows.map((label) => {
                    const versions = plans.filter((plan) =>
                      label === null ? plan.label === null : plan.label === label,
                    )
                    const activePlan = versions.find((plan) => plan.is_active) ?? versions[0] ?? null
                    const registeredLabel = label === null ? null : registeredLabelMap.get(label) ?? null
                    const labelTarget = label === null ? null : registeredLabel ?? { label, is_disabled: false, source_url: null }
                    const isDisabled = Boolean(labelTarget?.is_disabled)
                    const actualAvailableCases =
                      label === null ? unlabeledAvailableCases : availableCasesByLabel[label]
                    const displayedTotalCases =
                      activePlan?.planned_total_cases ?? actualAvailableCases ?? null
                    const isPlanOnly = label !== null && !actualLabelSet.has(label)
                    // 計画とデータの両方がそろっているのに項目数が食い違うときは警告する。
                    const casesMismatch =
                      activePlan != null &&
                      actualAvailableCases !== undefined &&
                      actualAvailableCases > 0 &&
                      activePlan.planned_total_cases !== actualAvailableCases
                    const businessDays = activePlan
                      ? countBusinessDays(activePlan.start_date, activePlan.end_date, holidays)
                      : 0
                    const dailyCases =
                      activePlan && businessDays > 0
                        ? formatDailyCount(activePlan.planned_total_cases / businessDays)
                        : '-'
                    const row = (
                      <PlanVersionRowContent
                        label={label}
                        activePlan={activePlan}
                        versions={versions}
                        registeredLabel={registeredLabel}
                        labelTarget={labelTarget}
                        isDisabled={isDisabled}
                        displayedTotalCases={displayedTotalCases}
                        actualAvailableCases={actualAvailableCases ?? null}
                        casesMismatch={casesMismatch}
                        businessDays={businessDays}
                        dailyCases={dailyCases}
                        isPlanOnly={isPlanOnly}
                        collectEnabled={collectEnabled}
                        readOnly={readOnly}
                        submitting={submitting}
                        collectingLabel={collectingLabel}
                        collectErrors={collectErrors}
                        onCreate={onCreate}
                        onEditLabel={onEditLabel}
                        onRefreshLabel={onRefreshLabel}
                        onManage={onManage}
                        formatDate={formatDate}
                      />
                    )
                    if (label !== null) {
                      return (
                        <SortablePlanVersionRow key={label} label={label} active={Boolean(activePlan)} isDisabled={isDisabled} readOnly={readOnly}>
                          {row}
                        </SortablePlanVersionRow>
                      )
                    }
                    return (
                      <tr
                        key="__overall"
                        className={`${activePlan ? 'active-plan-row' : ''}${isDisabled ? ' disabled-label-row' : ''}`}
                      >
                        <td className="plan-table-drag-column"></td>
                        {row}
                      </tr>
                    )
                  })}
                </tbody>
              </SortableContext>
            </table>
          </DndContext>
        </div>
      )}
    </div>
  )
}

function SortablePlanVersionRow({
  label,
  active,
  isDisabled,
  children,
  readOnly,
}: {
  label: string
  active: boolean
  isDisabled: boolean
  children: ReactNode
  readOnly: boolean
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: label,
    disabled: readOnly,
  })
  const style: CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <tr
      ref={setNodeRef}
      className={`${active ? 'active-plan-row' : ''}${isDragging ? ' dragging' : ''}${isDisabled ? ' disabled-label-row' : ''}`}
      style={style}
    >
      <td className="plan-table-drag-column">
        <span
          className="plan-label-drag-handle"
          title="ドラッグして並び替え"
          {...(readOnly ? {} : attributes)}
          {...(readOnly ? {} : listeners)}
        >
          <GripVertical aria-hidden="true" />
        </span>
      </td>
      {children}
    </tr>
  )
}

function PlanVersionRowContent({
  label,
  activePlan,
  versions,
  registeredLabel,
  labelTarget,
  isDisabled,
  displayedTotalCases,
  actualAvailableCases,
  casesMismatch,
  businessDays,
  dailyCases,
  isPlanOnly,
  collectEnabled,
  readOnly,
  submitting,
  collectingLabel,
  collectErrors,
  onCreate,
  onEditLabel,
  onRefreshLabel,
  onManage,
  formatDate,
}: {
  label: string | null
  activePlan: PlanItem | null
  versions: PlanItem[]
  registeredLabel: PlanLabelItem | null
  labelTarget: LabelEditTarget | null
  isDisabled: boolean
  displayedTotalCases: number | null
  actualAvailableCases: number | null
  casesMismatch: boolean
  businessDays: number
  dailyCases: string
  isPlanOnly: boolean
  collectEnabled: boolean
  readOnly: boolean
  submitting: boolean
  collectingLabel: string | null
  collectErrors: Record<string, string>
  onCreate: (label: string | null) => void
  onEditLabel: (planLabel: LabelEditTarget) => void
  onRefreshLabel: (label: string) => void
  onManage: (label: string | null) => void
  formatDate: (value: string) => string
}) {
  return (
    <>
      <td className="plan-table-icon-column">
        {labelTarget && (
          <div className="plan-row-actions">
            <button
              className="icon-button compact"
              type="button"
              disabled={submitting || readOnly}
              onClick={() => onEditLabel(labelTarget)}
              aria-label={`${labelTarget.label}を編集`}
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
                  readOnly ||
                  isDisabled ||
                  !registeredLabel?.source_url ||
                  collectingLabel !== null
                }
                onClick={() => label !== null && onRefreshLabel(label)}
                aria-label={`${labelTarget.label}の情報を更新`}
                title={
                  isDisabled
                    ? '無効な集計設定は更新対象外です'
                    : registeredLabel?.source_url
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
        <div className="plan-label-cell-title">
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
          {isDisabled && (
            <span className="disabled-label-note">無効</span>
          )}
        </div>
        {isPlanOnly && (
          <span className="row-note plan-only-note">
            <TriangleAlert className="plan-only-note-icon" aria-hidden="true" />
            <span>データがありません</span>
          </span>
        )}
        {casesMismatch && activePlan && (
          <span
            className="row-note plan-only-note"
            title={`計画とデータが一致していません（計画 ${activePlan.planned_total_cases} / データ ${actualAvailableCases}）`}
          >
            <TriangleAlert className="plan-only-note-icon" aria-hidden="true" />
            <span>項目数が不一致</span>
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
      <td className={`plan-table-centered-value${casesMismatch ? ' plan-cases-mismatch' : ''}`}>
        {casesMismatch && activePlan ? (
          <span
            className="plan-cases-mismatch-value"
            title={`計画とデータが一致していません（計画 ${activePlan.planned_total_cases} / データ ${actualAvailableCases}）`}
          >
            <TriangleAlert className="plan-only-note-icon" aria-hidden="true" />
            {displayedTotalCases}
          </span>
        ) : displayedTotalCases !== null ? (
          `${displayedTotalCases}`
        ) : (
          '-'
        )}
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
            disabled={submitting || readOnly || isDisabled}
            onClick={() => onCreate(label)}
          >
            <ChartLine className="button-icon" aria-hidden="true" strokeWidth={2.2} />
            <span>作成</span>
          </button>
          {versions.length > 0 && (
            <button
              className="secondary-button compact"
              type="button"
              disabled={submitting || readOnly}
              onClick={() => onManage(label)}
            >
              版の変更/削除
            </button>
          )}
        </div>
      </td>
    </>
  )
}

function formatDailyCount(value: number) {
  if (Number.isInteger(value)) {
    return String(value)
  }
  return value.toFixed(1)
}
