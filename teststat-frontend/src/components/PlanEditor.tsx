import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { activatePlan, createPlan, deletePlan, fetchPlans, fetchProgressFiles } from '../api/client'
import type { FileProgressItem, PlanItem, ProjectItem } from '../api/types'
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
  error: string | null
}

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
  const [form, setForm] = useState<PlanFormState>(() => createInitialPlanForm())

  const loadPlans = () => {
    Promise.all([
      fetchPlans(project.testing_id),
      fetchProgressFiles(project.testing_id).catch(() => [] as FileProgressItem[]),
    ])
      .then(([plans, files]) =>
        setResult({ testingId: project.testing_id, plans, files, error: null }),
      )
      .catch((err) =>
        setResult({
          testingId: project.testing_id,
          plans: [],
          files: [],
          error: getErrorMessage(err),
        }),
      )
  }

  useEffect(() => {
    let ignore = false
    Promise.all([
      fetchPlans(project.testing_id),
      fetchProgressFiles(project.testing_id).catch(() => [] as FileProgressItem[]),
    ])
      .then(([plans, files]) => {
        if (!ignore) {
          setResult({ testingId: project.testing_id, plans, files, error: null })
        }
      })
      .catch((err) => {
        if (!ignore) {
          setResult({
            testingId: project.testing_id,
            plans: [],
            files: [],
            error: getErrorMessage(err),
          })
        }
      })
    return () => {
      ignore = true
    }
  }, [project.testing_id])

  const loading = result?.testingId !== project.testing_id
  const plans = result?.testingId === project.testing_id ? result.plans : []
  const files = result?.testingId === project.testing_id ? result.files : []
  const labels = Array.from(
    new Set(files.map((file) => file.label).filter((label): label is string => Boolean(label))),
  ).sort((a, b) => a.localeCompare(b))
  const availableCasesByLabel = files.reduce<Record<string, number>>((casesByLabel, file) => {
    if (file.label) {
      casesByLabel[file.label] = (casesByLabel[file.label] ?? 0) + file.available_cases
    }
    return casesByLabel
  }, {})

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
          ? buildEvenDaily(form.start_date, form.end_date, plannedTotal)
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

    setSubmitting(true)
    createPlan(project.testing_id, {
      label: form.label.trim() || null,
      reason: form.reason.trim() || null,
      planned_total_cases: plannedTotal,
      start_date: form.start_date,
      end_date: form.end_date,
      activate: form.activate,
      daily,
    })
      .then(() => {
        setForm({
          ...form,
          reason: '',
          planned_total_cases: '',
          dailyText: '',
        })
        loadPlans()
        onChanged()
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
    setSubmitting(true)
    deletePlan(plan.id)
      .then(() => {
        loadPlans()
        onChanged()
      })
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="content-shell">
      <header className="content-header">
        <div>
          <div className="eyebrow">{project.name}</div>
          <h1>テスト計画</h1>
          <div className="header-meta">testing_id: {project.testing_id}</div>
        </div>
        <div className="header-actions">
          <button className="secondary-button" type="button" onClick={onBack}>
            ダッシュボード
          </button>
        </div>
      </header>

      {loading && <div className="chart-state">計画を読み込み中...</div>}
      {!loading && result?.error && (
        <div className="form-error">計画を取得できませんでした: {result.error}</div>
      )}
      {!loading && !result?.error && (
        <section className="plan-layout">
          <PlanVersionTable
            plans={plans}
            submitting={submitting}
            onActivate={handleActivate}
            onDelete={handleDeletePlan}
            formatDate={formatDate}
          />
          <PlanCreateForm
            form={form}
            formError={formError}
            labels={labels}
            availableCasesByLabel={availableCasesByLabel}
            submitting={submitting}
            onFormChange={setForm}
            onSubmit={submitPlan}
          />
        </section>
      )}
    </div>
  )
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
