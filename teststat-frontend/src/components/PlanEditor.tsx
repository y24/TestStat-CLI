import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  activatePlan,
  collectLabel,
  createPlan,
  createPlanLabel,
  deletePlan,
  deleteProjectLabel,
  fetchHolidays,
  fetchPlanLabels,
  fetchPlans,
  fetchProgressDaily,
  fetchProgressFiles,
  updateProjectLabel,
} from '../api/client'
import type { DailyProgressItem, FileProgressItem, LabelEditTarget, PlanItem, PlanLabelItem, ProjectItem } from '../api/types'
import { getTodayString } from '../utils/date'
import { getErrorMessage } from '../utils/errors'
import { buildEvenDaily, countBusinessDays, parseDailyCsv } from '../utils/plans'
import { useConfirmDialog } from './confirmDialogContext'
import { PlanCreateScreen } from './plans/PlanCreateScreen'
import { PlanLabelCreateScreen } from './plans/PlanLabelCreateScreen'
import { PlanLabelEditScreen } from './plans/PlanLabelEditScreen'
import { PlanListScreen } from './plans/PlanListScreen'
import type { PlanFormState } from './plans/planFormTypes'
import type { PlanVersionModalChanges } from './plans/PlanVersionModal'

interface PlanResult {
  testingId: number
  plans: PlanItem[]
  planLabels: PlanLabelItem[]
  files: FileProgressItem[]
  daily: DailyProgressItem[]
  error: string | null
}

export type PlanEditorMode = 'list' | 'create' | 'label' | 'label-edit'

