import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import {
  createProject,
  deleteBugCountData,
  deleteProject,
  fetchAzureDevOpsWorkItem,
  updateProject,
} from '../api/client'
import type { ProjectItem } from '../api/types'
import { getErrorMessage } from '../utils/errors'
import { useConfirmDialog } from './confirmDialogContext'
import { LockIcon } from './icons/LockIcon'

interface ProjectFormState {
  testing_id: string
  name: string
  planned_start_date: string
  planned_end_date: string
  bug_count_source: 'azure_devops' | 'test_result'
  bug_parent_work_item_id: string
  bug_work_item_type: string
  bug_tag: string
}

const emptyForm: ProjectFormState = {
  testing_id: '',
  name: '',
  planned_start_date: '',
  planned_end_date: '',
  bug_count_source: 'azure_devops',
  bug_parent_work_item_id: '',
  bug_work_item_type: '',
  bug_tag: '',
}

export function ProjectEditor({
  mode,
  project,
  onCancel,
  onSaved,
  onDeleted,
  onDirtyChange,
}: {
  mode: 'new' | 'edit'
  project: ProjectItem | null
  onCancel: () => void
  onSaved: (project: ProjectItem) => void
  onDeleted?: (testingId: number) => void
  onDirtyChange: (dirty: boolean) => void
}) {
  const confirm = useConfirmDialog()
  const [form, setForm] = useState<ProjectFormState>(() =>
    project
        ? {
          testing_id: String(project.testing_id),
          name: project.name,
          planned_start_date: project.planned_start_date ?? '',
          planned_end_date: project.planned_end_date ?? '',
          bug_count_source: project.bug_count_source,
          bug_parent_work_item_id: project.bug_parent_work_item_id ? String(project.bug_parent_work_item_id) : '',
          bug_work_item_type: project.bug_work_item_type ?? '',
          bug_tag: project.bug_tag ?? '',
        }
      : emptyForm,
  )
  const [submitting, setSubmitting] = useState(false)
  const [adoLoading, setAdoLoading] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [formNotice, setFormNotice] = useState<string | null>(null)
  const autoFilledNameRef = useRef<string | null>(project?.name ?? null)
  const testingIdValue = Number(form.testing_id)
  const testingIdValid = Number.isInteger(testingIdValue) && testingIdValue > 0
  const isArchivedReadOnly = mode === 'edit' && Boolean(project?.archived)
  const deleteDisabledReason = project?.archived ? 'アーカイブ済みのプロジェクトは削除できません。' : null

  useEffect(() => {
    const dirty =
      mode === 'new'
        ? Boolean(form.testing_id.trim()) ||
          (Boolean(form.name.trim()) && form.name !== autoFilledNameRef.current) ||
          Boolean(form.planned_start_date) ||
          Boolean(form.planned_end_date) ||
          form.bug_count_source !== 'azure_devops' ||
          Boolean(form.bug_parent_work_item_id.trim()) ||
          Boolean(form.bug_work_item_type.trim()) ||
          Boolean(form.bug_tag.trim())
        : project !== null &&
          (form.name !== project.name ||
            form.planned_start_date !== (project.planned_start_date ?? '') ||
            form.planned_end_date !== (project.planned_end_date ?? '') ||
            form.bug_count_source !== project.bug_count_source ||
            form.bug_parent_work_item_id !== (project.bug_parent_work_item_id ? String(project.bug_parent_work_item_id) : '') ||
            form.bug_work_item_type !== (project.bug_work_item_type ?? '') ||
            form.bug_tag !== (project.bug_tag ?? ''))
    onDirtyChange(dirty)
  }, [form, mode, onDirtyChange, project])

  useEffect(() => {
    return () => onDirtyChange(false)
  }, [onDirtyChange])

  const handleAzureFetch = () => {
    if (!testingIdValid) {
      setFormError('Testing ID は正の整数で入力してください')
      return
    }
    setAdoLoading(true)
    setFormError(null)
    fetchAzureDevOpsWorkItem(testingIdValue)
      .then((workItem) => {
        autoFilledNameRef.current = workItem.name
        setForm((current) => ({
          ...current,
          name: workItem.name,
          planned_start_date: workItem.start_date ?? '',
          planned_end_date: workItem.end_date ?? '',
        }))
      })
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setAdoLoading(false))
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setFormError(null)
    setFormNotice(null)
    if (isArchivedReadOnly) {
      setFormError('アーカイブ済みプロジェクトは閲覧のみ可能です。編集する場合はアーカイブを解除してください。')
      return
    }

    const testingId = Number(form.testing_id)
    if (!Number.isInteger(testingId) || testingId <= 0) {
      setFormError('Testing ID は正の整数で入力してください')
      return
    }
    if (!form.name.trim()) {
      setFormError('表示名を入力してください')
      return
    }
    if (form.planned_start_date && form.planned_end_date && form.planned_start_date > form.planned_end_date) {
      setFormError('テスト期間の開始予定日と終了予定日を正しい順序で入力してください')
      return
    }
    const bugParentWorkItemId = form.bug_parent_work_item_id.trim()
      ? Number(form.bug_parent_work_item_id)
      : null
    if (bugParentWorkItemId !== null && (!Number.isInteger(bugParentWorkItemId) || bugParentWorkItemId <= 0)) {
      setFormError('親となるチケットのWork Item IDは正の整数で入力してください')
      return
    }
    setSubmitting(true)
    const plannedDates = {
      planned_start_date: form.planned_start_date || null,
      planned_end_date: form.planned_end_date || null,
      bug_count_source: form.bug_count_source,
      bug_parent_work_item_id: bugParentWorkItemId,
      bug_work_item_type: form.bug_work_item_type.trim() || null,
      bug_tag: form.bug_tag.trim() || null,
    }
    const request =
      mode === 'new'
        ? createProject({
            testing_id: testingId,
            name: form.name.trim(),
            ...plannedDates,
          })
        : updateProject(testingId, {
            name: form.name.trim(),
            ...plannedDates,
          })

    request
      .then(onSaved)
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  const handleArchiveToggle = () => {
    if (!project) {
      return
    }
    setSubmitting(true)
    setFormError(null)
    setFormNotice(null)
    updateProject(project.testing_id, {
      archived: !project.archived,
    })
      .then(onSaved)
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  const handleDeleteBugData = async () => {
    if (!project) {
      return
    }
    if (project.archived) {
      setFormError('アーカイブ済みプロジェクトは閲覧のみ可能です。編集する場合はアーカイブを解除してください。')
      return
    }
    const confirmed = await confirm({
      title: '課題チケット数データの削除',
      message: `Testing ID ${project.testing_id} の取得済み課題チケット数データを削除します。プロジェクト、計画、実績データは削除されません。`,
      confirmLabel: '削除',
      danger: true,
    })
    if (!confirmed) {
      return
    }
    setSubmitting(true)
    setFormError(null)
    setFormNotice(null)
    deleteBugCountData(project.testing_id)
      .then(() => setFormNotice('課題チケット数データを削除しました。'))
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  const handleDelete = async () => {
    if (!project || !onDeleted) {
      return
    }
    if (project.archived) {
      setFormError('アーカイブ済みプロジェクトは削除できません。削除する場合はアーカイブを解除してください。')
      return
    }
    const confirmed = await confirm({
      title: 'プロジェクトの削除',
      message: `Testing ID ${project.testing_id} のプロジェクトと計画を削除します。実績データは削除されません。`,
      confirmLabel: '削除',
      danger: true,
    })
    if (!confirmed) {
      return
    }
    setSubmitting(true)
    setFormError(null)
    deleteProject(project.testing_id)
      .then(() => onDeleted(project.testing_id))
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="content-shell narrow plan-screen">
      <header className="content-header">
        <div>
          <h1>{mode === 'new' ? '新規プロジェクト作成' : 'プロジェクト設定'}</h1>
        </div>
      </header>

      <form className="editor-form" onSubmit={submit}>
        {formError && <div className="form-error">{formError}</div>}
        {formNotice && <div className="form-success">{formNotice}</div>}
        <label>
          <span>Testing ID</span>
          <div className="ado-fetch-row">
            <input
              type="number"
              min="1"
              value={form.testing_id}
              disabled={mode === 'edit' || submitting || isArchivedReadOnly}
              onChange={(event) => {
                autoFilledNameRef.current = null
                setForm({ ...form, testing_id: event.target.value })
              }}
              required
            />
            <button
              type="button"
              className="secondary-button"
              onClick={handleAzureFetch}
              disabled={submitting || adoLoading || !testingIdValid || isArchivedReadOnly}
            >
              {adoLoading ? '取得中...' : 'AzureDevOpsから情報取得'}
            </button>
          </div>
        </label>
        <label>
          <span>表示名</span>
          <input
            type="text"
            maxLength={255}
            value={form.name}
            disabled={submitting || isArchivedReadOnly}
            onChange={(event) => {
              const nextName = event.target.value
              if (nextName !== autoFilledNameRef.current) {
                autoFilledNameRef.current = null
              }
              setForm({ ...form, name: nextName })
            }}
            required
          />
        </label>
        <div className="form-grid">
          <label>
            <span>開始日</span>
            <input
              type="date"
              value={form.planned_start_date}
              disabled={submitting || isArchivedReadOnly}
              onChange={(event) => setForm({ ...form, planned_start_date: event.target.value })}
            />
          </label>
          <label>
            <span>終了日</span>
            <input
              type="date"
              value={form.planned_end_date}
              disabled={submitting || isArchivedReadOnly}
              onChange={(event) => setForm({ ...form, planned_end_date: event.target.value })}
            />
          </label>
        </div>
        <label>
          <span>課題件数ソース</span>
          <select
            value={form.bug_count_source}
            disabled={submitting || isArchivedReadOnly}
            onChange={(event) =>
              setForm({
                ...form,
                bug_count_source: event.target.value as ProjectFormState['bug_count_source'],
              })
            }
          >
            <option value="azure_devops">Azure DevOps</option>
            <option value="test_result">テスト仕様書 - テスト実施結果ステータスを参照する</option>
          </select>
        </label>
        {form.bug_count_source === 'azure_devops' && (
          <fieldset className="ado-bug-settings">
            <legend>課題チケット抽出条件</legend>
            <label>
              <span>親チケットのWork Item ID</span>
              <input
                type="number"
                min="1"
                value={form.bug_parent_work_item_id}
                disabled={submitting || isArchivedReadOnly}
                placeholder="未設定の場合はTesting ID"
                onChange={(event) => setForm({ ...form, bug_parent_work_item_id: event.target.value })}
              />
            </label>
            <label>
              <span>Work Item Type</span>
              <input
                type="text"
                maxLength={255}
                value={form.bug_work_item_type}
                disabled={submitting || isArchivedReadOnly}
                placeholder=""
                onChange={(event) => setForm({ ...form, bug_work_item_type: event.target.value })}
              />
            </label>
            <label>
              <span>Tag</span>
              <input
                type="text"
                maxLength={255}
                value={form.bug_tag}
                disabled={submitting || isArchivedReadOnly}
                placeholder=""
                onChange={(event) => setForm({ ...form, bug_tag: event.target.value })}
              />
            </label>
          </fieldset>
        )}

        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={submitting || adoLoading || isArchivedReadOnly}>
            {submitting ? '保存中...' : '保存'}
          </button>
          <button className="secondary-button" type="button" onClick={onCancel} disabled={submitting || adoLoading}>
            キャンセル
          </button>
          {mode === 'edit' && (
            <span className="form-actions-right">
              <button
                className="secondary-button icon-text-button"
                type="button"
                onClick={handleArchiveToggle}
                disabled={submitting}
              >
                <LockIcon unlocked={project?.archived} />
                {project?.archived ? 'アーカイブ解除' : 'アーカイブ'}
              </button>
              <button
                className="secondary-button"
                type="button"
                onClick={handleDeleteBugData}
                disabled={submitting || isArchivedReadOnly}
              >
                課題データのクリア
              </button>
              <span
                className="delete-action-tooltip"
                data-tooltip={deleteDisabledReason ?? undefined}
                tabIndex={deleteDisabledReason ? 0 : undefined}
              >
                <button
                  className="danger-button"
                  type="button"
                  onClick={handleDelete}
                  disabled={submitting || Boolean(deleteDisabledReason)}
                >
                  プロジェクト削除
                </button>
              </span>
            </span>
          )}
        </div>
      </form>
    </div>
  )
}
