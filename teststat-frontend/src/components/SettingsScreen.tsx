import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Plus, Settings, Trash2 } from 'lucide-react'
import { createHoliday, fetchHolidays, syncHolidays } from '../api/client'
import type { BugStateColorSetting, BugStateColorSettings, HolidayItem, PbChartSettings } from '../api/types'
import { formatDate } from '../utils/date'
import { getErrorMessage } from '../utils/errors'
import {
  DEFAULT_PROGRESS_STATUS_THRESHOLDS,
  normalizeProgressStatusThresholds,
  type ProgressStatusThresholds,
} from '../utils/statusThresholds'

const HOLIDAY_COLLAPSED_ROWS = 6

const BUG_STATE_COLOR_PRESETS = [
  { label: '灰色', background_color: '#f7f9fb', text_color: '#5f6b7a', border_color: '#d8dee8' },
  { label: '青色', background_color: '#eef9ff', text_color: '#0369a1', border_color: '#bae6fd' },
  { label: '薄い紫色', background_color: '#f5f0ff', text_color: '#6b46c1', border_color: '#ddd0ff' },
  { label: '紫色', background_color: '#e9d5ff', text_color: '#581c87', border_color: '#c084fc' },
  { label: '緑色', background_color: '#edf8f3', text_color: '#147d54', border_color: '#bfdacb' },
  { label: '黄色', background_color: '#fff8e6', text_color: '#8a5a00', border_color: '#f5d58a' },
  { label: '赤色', background_color: '#fff1f5', text_color: '#b4234f', border_color: '#f1bfd0' },
] as const

const DEFAULT_BUG_STATE_COLORS: BugStateColorSetting[] = [
  { state: 'New', background_color: '#f7f9fb', text_color: '#5f6b7a', border_color: '#d8dee8' },
  { state: 'In Progress', background_color: '#eef9ff', text_color: '#0369a1', border_color: '#bae6fd' },
  { state: 'Dev In Progress', background_color: '#f5f0ff', text_color: '#6b46c1', border_color: '#ddd0ff' },
  { state: 'Resolved', background_color: '#e9d5ff', text_color: '#581c87', border_color: '#c084fc' },
  { state: 'Done', background_color: '#edf8f3', text_color: '#147d54', border_color: '#bfdacb' },
  { state: 'Suspend', background_color: '#fff8e6', text_color: '#8a5a00', border_color: '#f5d58a' },
]


