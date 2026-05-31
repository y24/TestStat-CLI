import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { createHoliday, fetchHolidays, syncHolidays } from '../api/client'
import type { HolidayItem } from '../api/types'
import { formatDate } from '../utils/date'
import { getErrorMessage } from '../utils/errors'
import {
  DEFAULT_PROGRESS_STATUS_THRESHOLDS,
  normalizeProgressStatusThresholds,
  type ProgressStatusThresholds,
} from '../utils/statusThresholds'

const HOLIDAY_COLLAPSED_ROWS = 6

export function SettingsScreen({
  progressStatusThresholds,
  onProgressStatusThresholdsChange,
}: {
  progressStatusThresholds: ProgressStatusThresholds
  onProgressStatusThresholdsChange: (thresholds: ProgressStatusThresholds) => Promise<ProgressStatusThresholds>
}) {
  const [holidays, setHolidays] = useState<HolidayItem[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [showAllHolidays, setShowAllHolidays] = useState(false)
  const [holidayForm, setHolidayForm] = useState({ date: '', name: '' })
  const [thresholdForm, setThresholdForm] = useState(progressStatusThresholds)
  const [savingThresholds, setSavingThresholds] = useState(false)

  const loadHolidays = () => {
    setLoading(true)
    setError(null)
    fetchHolidays()
      .then(setHolidays)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    let ignore = false
    fetchHolidays()
      .then((items) => {
        if (!ignore) {
          setHolidays(items)
        }
      })
      .catch((err) => {
        if (!ignore) {
          setError(getErrorMessage(err))
        }
      })
      .finally(() => {
        if (!ignore) {
          setLoading(false)
        }
      })
    return () => {
      ignore = true
    }
  }, [])

  const handleSync = () => {
    setSyncing(true)
    setError(null)
    setMessage(null)
    syncHolidays()
      .then((result) => {
        setHolidays(result.holidays)
        setMessage(`${result.updated}件の祝日を更新しました。`)
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSyncing(false))
  }

  const handleAddHoliday = (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setMessage(null)
    const date = holidayForm.date
    const name = holidayForm.name.trim()
    if (!date || !name) {
      setError('日付と祝日名を入力してください。')
      return
    }
    setAdding(true)
    createHoliday({ date, name })
      .then((holiday) => {
        setHolidays((current) => upsertHolidayItem(current, holiday))
        setHolidayForm({ date: '', name: '' })
        setMessage(`${formatDate(holiday.date)} ${holiday.name} を追加しました。`)
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setAdding(false))
  }

  const handleSaveThresholds = (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setMessage(null)

    const thresholds = normalizeProgressStatusThresholds(thresholdForm)
    if (!(thresholds.caution > thresholds.warning)) {
      setError('注意しきい値は警告しきい値より大きい値にしてください。')
      return
    }

    setSavingThresholds(true)
    onProgressStatusThresholdsChange(thresholds)
      .then((saved) => {
        setThresholdForm(saved)
        setMessage('進捗状態のしきい値を保存しました。')
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSavingThresholds(false))
  }

  const handleResetThresholds = () => {
    setError(null)
    setMessage(null)
    setSavingThresholds(true)
    onProgressStatusThresholdsChange(DEFAULT_PROGRESS_STATUS_THRESHOLDS)
      .then((saved) => {
        setThresholdForm(saved)
        setMessage('進捗状態のしきい値を初期値に戻しました。')
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSavingThresholds(false))
  }

  return (
    <div className="content-shell">
      <header className="content-header">
        <div>
          <h1>設定</h1>
        </div>
      </header>

      {error && <div className="form-error">{error}</div>}
      {message && <div className="form-success">{message}</div>}

      <section className="settings-panel">
        <div className="settings-section-header">
          <div>
            <div className="panel-title">進捗状態のしきい値</div>
            <div className="panel-subtitle">完了率(対計画)の状態表示に使用します。</div>
          </div>
        </div>
        <form className="threshold-settings-form" onSubmit={handleSaveThresholds}>
          <label>
            <span className="threshold-label">
              <span className="threshold-dot caution" aria-hidden="true">●</span>
              注意以下
            </span>
            <input
              type="number"
              min="0"
              max="100"
              step="1"
              value={thresholdForm.caution}
              disabled={savingThresholds}
              onChange={(event) =>
                setThresholdForm((current) => ({ ...current, caution: Number(event.target.value) }))
              }
              required
            />
          </label>
          <label>
            <span className="threshold-label">
              <span className="threshold-dot warning" aria-hidden="true">●</span>
              警告以下
            </span>
            <input
              type="number"
              min="0"
              max="100"
              step="1"
              value={thresholdForm.warning}
              disabled={savingThresholds}
              onChange={(event) =>
                setThresholdForm((current) => ({ ...current, warning: Number(event.target.value) }))
              }
              required
            />
          </label>
          <div className="threshold-actions">
            <button
              className="secondary-button"
              type="button"
              onClick={handleResetThresholds}
              disabled={savingThresholds}
            >
              初期値に戻す
            </button>
            <button className="primary-button" type="submit" disabled={savingThresholds}>
              {savingThresholds ? '保存中...' : '保存'}
            </button>
          </div>
        </form>
      </section>

      <section className="settings-panel">
        <div className="settings-section-header">
          <div>
            <div className="panel-title">祝日一覧</div>
          </div>
          <div className="settings-section-actions">
            <button className="secondary-button" type="button" onClick={loadHolidays} disabled={loading || syncing}>
              再読込
            </button>
            <button className="primary-button" type="button" onClick={handleSync} disabled={syncing}>
              {syncing ? '更新中...' : 'APIから祝日を取得'}
            </button>
          </div>
        </div>
        <form className="holiday-add-form" onSubmit={handleAddHoliday}>
          <label>
            <span>日付</span>
            <input
              type="date"
              min="2025-01-01"
              value={holidayForm.date}
              disabled={adding}
              onChange={(event) => setHolidayForm((current) => ({ ...current, date: event.target.value }))}
              required
            />
          </label>
          <label>
            <span>祝日名</span>
            <input
              type="text"
              value={holidayForm.name}
              disabled={adding}
              onChange={(event) => setHolidayForm((current) => ({ ...current, name: event.target.value }))}
              required
            />
          </label>
          <button className="secondary-button" type="submit" disabled={adding}>
            {adding ? '追加中...' : '追加'}
          </button>
        </form>
        {loading && <div className="chart-state">祝日を読み込み中...</div>}
        {!loading && holidays.length === 0 && (
          <div className="muted-block">祝日が登録されていません。更新ボタンで取得してください。</div>
        )}
        {!loading && holidays.length > 0 && (
          <>
            <div className="plan-table-wrap">
              <table className="plan-table">
                <thead>
                  <tr>
                    <th>日付</th>
                    <th>祝日名</th>
                  </tr>
                </thead>
                <tbody>
                  {holidays
                    .slice(0, showAllHolidays ? holidays.length : HOLIDAY_COLLAPSED_ROWS)
                    .map((holiday) => (
                      <tr key={holiday.date}>
                        <td>{formatDate(holiday.date)}</td>
                        <td>{holiday.name}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
            {holidays.length > HOLIDAY_COLLAPSED_ROWS && (
              <button
                className="list-toggle-button"
                type="button"
                onClick={() => setShowAllHolidays((current) => !current)}
              >
                <span className={`chevron-icon ${showAllHolidays ? 'up' : 'down'}`} aria-hidden="true" />
                <span>{showAllHolidays ? '折りたたむ' : 'すべて表示'}</span>
              </button>
            )}
          </>
        )}
      </section>
    </div>
  )
}

function upsertHolidayItem(holidays: HolidayItem[], holiday: HolidayItem) {
  const exists = holidays.some((item) => item.date === holiday.date)
  const next = exists
    ? holidays.map((item) => (item.date === holiday.date ? holiday : item))
    : [...holidays, holiday]
  return next.sort((a, b) => a.date.localeCompare(b.date))
}
