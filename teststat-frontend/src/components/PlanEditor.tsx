import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { activatePlan, createPlan, deletePlan, fetchHolidays, fetchPlans, fetchProgressDaily, fetchProgressFiles } from '../api/client'
import type { DailyProgressItem, FileProgressItem, PlanItem, ProjectItem } from '../api/types'
import { getTodayString } from '../utils/date'
import { getErrorMessage } from '../utils/errors'
import { buildEvenDaily, parseDailyCsv } from '../utils/plans'
import { useConfirmDialog } from './confirmDialogContext'
import { PlanCreateScreen } from './plans/PlanCreateScreen'
import { PlanListScreen } from './plans/PlanListScreen'
import type { PlanFormState } from './plans/planFormTypes'
import type { PlanVersionModalChanges } from './plans/PlanVersionModal'

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
  onDirtyChange,
}: {
  project: ProjectItem
  onBack: () => void
  onChanged: () => void
  onDirtyChange: (dirty: boolean) => void
}) {
  const confirm = useConfirmDialog()
  const [result, setResult] = useState<PlanResult | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [mode, setMode] = useState<PlanEditorMode>('list')
  const [useOverallPlan, setUseOverallPlan] = useState(false)
  const [modalLabel, setModalLabel] = useState<string | null | undefined>(undefined)
  const [form, setForm] = useState<PlanFormState>(() => createInitialPlanForm())
  const [initialCreateForm, setInitialCreateForm] = useState<PlanFormState>(() => createInitialPlanForm())
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

  useEffect(() => {
    onDirtyChange(mode === 'create' && !isSamePlanForm(form, initialCreateForm))
  }, [form, initialCreateForm, mode, onDirtyChange])

  useEffect(() => {
    return () => onDirtyChange(false)
  }, [onDirtyChange])

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
  const targetPlanLabel = form.label.trim() || null
  const isCreatingNewVersion = plans.some((plan) =>
    targetPlanLabel === null ? plan.label === null : plan.label === targetPlanLabel,
  )

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

  const handleToggleOverall = async (checked: boolean) => {
    if (checked === useOverallPlan || submitting) {
      return
    }
    const conflictingPlans = plans.filter((plan) => (checked ? plan.label !== null : plan.label === null))
    if (conflictingPlans.length === 0) {
      setUseOverallPlan(checked)
      return
    }

    const confirmed = await confirm({
      title: '計画の切り替え',
      message: checked
        ? '全体計画に切り替えるため、入力済みの個別計画をすべて削除します。続行しますか。'
        : '個別計画に切り替えるため、入力済みの全体計画を削除します。続行しますか。',
      confirmLabel: '削除して切り替え',
      danger: true,
    })
    if (!confirmed) {
      return
    }
    setUseOverallPlan(checked)
    deletePlans(conflictingPlans)
  }

  const openCreateScreen = (label: string | null) => {
    const actualDateRange = getActualDateRange(label, daily, files)
    const projectDateRange =
      project.planned_start_date && project.planned_end_date
        ? {
            start_date: project.planned_start_date,
            end_date: project.planned_end_date,
          }
        : null
    const initialDateRange = projectDateRange ?? actualDateRange
    const initialForm = createInitialPlanForm()
    const nextForm = {
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
      start_date: initialDateRange?.start_date ?? initialForm.start_date,
      end_date: initialDateRange?.end_date ?? initialForm.end_date,
    }
    setFormError(null)
    setForm(nextForm)
    setInitialCreateForm(nextForm)
    setMode('create')
  }

  const cancelCreate = async () => {
    if (!isSamePlanForm(form, initialCreateForm)) {
      const confirmed = await confirm({
        title: '入力内容の破棄',
        message: 'データが破棄されますが、よろしいですか？',
        confirmLabel: '破棄',
        danger: true,
      })
      if (!confirmed) {
        return
      }
    }
    setFormError(null)
    setMode('list')
  }

  const submitPlan = async (event: FormEvent) => {
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
      const confirmed = await confirm({
        title: '既存計画の削除',
        message: targetLabel === null
          ? '全体計画を作成するため、入力済みの個別計画をすべて削除します。続行しますか。'
          : '個別計画を作成するため、入力済みの全体計画を削除します。続行しますか。',
        confirmLabel: '削除して作成',
        danger: true,
      })
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

  const handleSaveModalChanges = (changes: PlanVersionModalChanges) => {
    const targetPlans = plans.filter((plan) => changes.deletedPlanIds.includes(plan.id))
    const activePlanChanged = changes.activePlanId !== selectedModalPlans.find((plan) => plan.is_active)?.id
    const activePlanDeleted = targetPlans.some((plan) => plan.id === changes.activePlanId)
    setSubmitting(true)
    Promise.all(targetPlans.map((plan) => deletePlan(plan.id)))
      .then(() =>
        changes.activePlanId !== null && activePlanChanged && !activePlanDeleted
          ? activatePlan(changes.activePlanId).then(() => undefined)
          : Promise.resolve(),
      )
      .then(() => {
        setModalLabel(undefined)
        loadPlans()
        onChanged()
      })
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  if (mode === 'create') {
    return (
      <PlanCreateScreen
        loading={loading}
        error={result?.error}
        form={form}
        formError={formError}
        targetLabel={targetPlanLabel}
        holidays={holidayDates}
        showReason={isCreatingNewVersion}
        submitting={submitting}
        onFormChange={setForm}
        onCancel={cancelCreate}
        onSubmit={submitPlan}
      />
    )
  }

  return (
    <PlanListScreen
      loading={loading}
      error={result?.error}
      labels={labels}
      actualLabels={actualLabels}
      availableCasesByLabel={availableCasesByLabel}
      overallAvailableCases={overallAvailableCases}
      plans={plans}
      useOverallPlan={useOverallPlan}
      submitting={submitting}
      modalLabel={modalLabel}
      selectedModalPlans={selectedModalPlans}
      onBack={onBack}
      onToggleOverall={handleToggleOverall}
      onCreate={openCreateScreen}
      onManage={(label) => setModalLabel(label)}
      onSaveModal={handleSaveModalChanges}
      onCloseModal={() => setModalLabel(undefined)}
    />
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

function isSamePlanForm(left: PlanFormState, right: PlanFormState): boolean {
  return (
    left.label === right.label &&
    left.reason === right.reason &&
    left.planned_total_cases === right.planned_total_cases &&
    left.start_date === right.start_date &&
    left.end_date === right.end_date &&
    left.activate === right.activate &&
    left.inputMode === right.inputMode &&
    left.dailyText === right.dailyText
  )
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