export function PlanEditor({
  project,
  mode,
  onBack,
  onOpenScreen,
  onChanged,
  onDirtyChange,
}: {
  project: ProjectItem
  /** 表示モードは App の履歴スタックから渡る（ブラウザバックで一段ずつ戻れるようにするため）。 */
  mode: PlanEditorMode
  /** 一段戻る（サブ画面→一覧、一覧→概要）。未保存ガードは App 側で行う。 */
  onBack: () => void
  /** サブ画面（計画線作成・識別子）へ一段進む。 */
  onOpenScreen: (mode: Exclude<PlanEditorMode, 'list'>) => void
  onChanged: () => void
  onDirtyChange: (dirty: boolean) => void
}) {
  const confirm = useConfirmDialog()
  const [result, setResult] = useState<PlanResult | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [labelInput, setLabelInput] = useState('')
  const [sourceUrlInput, setSourceUrlInput] = useState('')
  const [editingPlanLabel, setEditingPlanLabel] = useState<LabelEditTarget | null>(null)
  const [modalLabel, setModalLabel] = useState<string | null | undefined>(undefined)
  const [form, setForm] = useState<PlanFormState>(() => createInitialPlanForm())
  const [initialCreateForm, setInitialCreateForm] = useState<PlanFormState>(() => createInitialPlanForm())
  const [holidayDates, setHolidayDates] = useState<Set<string>>(() => new Set())
  const [collectingLabel, setCollectingLabel] = useState<string | null>(null)
  const [collectingAll, setCollectingAll] = useState(false)
  const [collectErrors, setCollectErrors] = useState<Record<string, string>>({})

  const loadPlanLabels = () => fetchPlanLabels(project.testing_id).catch(() => [] as PlanLabelItem[])

  const loadPlans = () => {
    Promise.all([
      fetchPlans(project.testing_id),
      loadPlanLabels(),
      fetchProgressFiles(project.testing_id).catch(() => [] as FileProgressItem[]),
      fetchProgressDaily(project.testing_id).catch(() => [] as DailyProgressItem[]),
    ])
      .then(([plans, planLabels, files, daily]) =>
        setResult({ testingId: project.testing_id, plans, planLabels, files, daily, error: null }),
      )
      .catch((err) =>
        setResult({
          testingId: project.testing_id,
          plans: [],
          planLabels: [],
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
      loadPlanLabels(),
      fetchProgressFiles(project.testing_id).catch(() => [] as FileProgressItem[]),
      fetchProgressDaily(project.testing_id).catch(() => [] as DailyProgressItem[]),
    ])
      .then(([plans, planLabels, files, daily]) => {
        if (!ignore) {
          setResult({ testingId: project.testing_id, plans, planLabels, files, daily, error: null })
        }
      })
      .catch((err) => {
        if (!ignore) {
          setResult({
            testingId: project.testing_id,
            plans: [],
            planLabels: [],
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
    onDirtyChange(
      (mode === 'create' && !isSamePlanForm(form, initialCreateForm)) ||
        (mode === 'label' && (labelInput.trim() !== '' || sourceUrlInput.trim() !== '')) ||
        (mode === 'label-edit' &&
          editingPlanLabel !== null &&
          (labelInput.trim() !== editingPlanLabel.label || sourceUrlInput.trim() !== (editingPlanLabel.source_url ?? ''))),
    )
  }, [editingPlanLabel, form, initialCreateForm, labelInput, mode, onDirtyChange, sourceUrlInput])

  useEffect(() => {
    return () => onDirtyChange(false)
  }, [onDirtyChange])

  const loading = result?.testingId !== project.testing_id
  const plans = result?.testingId === project.testing_id ? result.plans : []
  const planLabels = result?.testingId === project.testing_id ? result.planLabels : []
  const files = result?.testingId === project.testing_id ? result.files : []
  const daily = result?.testingId === project.testing_id ? result.daily : []
  const actualLabels = Array.from(
    new Set(files.map((file) => file.label).filter((label): label is string => Boolean(label))),
  ).sort((a, b) => a.localeCompare(b))
  const labels = Array.from(
    new Set([
      ...actualLabels,
      ...planLabels.map((item) => item.label),
      ...plans.map((plan) => plan.label).filter((label): label is string => Boolean(label)),
    ]),
  ).sort((a, b) => a.localeCompare(b))
  const refreshableLabels = planLabels
    .filter((item) => Boolean(item.source_url && item.source_url.trim()))
    .map((item) => item.label)
  const availableCasesByLabel = files.reduce<Record<string, number>>((casesByLabel, file) => {
    if (file.label) {
      casesByLabel[file.label] = (casesByLabel[file.label] ?? 0) + file.available_cases
    }
    return casesByLabel
  }, {})
  // 未設定（label なし）バケット: label を持たないファイルの集計。識別子別の行と共存させる。
  const unlabeledFiles = files.filter((file) => !file.label)
  const hasUnlabeledData = unlabeledFiles.length > 0
  const unlabeledAvailableCases = unlabeledFiles.reduce(
    (total, file) => total + file.available_cases,
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
  const closePlanSubscreen = () => {
    onDirtyChange(false)
    onBack()
  }
  const handleRefreshLabel = (label: string) => {
    if (collectingLabel !== null) {
      return
    }
    setCollectingLabel(label)
    setCollectErrors((prev) => {
      if (!(label in prev)) {
        return prev
      }
      const next = { ...prev }
      delete next[label]
      return next
    })
    collectLabel(project.testing_id, label)
      .then((result) => {
        const failure = result.failed[0]
        if (failure) {
          setCollectErrors((prev) => ({ ...prev, [label]: failure.message }))
          return
        }
        if (result.targets === 0) {
          setCollectErrors((prev) => ({ ...prev, [label]: 'URLが登録されていないため取得できませんでした' }))
          return
        }
        loadPlans()
        onChanged()
      })
      .catch((err) => {
        setCollectErrors((prev) => ({ ...prev, [label]: getErrorMessage(err) }))
      })
      .finally(() => setCollectingLabel(null))
  }

  const handleRefreshAll = async () => {
    if (collectingLabel !== null || collectingAll) {
      return
    }
    const targets = refreshableLabels
    if (targets.length === 0) {
      return
    }
    setCollectingAll(true)
    setCollectErrors({})
    const errors: Record<string, string> = {}
    try {
      for (const label of targets) {
        setCollectingLabel(label)
        try {
          const result = await collectLabel(project.testing_id, label)
          const failure = result.failed[0]
          if (failure) {
            errors[label] = failure.message
          } else if (result.targets === 0) {
            errors[label] = 'URLが登録されていないため取得できませんでした'
          }
        } catch (err) {
          errors[label] = getErrorMessage(err)
        }
        setCollectErrors({ ...errors })
      }
    } finally {
      setCollectingLabel(null)
      setCollectingAll(false)
      loadPlans()
      onChanged()
    }
  }

  const openLabelCreateScreen = () => {
    setFormError(null)
    setEditingPlanLabel(null)
    setLabelInput('')
    setSourceUrlInput('')
    onOpenScreen('label')
  }

  const openLabelEditScreen = (planLabel: LabelEditTarget) => {
    setFormError(null)
    setEditingPlanLabel(planLabel)
    setLabelInput(planLabel.label)
    setSourceUrlInput(planLabel.source_url ?? '')
    onOpenScreen('label-edit')
  }

  const cancelLabelEdit = async () => {
    if (
      editingPlanLabel !== null &&
      (labelInput.trim() !== editingPlanLabel.label || sourceUrlInput.trim() !== (editingPlanLabel.source_url ?? ''))
    ) {
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
    setEditingPlanLabel(null)
    setLabelInput('')
    setSourceUrlInput('')
    closePlanSubscreen()
  }

  const cancelLabelCreate = async () => {
    if (labelInput.trim() !== '' || sourceUrlInput.trim() !== '') {
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
    setLabelInput('')
    setSourceUrlInput('')
    closePlanSubscreen()
  }

  const submitPlanLabel = async (event: FormEvent) => {
    event.preventDefault()
    setFormError(null)

    const label = labelInput.trim()
    const sourceUrl = normalizeSourceUrl(sourceUrlInput)
    if (!label) {
      setFormError('識別子を入力してください')
      return
    }
    if (labels.includes(label)) {
      setFormError('同じ識別子がすでに存在します')
      return
    }
    if (!isValidOptionalUrl(sourceUrl)) {
      setFormError('SharePoint 共有 URL は http:// または https:// で始まる URL を入力してください')
      return
    }

    setSubmitting(true)
    createPlanLabel(project.testing_id, { label, source_url: sourceUrl })
      .then(() => {
        loadPlans()
        onChanged()
        setLabelInput('')
        setSourceUrlInput('')
        closePlanSubscreen()
      })
      .catch((err) => {
        if (isNotFoundError(err)) {
          setFormError('識別子登録APIが見つかりません。')
          return
        }
        setFormError(getErrorMessage(err))
      })
      .finally(() => setSubmitting(false))
  }

  const submitPlanLabelEdit = async (event: FormEvent) => {
    event.preventDefault()
    if (editingPlanLabel === null) {
      return
    }
    setFormError(null)

    const label = labelInput.trim()
    const sourceUrl = normalizeSourceUrl(sourceUrlInput)
    if (!label) {
      setFormError('識別子を入力してください')
      return
    }
    if (label !== editingPlanLabel.label && labels.includes(label)) {
      setFormError('同じ識別子がすでに存在します')
      return
    }
    if (!isValidOptionalUrl(sourceUrl)) {
      setFormError('SharePoint 共有 URL は http:// または https:// で始まる URL を入力してください')
      return
    }

    setSubmitting(true)
    updateProjectLabel(project.testing_id, { old_label: editingPlanLabel.label, label, source_url: sourceUrl })
      .then(() => {
        loadPlans()
        onChanged()
        setEditingPlanLabel(null)
        setLabelInput('')
        setSourceUrlInput('')
        closePlanSubscreen()
      })
      .catch((err) => {
        if (isNotFoundError(err)) {
          setFormError('識別子編集APIが見つかりません。バックエンドを最新化して再起動してください。')
          return
        }
        setFormError(getErrorMessage(err))
      })
      .finally(() => setSubmitting(false))
  }

  const handleDeletePlanLabel = async () => {
    if (editingPlanLabel === null) {
      return
    }
    const confirmed = await confirm({
      title: '識別子の削除',
      message: 'この識別子と、この識別子に作成した計画線を削除します。続行しますか。',
      confirmLabel: '削除',
      danger: true,
    })
    if (!confirmed) {
      return
    }

    setSubmitting(true)
    deleteProjectLabel(project.testing_id, editingPlanLabel.label)
      .then(() => {
        loadPlans()
        onChanged()
        setEditingPlanLabel(null)
        setLabelInput('')
        setSourceUrlInput('')
        closePlanSubscreen()
      })
      .catch((err) => {
        if (isNotFoundError(err)) {
          setFormError('識別子削除APIが見つかりません。バックエンドを最新化して再起動してください。')
          return
        }
        setFormError(getErrorMessage(err))
      })
      .finally(() => setSubmitting(false))
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
    const plannedTotal =
      label === null
        ? unlabeledAvailableCases > 0
          ? String(unlabeledAvailableCases)
          : ''
        : availableCasesByLabel[label] !== undefined
          ? String(availableCasesByLabel[label])
          : ''
    const startDate = initialDateRange?.start_date ?? initialForm.start_date
    const endDate = initialDateRange?.end_date ?? initialForm.end_date
    const nextForm = {
      ...initialForm,
      label: label ?? '',
      planned_total_cases: plannedTotal,
      daily_count_per_day: calculateDailyCountText(plannedTotal, startDate, endDate, holidayDates),
      business_days: calculateBusinessDaysText(startDate, endDate, holidayDates),
      start_date: startDate,
      end_date: endDate,
    }
    setFormError(null)
    setForm(nextForm)
    setInitialCreateForm(nextForm)
    onOpenScreen('create')
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
    closePlanSubscreen()
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

    setSubmitting(true)
    createPlan(project.testing_id, {
      label: targetLabel,
      reason: form.reason.trim() || null,
      planned_total_cases: plannedTotal,
      start_date: form.start_date,
      end_date: form.end_date,
      activate: form.activate,
      daily,
    })
      .then(() => {
        loadPlans()
        onChanged()
        closePlanSubscreen()
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

  if (mode === 'label-edit' && editingPlanLabel !== null) {
    return (
      <PlanLabelEditScreen
        loading={loading}
        error={result?.error}
        planLabel={editingPlanLabel}
        label={labelInput}
        sourceUrl={sourceUrlInput}
        formError={formError}
        submitting={submitting}
        onLabelChange={setLabelInput}
        onSourceUrlChange={setSourceUrlInput}
        onCancel={cancelLabelEdit}
        onSubmit={submitPlanLabelEdit}
        onDelete={handleDeletePlanLabel}
      />
    )
  }

  if (mode === 'label') {
    return (
      <PlanLabelCreateScreen
        loading={loading}
        error={result?.error}
        label={labelInput}
        sourceUrl={sourceUrlInput}
        formError={formError}
        submitting={submitting}
        onLabelChange={setLabelInput}
        onSourceUrlChange={setSourceUrlInput}
        onCancel={cancelLabelCreate}
        onSubmit={submitPlanLabel}
      />
    )
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
        projectStartDate={project.planned_start_date}
        projectEndDate={project.planned_end_date}
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
      unlabeledAvailableCases={unlabeledAvailableCases}
      hasUnlabeledData={hasUnlabeledData}
      plans={plans}
      planLabels={planLabels}
      holidays={holidayDates}
      submitting={submitting}
      collectingLabel={collectingLabel}
      collectingAll={collectingAll}
      refreshableCount={refreshableLabels.length}
      collectErrors={collectErrors}
      modalLabel={modalLabel}
      selectedModalPlans={selectedModalPlans}
      onBack={onBack}
      onAddLabel={openLabelCreateScreen}
      onEditLabel={openLabelEditScreen}
      onRefreshLabel={handleRefreshLabel}
      onRefreshAll={handleRefreshAll}
      onCreate={openCreateScreen}
      onManage={(label) => setModalLabel(label)}
      onSaveModal={handleSaveModalChanges}
      onCloseModal={() => setModalLabel(undefined)}
    />
  )
}


function normalizeSourceUrl(value: string): string | null {
  const normalized = value.trim()
  return normalized === '' ? null : normalized
}

function isValidOptionalUrl(value: string | null): boolean {
  return value === null || value.startsWith('http://') || value.startsWith('https://')
}
function createInitialPlanForm(): PlanFormState {
  const today = getTodayString()
  return {
    label: '',
    reason: '',
    planned_total_cases: '',
    daily_count_per_day: '',
    business_days: '',
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
    left.daily_count_per_day === right.daily_count_per_day &&
    left.business_days === right.business_days &&
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

function calculateDailyCountText(
  plannedTotalText: string,
  startDate: string,
  endDate: string,
  holidays: Set<string>,
) {
  const plannedTotal = Number(plannedTotalText)
  if (!Number.isFinite(plannedTotal) || plannedTotal <= 0 || !startDate || !endDate || startDate > endDate) {
    return ''
  }
  const businessDays = countBusinessDays(startDate, endDate, holidays)
  if (businessDays === 0) {
    return ''
  }
  return formatDailyCount(plannedTotal / businessDays)
}

function calculateBusinessDaysText(startDate: string, endDate: string, holidays: Set<string>) {
  const businessDays = countBusinessDays(startDate, endDate, holidays)
  return businessDays > 0 ? String(businessDays) : ''
}

function formatDailyCount(value: number) {
  if (Number.isInteger(value)) {
    return String(value)
  }
  return value.toFixed(1)
}

function isNotFoundError(err: unknown) {
  return getErrorMessage(err).includes('404 Not Found')
}

