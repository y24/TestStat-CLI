import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { activatePlan, createPlan, deletePlan, fetchHolidays, fetchPlans, fetchProgressDaily, fetchProgressFiles } from '../api/client'
import type { DailyProgressItem, FileProgressItem, PlanItem, ProjectItem } from '../api/types'
import { formatDate, getTodayString } from '../utils/date'
import { getErrorMessage } from '../utils/errors'
import { buildEvenDaily, displayLabel, parseDailyCsv } from '../utils/plans'
import { PlanCreateForm } from './plans/PlanCreateForm'
import { PlanVersionTable } from './plans/PlanVersionTable'

export type PlanInputMode = 'even' | 'csv'

export interface PlanFormState {
  label: string
  reason: string
  planned_total_cases: string
  start_date: string
  end_date: string
  activate: boolean
  inputMode: PlanInputMode
  dailyText: string
}

interface PlanResult {
  testingId: number
  plans: PlanItem[]
  files: FileProgressItem[]
  daily: DailyProgressItem[]
  error: string | null
}

type PlanEditorMode = 'list' | 'create'

export function PlanEditor({
  project,
  onBack,
  onChanged,
}: {
  project: ProjectItem
  onBack: () => void
  onChanged: () => void
}) {
  const [result, setResult] = useState<PlanResult | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [mode, setMode] = useState<PlanEditorMode>('list')
  const [useOverallPlan, setUseOverallPlan] = useState(false)
  const [modalLabel, setModalLabel] = useState<string | null | undefined>(undefined)
  const [form, setForm] = useState<PlanFormState>(() => createInitialPlanForm())
  const [holidayDates, setHolidayDates] = useState<Set<string>>(() => new Set())

  const loadPlans = () => {
    Promise.all([
      fetchPlans(project.testing_id),
      fetchProgressFiles(project.testing_id).catch(() => [] as FileProgressItem[]),
      fetchProgressDaily(project.testing_id).catch(() => [] as DailyProgressItem[]),
    ])
      .then(([plans, files, daily]) =>
        setResult({ testingId: project.testing_id, plans, files, daily, error: null }),
      )
      .catch((err) =>
        setResult({
          testingId: project.testing_id,
          plans: [],
          files: [],
          daily: [],
          error: getErrorMessage(err),
        }),
      )
  }

  useEffect(() => {
    let ignore = false
    Promise.all([
      fetchPlans(project.testing_id),
      fetchProgressFiles(project.testing_id).catch(() => [] as FileProgressItem[]),
      fetchProgressDaily(project.testing_id).catch(() => [] as DailyProgressItem[]),
    ])
      .then(([plans, files, daily]) => {
        if (!ignore) {
          setResult({ testingId: project.testing_id, plans, files, daily, error: null })
          const hasOverall = plans.some((plan) => plan.label === null)
          const hasIndividual = plans.some((plan) => plan.label !== null)
          setUseOverallPlan(hasOverall && !hasIndividual)
        }
      })
      .catch((err) => {
        if (!ignore) {
          setResult({
            testingId: project.testing_id,
            plans: [],
            files: [],
            daily: [],
            error: getErrorMessage(err),
          })
        }
      })
    return () => {
      ignore = true
    }
  }, [project.testing_id])

  useEffect(() => {
    let ignore = false
    fetchHolidays()
      .then((holidays) => {
        if (!ignore) {
          setHolidayDates(new Set(holidays.map((holiday) => holiday.date)))
        }
      })
      .catch(() => {
        if (!ignore) {
          setHolidayDates(new Set())
        }
      })
    return () => {
      ignore = true
    }
  }, [])

  const loading = result?.testingId !== project.testing_id
  const plans = result?.testingId === project.testing_id ? result.plans : []
  const files = result?.testingId === project.testing_id ? result.files : []
  const daily = result?.testingId === project.testing_id ? result.daily : []
  const actualLabels = Array.from(
    new Set(files.map((file) => file.label).filter((label): label is string => Boolean(label))),
  ).sort((a, b) => a.localeCompare(b))
  const labels = Array.from(
    new Set([
      ...actualLabels,
      ...plans.map((plan) => plan.label).filter((label): label is string => Boolean(label)),
    ]),
  ).sort((a, b) => a.localeCompare(b))
  const availableCasesByLabel = files.reduce<Record<string, number>>((casesByLabel, file) => {
    if (file.label) {
      casesByLabel[file.label] = (casesByLabel[file.label] ?? 0) + file.available_cases
    }
    return casesByLabel
  }, {})
  const overallAvailableCases = Object.values(availableCasesByLabel).reduce(
    (total, count) => total + count,
    0,
  )
  const selectedModalPlans =
    modalLabel === undefined
      ? []
      : plans.filter((plan) => (modalLabel === null ? plan.label === null : plan.label === modalLabel))

  const deletePlans = (targetPlans: PlanItem[]) => {
    const replacementPlans = findReplacementPlansAfterDelete(plans, targetPlans)
    setSubmitting(true)
    Promise.all(targetPlans.map((plan) => deletePlan(plan.id)))
      .then(() => Promise.all(replacementPlans.map((plan) => activatePlan(plan.id))))
      .then(() => {
        loadPlans()
        onChanged()
      })
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  const handleToggleOverall = (checked: boolean) => {
    if (checked === useOverallPlan || submitting) {
      return
    }
    const conflictingPlans = plans.filter((plan) => (checked ? plan.label !== null : plan.label === null))
    if (conflictingPlans.length === 0) {
      setUseOverallPlan(checked)
      return
    }

    const confirmed = window.confirm(
      checked
        ? '全体計画に切り替えるため、入力済みの個別計画をすべて削除します。続行しますか。'
        : '個別計画に切り替えるため、入力済みの全体計画を削除します。続行しますか。',
    )
    if (!confirmed) {
      return
    }
    setUseOverallPlan(checked)
    deletePlans(conflictingPlans)
  }

  const openCreateScreen = (label: string | null) => {
    const actualDateRange = getActualDateRange(label, daily, files)
    const initialForm = createInitialPlanForm()
    setFormError(null)
    setForm({
      ...initialForm,
      label: label ?? '',
      planned_total_cases:
        label === null
          ? overallAvailableCases > 0
            ? String(overallAvailableCases)
            : ''
          : availableCasesByLabel[label] !== undefined
            ? String(availableCasesByLabel[label])
            : '',
      start_date: actualDateRange?.start_date ?? initialForm.start_date,
      end_date: actualDateRange?.end_date ?? initialForm.end_date,
    })
    setMode('create')
  }

  const submitPlan = (event: FormEvent) => {
    event.preventDefault()
    setFormError(null)

    const plannedTotal = Number(form.planned_total_cases)
    if (!Number.isInteger(plannedTotal) || plannedTotal <= 0) {
      setFormError('項目数は正の整数で入力してください')
      return
    }
    if (!form.start_date || !form.end_date || form.start_date > form.end_date) {
      setFormError('開始日と終了日を正しい順序で入力してください')
      return
    }

    let daily: Array<{ date: string; planned_count: number }>
    try {
      daily =
        form.inputMode === 'even'
          ? buildEvenDaily(form.start_date, form.end_date, plannedTotal, holidayDates)
          : parseDailyCsv(form.dailyText)
    } catch (err) {
      setFormError(getErrorMessage(err))
      return
    }

    if (daily.length === 0) {
      setFormError('日別計画を1件以上入力してください')
      return
    }
    const invalidDaily = daily.find((item) => item.date < form.start_date || item.date > form.end_date)
    if (invalidDaily) {
      setFormError(`日別計画 ${invalidDaily.date} が期間外です`)
      return
    }

    const targetLabel = form.label.trim() || null
    const conflictingPlans = plans.filter((plan) =>
      targetLabel === null ? plan.label !== null : plan.label === null,
    )
    if (conflictingPlans.length > 0) {
      const confirmed = window.confirm(
        targetLabel === null
          ? '全体計画を作成するため、入力済みの個別計画をすべて削除します。続行しますか。'
          : '個別計画を作成するため、入力済みの全体計画を削除します。続行しますか。',
      )
      if (!confirmed) {
        return
      }
    }

    setSubmitting(true)
    const cleanup = conflictingPlans.length > 0
      ? Promise.all(conflictingPlans.map((plan) => deletePlan(plan.id)))
      : Promise.resolve()
    cleanup
      .then(() =>
        createPlan(project.testing_id, {
          label: targetLabel,
          reason: form.reason.trim() || null,
          planned_total_cases: plannedTotal,
          start_date: form.start_date,
          end_date: form.end_date,
          activate: form.activate,
          daily,
        }),
      )
      .then(() => {
        loadPlans()
        onChanged()
        setMode('list')
      })
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  const handleActivate = (plan: PlanItem) => {
    setSubmitting(true)
    activatePlan(plan.id)
      .then(() => {
        loadPlans()
        onChanged()
      })
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  const handleDeletePlan = (plan: PlanItem) => {
    const confirmed = window.confirm(`計画 ${displayLabel(plan.label)} v${plan.version} を削除します。`)
    if (!confirmed) {
      return
    }
    deletePlans([plan])
  }

  return (
    <div className="content-shell">
      <header className="content-header">
        <div>
          <div className="eyebrow">{project.name}</div>
          <h1>{mode === 'create' ? '新バージョン作成' : 'テスト計画'}</h1>
          <div className="header-meta">testing_id: {project.testing_id}</div>
        </div>
        <div className="header-actions">
          {mode === 'create' && (
            <button
              className="secondary-button"
              type="button"
              disabled={submitting}
              onClick={() => setMode('list')}
            >
              計画編集へ戻る
            </button>
          )}
          <button className="secondary-button" type="button" onClick={onBack}>
            ダッシュボード
          </button>
        </div>
      </header>

      {loading && <div className="chart-state">計画を読み込み中...</div>}
      {!loading && result?.error && (
        <div className="form-error">計画を取得できませんでした: {result.error}</div>
      )}
      {!loading && !result?.error && mode === 'list' && (
        <PlanVersionTable
          labels={labels}
          actualLabels={actualLabels}
          plans={plans}
          useOverallPlan={useOverallPlan}
          submitting={submitting}
          onToggleOverall={handleToggleOverall}
          onCreate={openCreateScreen}
          onManage={(label) => setModalLabel(label)}
          formatDate={formatDate}
        />
      )}
      {!loading && !result?.error && mode === 'create' && (
        <PlanCreateForm
          form={form}
          formError={formError}
          targetLabel={form.label.trim() || null}
          availableCases={form.label.trim() ? availableCasesByLabel[form.label.trim()] : overallAvailableCases}
          holidays={holidayDates}
          submitting={submitting}
          onFormChange={setForm}
          onSubmit={submitPlan}
        />
      )}
      {modalLabel !== undefined && (
        <PlanVersionModal
          label={modalLabel}
          plans={selectedModalPlans}
          submitting={submitting}
          onActivate={handleActivate}
          onDelete={handleDeletePlan}
          onClose={() => setModalLabel(undefined)}
        />
      )}
    </div>
  )
}

function PlanVersionModal({
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

function findReplacementPlansAfterDelete(plans: PlanItem[], targetPlans: PlanItem[]): PlanItem[] {
  const deletingIds = new Set(targetPlans.map((plan) => plan.id))
  const deletedActivePlans = targetPlans.filter((plan) => plan.is_active)
  const replacementPlans: PlanItem[] = []

  deletedActivePlans.forEach((deletedPlan) => {
    const alreadyQueued = replacementPlans.some((plan) => plan.label === deletedPlan.label)
    if (alreadyQueued) {
      return
    }

    const remainingVersions = plans.filter(
      (plan) => plan.label === deletedPlan.label && !deletingIds.has(plan.id),
    )
    const alreadyActive = remainingVersions.some((plan) => plan.is_active)
    if (alreadyActive) {
      return
    }

    const latestVersion = remainingVersions.reduce<PlanItem | null>(
      (latest, plan) => (latest === null || plan.version > latest.version ? plan : latest),
      null,
    )
    if (latestVersion) {
      replacementPlans.push(latestVersion)
    }
  })

  return replacementPlans
}

function createInitialPlanForm(): PlanFormState {
  const today = getTodayString()
  return {
    label: '',
    reason: '',
    planned_total_cases: '',
    start_date: today,
    end_date: today,
    activate: true,
    inputMode: 'even',
    dailyText: '',
  }
}

function getActualDateRange(
  label: string | null,
  daily: DailyProgressItem[],
  files: FileProgressItem[],
): { start_date: string; end_date: string } | null {
  const matchesLabel = (actualLabel: string | null) => label === null || actualLabel === label
  const dailyDates = daily
    .filter((item) => matchesLabel(item.label))
    .map((item) => item.date)
    .filter(Boolean)

  if (dailyDates.length > 0) {
    return {
      start_date: minString(dailyDates),
      end_date: maxString(dailyDates),
    }
  }

  const fileDates = files
    .filter((file) => matchesLabel(file.label))
    .flatMap((file) => [file.start_date, file.latest_update])
    .filter((date): date is string => Boolean(date))

  if (fileDates.length === 0) {
    return null
  }

  return {
    start_date: minString(fileDates),
    end_date: maxString(fileDates),
  }
}

function minString(values: string[]): string {
  return values.reduce((min, value) => (value < min ? value : min))
}

function maxString(values: string[]): string {
  return values.reduce((max, value) => (value > max ? value : max))
}
