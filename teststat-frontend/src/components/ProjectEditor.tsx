import { useState } from 'react'
import type { FormEvent } from 'react'
import { createProject, deleteProject, updateProject } from '../api/client'
import type { ProjectItem } from '../api/types'
import { formatDateTime } from '../utils/date'
import { getErrorMessage } from '../utils/errors'

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

  const handleDelete = () => {
    if (!project || !onDeleted) {
      return
    }
    const confirmed = window.confirm(
      `testing_id ${project.testing_id} のプロジェクトと計画を削除します。実績データは削除されません。`,
    )
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
            onChange={(event) => setForm({ ...form, testing_id: event.target.value })}
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
            onChange={(event) => setForm({ ...form, name: event.target.value })}
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

        {project && (
          <div className="actuals-note">
            {project.has_actuals
              ? `実績受信済み: ${formatDateTime(project.actuals_updated_at)}`
              : '実績未受信: CLI 送信後に testing_id で紐付きます'}
          </div>
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
