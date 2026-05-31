import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { createProject, deleteProject, fetchProgressSummary, updateProject } from '../api/client'
import type { ProjectItem } from '../api/types'
import { getErrorMessage } from '../utils/errors'
import { useConfirmDialog } from './confirmDialogContext'

interface ProjectFormState {
  testing_id: string
  name: string
  archived: boolean
}

const emptyForm: ProjectFormState = {
  testing_id: '',
  name: '',
  archived: false,
}

export function ProjectEditor({
  mode,
  project,
  onCancel,
  onSaved,
  onDeleted,
}: {
  mode: 'new' | 'edit'
  project: ProjectItem | null
  onCancel: () => void
  onSaved: (project: ProjectItem) => void
  onDeleted?: (testingId: number) => void
}) {
  const confirm = useConfirmDialog()
  const [form, setForm] = useState<ProjectFormState>(() =>
    project
      ? {
          testing_id: String(project.testing_id),
          name: project.name,
          archived: project.archived,
        }
      : emptyForm,
  )
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const autoFilledNameRef = useRef<string | null>(project?.name ?? null)

  useEffect(() => {
    if (mode !== 'new') {
      return
    }

    const testingId = Number(form.testing_id)
    if (!Number.isInteger(testingId) || testingId <= 0) {
      autoFilledNameRef.current = null
      return
    }

    let active = true
    const timeoutId = window.setTimeout(() => {
      fetchProgressSummary(testingId)
        .then((summary) => {
          if (!active) {
            return
          }
          setForm((current) => {
            const canAutoFill =
              !current.name.trim() ||
              (autoFilledNameRef.current !== null && current.name === autoFilledNameRef.current)
            autoFilledNameRef.current = summary.project_name
            if (!canAutoFill) {
              return current
            }
            return { ...current, name: summary.project_name }
          })
        })
        .catch(() => {
          if (!active) {
            return
          }
          autoFilledNameRef.current = null
        })
    }, 300)

    return () => {
      active = false
      window.clearTimeout(timeoutId)
    }
  }, [form.testing_id, mode])

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setFormError(null)

    const testingId = Number(form.testing_id)
    if (!Number.isInteger(testingId) || testingId <= 0) {
      setFormError('testing_id は正の整数で入力してください')
      return
    }
    if (!form.name.trim()) {
      setFormError('表示名を入力してください')
      return
    }

    setSubmitting(true)
    const request =
      mode === 'new'
        ? createProject({
            testing_id: testingId,
            name: form.name.trim(),
          })
        : updateProject(testingId, {
            name: form.name.trim(),
            archived: form.archived,
          })

    request
      .then(onSaved)
      .catch((err) => setFormError(getErrorMessage(err)))
      .finally(() => setSubmitting(false))
  }

  const handleDelete = async () => {
    if (!project || !onDeleted) {
      return
    }
    const confirmed = await confirm({
      title: 'プロジェクトの削除',
      message: `testing_id ${project.testing_id} のプロジェクトと計画を削除します。実績データは削除されません。`,
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
    <div className="content-shell narrow">
      <header className="content-header">
        <div>
          <div className="eyebrow">プロジェクト</div>
          <h1>{mode === 'new' ? '新規作成' : '編集'}</h1>
        </div>
      </header>

      <form className="editor-form" onSubmit={submit}>
        {formError && <div className="form-error">{formError}</div>}
        <label>
          <span>testing_id</span>
          <input
            type="number"
            min="1"
            value={form.testing_id}
            disabled={mode === 'edit' || submitting}
            onChange={(event) => {
              autoFilledNameRef.current = null
              setForm({ ...form, testing_id: event.target.value })
            }}
            required
          />
        </label>
        <label>
          <span>表示名</span>
          <input
            type="text"
            maxLength={255}
            value={form.name}
            disabled={submitting}
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
        {mode === 'edit' && (
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={form.archived}
              disabled={submitting}
              onChange={(event) => setForm({ ...form, archived: event.target.checked })}
            />
            <span>アーカイブ済みにする</span>
          </label>
        )}

        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={submitting}>
            {submitting ? '保存中...' : '保存'}
          </button>
          <button className="secondary-button" type="button" onClick={onCancel} disabled={submitting}>
            キャンセル
          </button>
          {mode === 'edit' && (
            <button className="danger-button" type="button" onClick={handleDelete} disabled={submitting}>
              削除
            </button>
          )}
        </div>
      </form>
    </div>
  )
}