export function SettingsScreen({
  progressStatusThresholds,
  pbChartSettings,
  bugStateColorSettings,
  onProgressStatusThresholdsChange,
  onPbChartSettingsChange,
  onBugStateColorSettingsChange,
}: {
  progressStatusThresholds: ProgressStatusThresholds
  pbChartSettings: PbChartSettings
  bugStateColorSettings: BugStateColorSettings
  onProgressStatusThresholdsChange: (thresholds: ProgressStatusThresholds) => Promise<ProgressStatusThresholds>
  onPbChartSettingsChange: (settings: PbChartSettings) => Promise<PbChartSettings>
  onBugStateColorSettingsChange: (settings: BugStateColorSettings) => Promise<BugStateColorSettings>
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
  const [pbChartForm, setPbChartForm] = useState(pbChartSettings)
  const [savingPbChartSettings, setSavingPbChartSettings] = useState(false)
  const [bugStateColorForm, setBugStateColorForm] = useState<BugStateColorSetting[]>(bugStateColorSettings.items)
  const [savingBugStateColors, setSavingBugStateColors] = useState(false)

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


  const updateBugStateColorRow = (index: number, patch: Partial<BugStateColorSetting>) => {
    setBugStateColorForm((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)))
  }

  const applyBugStateColorPreset = (index: number, presetLabel: string) => {
    const preset = BUG_STATE_COLOR_PRESETS.find((item) => item.label === presetLabel)
    if (!preset) {
      return
    }
    updateBugStateColorRow(index, {
      background_color: preset.background_color,
      text_color: preset.text_color,
      border_color: preset.border_color,
    })
  }

  const addBugStateColorRow = () => {
    setBugStateColorForm((current) => [
      ...current,
      { state: '', background_color: '#f7f9fb', text_color: '#5f6b7a', border_color: '#d8dee8' },
    ])
  }

  const removeBugStateColorRow = (index: number) => {
    setBugStateColorForm((current) => current.filter((_, itemIndex) => itemIndex !== index))
  }

  const handleSaveBugStateColors = (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setMessage(null)

    const items = bugStateColorForm.map((item) => ({ ...item, state: item.state.trim() })).filter((item) => item.state)
    const stateKeys = items.map((item) => item.state.toLocaleLowerCase())
    if (items.length !== bugStateColorForm.length) {
      setError('State名を入力してください。')
      return
    }
    if (new Set(stateKeys).size !== stateKeys.length) {
      setError('State名が重複しています。')
      return
    }

    setSavingBugStateColors(true)
    onBugStateColorSettingsChange({ items })
      .then((saved) => {
        setBugStateColorForm(saved.items)
        setMessage('State色の設定を保存しました。')
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSavingBugStateColors(false))
  }

  const handleResetBugStateColors = () => {
    setError(null)
    setMessage(null)
    setSavingBugStateColors(true)
    onBugStateColorSettingsChange({ items: DEFAULT_BUG_STATE_COLORS })
      .then((saved) => {
        setBugStateColorForm(saved.items)
        setMessage('State色の設定を初期値に戻しました。')
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSavingBugStateColors(false))
  }

  const handleSavePbChartSettings = (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setMessage(null)

    const nextBugAxisMax = Math.floor(Number(pbChartForm.bug_axis_max))
    if (!Number.isFinite(nextBugAxisMax) || nextBugAxisMax < 1) {
      setError('不具合件数の縦軸上限は1以上の整数にしてください。')
      return
    }

    setSavingPbChartSettings(true)
    onPbChartSettingsChange({ bug_axis_max: nextBugAxisMax })
      .then((saved) => {
        setPbChartForm(saved)
        setMessage('PB図の設定を保存しました。')
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSavingPbChartSettings(false))
  }

  const handleResetPbChartSettings = () => {
    setError(null)
    setMessage(null)
    setSavingPbChartSettings(true)
    onPbChartSettingsChange({ bug_axis_max: 30 })
      .then((saved) => {
        setPbChartForm(saved)
        setMessage('PB図の設定を初期値に戻しました。')
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setSavingPbChartSettings(false))
  }

  return (
    <div className="content-shell">
      <header className="content-header">
        <div>
          <h1 className="title-with-icon">
            <Settings className="title-icon" aria-hidden="true" />
            <span>設定</span>
          </h1>
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
            <div className="panel-title">PB図</div>
            <div className="panel-subtitle">不具合件数の右側の縦軸に使用します。</div>
          </div>
        </div>
        <form className="threshold-settings-form" onSubmit={handleSavePbChartSettings}>
          <label>
            <span>不具合件数の縦軸上限</span>
            <input
              type="number"
              min="1"
              max="100000"
              step="1"
              value={pbChartForm.bug_axis_max}
              disabled={savingPbChartSettings}
              onChange={(event) => setPbChartForm({ bug_axis_max: Number(event.target.value) })}
              required
            />
          </label>
          <div className="threshold-actions">
            <button
              className="secondary-button"
              type="button"
              onClick={handleResetPbChartSettings}
              disabled={savingPbChartSettings}
            >
              初期値に戻す
            </button>
            <button className="primary-button" type="submit" disabled={savingPbChartSettings}>
              {savingPbChartSettings ? '保存中...' : '保存'}
            </button>
          </div>
        </form>
      </section>


      <section className="settings-panel">
        <div className="settings-section-header">
          <div>
            <div className="panel-title">チケット State 色</div>
            <div className="panel-subtitle">未解決チケット一覧と対応見送りチケット一覧の State バッジに使用します。</div>
          </div>
          <div className="settings-section-actions">
            <button
              className="secondary-button icon-text-button"
              type="button"
              onClick={addBugStateColorRow}
              disabled={savingBugStateColors}
            >
              <Plus className="button-icon" aria-hidden="true" />
              <span>追加</span>
            </button>
          </div>
        </div>
        <form className="bug-state-color-form" onSubmit={handleSaveBugStateColors}>
          <div className="bug-state-color-list">
            {bugStateColorForm.map((item, index) => (
              <div className="bug-state-color-row" key={`${index}-${item.state}`}>
                <label className="bug-state-name-field">
                  <span>State</span>
                  <input
                    type="text"
                    value={item.state}
                    disabled={savingBugStateColors}
                    onChange={(event) => updateBugStateColorRow(index, { state: event.target.value })}
                    required
                  />
                </label>
                <label>
                  <span>候補</span>
                  <select
                    value={findBugStatePresetLabel(item)}
                    disabled={savingBugStateColors}
                    onChange={(event) => applyBugStateColorPreset(index, event.target.value)}
                  >
                    <option value="">カスタム</option>
                    {BUG_STATE_COLOR_PRESETS.map((preset) => (
                      <option key={preset.label} value={preset.label}>
                        {preset.label}
                      </option>
                    ))}
                  </select>
                </label>
                <ColorField
                  label="背景"
                  value={item.background_color}
                  disabled={savingBugStateColors}
                  onChange={(value) => updateBugStateColorRow(index, { background_color: value })}
                />
                <ColorField
                  label="文字"
                  value={item.text_color}
                  disabled={savingBugStateColors}
                  onChange={(value) => updateBugStateColorRow(index, { text_color: value })}
                />
                <ColorField
                  label="枠"
                  value={item.border_color}
                  disabled={savingBugStateColors}
                  onChange={(value) => updateBugStateColorRow(index, { border_color: value })}
                />
                <div className="bug-state-color-preview" aria-label="プレビュー">
                  <span
                    className="bug-state-badge"
                    style={{
                      backgroundColor: item.background_color,
                      borderColor: item.border_color,
                      color: item.text_color,
                    }}
                  >
                    {item.state || 'State'}
                  </span>
                </div>
                <button
                  className="icon-button danger-icon-button"
                  type="button"
                  onClick={() => removeBugStateColorRow(index)}
                  disabled={savingBugStateColors}
                  title="削除"
                  aria-label="削除"
                >
                  <Trash2 aria-hidden="true" />
                </button>
              </div>
            ))}
          </div>
          <div className="threshold-actions bug-state-color-actions">
            <button
              className="secondary-button"
              type="button"
              onClick={handleResetBugStateColors}
              disabled={savingBugStateColors}
            >
              初期値に戻す
            </button>
            <button className="primary-button" type="submit" disabled={savingBugStateColors}>
              {savingBugStateColors ? '保存中...' : '保存'}
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


function ColorField({
  label,
  value,
  disabled,
  onChange,
}: {
  label: string
  value: string
  disabled: boolean
  onChange: (value: string) => void
}) {
  return (
    <label className="bug-state-color-field">
      <span>{label}</span>
      <input type="color" value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)} />
    </label>
  )
}

function findBugStatePresetLabel(item: BugStateColorSetting) {
  return (
    BUG_STATE_COLOR_PRESETS.find(
      (preset) =>
        preset.background_color === item.background_color &&
        preset.text_color === item.text_color &&
        preset.border_color === item.border_color,
    )?.label ?? ''
  )
}

function upsertHolidayItem(holidays: HolidayItem[], holiday: HolidayItem) {
  const exists = holidays.some((item) => item.date === holiday.date)
  const next = exists
    ? holidays.map((item) => (item.date === holiday.date ? holiday : item))
    : [...holidays, holiday]
  return next.sort((a, b) => a.date.localeCompare(b.date))
}

