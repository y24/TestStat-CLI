import { useState } from 'react'
import type { LabelEditTarget, PlanItem, PlanLabelItem } from '../../api/types'
import { formatDate } from '../../utils/date'
import { copyTextToClipboard } from '../../utils/shareLink'
import { PlanVersionModal } from './PlanVersionModal'
import type { PlanVersionModalChanges } from './PlanVersionModal'
import { PlanVersionTable } from './PlanVersionTable'
import { ArrowLeft, Check, ClipboardList, Copy, Download, Plus, RefreshCw } from 'lucide-react'

export function PlanListScreen({
  loading,
  error,
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
  collectingLabel,
  collectingAll,
  refreshableCount,
  cliCommand,
  collectErrors,
  downloadingListYaml,
  listYamlError,
  modalLabel,
  selectedModalPlans,
  onBack,
  onAddLabel,
  onEditLabel,
  onRefreshLabel,
  onRefreshAll,
  onDownloadListYaml,
  onCreate,
  onManage,
  onSaveModal,
  onCloseModal,
}: {
  loading: boolean
  error: string | null | undefined
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
  collectingLabel: string | null
  collectingAll: boolean
  refreshableCount: number
  cliCommand: string
  collectErrors: Record<string, string>
  downloadingListYaml: boolean
  listYamlError: string | null
  modalLabel: string | null | undefined
  selectedModalPlans: PlanItem[]
  onBack: () => void
  onAddLabel: () => void
  onEditLabel: (planLabel: LabelEditTarget) => void
  onRefreshLabel: (label: string) => void
  onRefreshAll: () => void
  onDownloadListYaml: () => void
  onCreate: (label: string | null) => void
  onManage: (label: string | null) => void
  onSaveModal: (changes: PlanVersionModalChanges) => void
  onCloseModal: () => void
}) {
  const [copiedCommand, setCopiedCommand] = useState(false)

  const copyCliCommand = () => {
    copyTextToClipboard(cliCommand).then((ok) => {
      if (ok) {
        setCopiedCommand(true)
        window.setTimeout(() => setCopiedCommand(false), 1600)
      }
    })
  }

  const modalResetKey = `${modalLabel ?? 'unlabeled'}:${selectedModalPlans
    .map((plan) => `${plan.id}:${plan.is_active}`)
    .join(',')}`

  return (
    <div className="content-shell plan-screen">
      <header className="content-header">
        <div className="header-title-row">
          <button
            className="icon-button header-back-button"
            type="button"
            onClick={onBack}
            aria-label="戻る"
            title="戻る"
          >
            <ArrowLeft aria-hidden="true" />
          </button>
          <div>
            <h1 className="title-with-icon">
              <ClipboardList className="title-icon" aria-hidden="true" />
              <span>テスト計画・管理</span>
            </h1>
          </div>
        </div>
        <div className="header-actions">
          {collectEnabled && refreshableCount > 0 && (
            <button
              className={`secondary-button icon-text-button${collectingAll ? ' is-refreshing' : ''}`}
              type="button"
              disabled={submitting || collectingLabel !== null || collectingAll}
              onClick={onRefreshAll}
              title="URLが登録されている識別子をすべて取得して集計します"
            >
              <RefreshCw className="button-icon" aria-hidden="true" />
              <span>{collectingAll ? '一括更新中...' : 'すべて更新'}</span>
            </button>
          )}
          <button
            className="primary-button icon-text-button"
            type="button"
            disabled={submitting || collectingAll}
            onClick={onAddLabel}
          >
            <Plus className="button-icon" aria-hidden="true" />
            <span>集計設定を追加</span>
          </button>
        </div>
      </header>

      {loading && <div className="chart-state">計画を読み込み中...</div>}
      {!loading && error && <div className="form-error">計画を取得できませんでした: {error}</div>}
      {!loading && !error && (
        <>
          <PlanVersionTable
            labels={labels}
            actualLabels={actualLabels}
            availableCasesByLabel={availableCasesByLabel}
            unlabeledAvailableCases={unlabeledAvailableCases}
            hasUnlabeledData={hasUnlabeledData}
            plans={plans}
            planLabels={planLabels}
            holidays={holidays}
            submitting={submitting}
            collectEnabled={collectEnabled}
            collectingLabel={collectingLabel}
            collectErrors={collectErrors}
            onCreate={onCreate}
            onEditLabel={onEditLabel}
            onRefreshLabel={onRefreshLabel}
            onManage={onManage}
            formatDate={formatDate}
          />
          <section className="plan-list-panel cli-run-panel" aria-labelledby="cli-run-title">
            <div className="plan-panel-header cli-run-header">
              <div>
                <div className="panel-title" id="cli-run-title">CLI実行</div>
                <div className="panel-subtitle">
                  以下のコマンドを実行して集計を実行します。TestStat-CLI, Azure CLIのインストールが必要です。
                </div>
              </div>
            </div>
            <div className="cli-command-row">
              <input className="cli-command-input" type="text" value={cliCommand} readOnly aria-label="CLI実行コマンド" />
              <button className="secondary-button icon-text-button" type="button" onClick={copyCliCommand}>
                {copiedCommand ? <Check className="button-icon" aria-hidden="true" /> : <Copy className="button-icon" aria-hidden="true" />}
                <span>{copiedCommand ? 'コピー済み' : 'コピー'}</span>
              </button>
            </div>
            <div className="cli-yaml-row">
              <div>
                <div className="cli-yaml-title">リストファイルを取得</div>
                <div className="panel-subtitle">設定ファイルとしてダウンロードします。</div>
              </div>
              <button
                className="secondary-button icon-text-button"
                type="button"
                disabled={
                  submitting ||
                  collectingAll ||
                  collectingLabel !== null ||
                  downloadingListYaml ||
                  refreshableCount === 0
                }
                onClick={onDownloadListYaml}
              >
                <Download className="button-icon" aria-hidden="true" />
                <span>{downloadingListYaml ? '生成中...' : 'YAMLをダウンロード'}</span>
              </button>
            </div>
            {listYamlError && (
              <div className="form-error list-yaml-error">ダウンロードできませんでした: {listYamlError}</div>
            )}
          </section>
        </>
      )}
      {modalLabel !== undefined && (
        <PlanVersionModal
          key={modalResetKey}
          label={modalLabel}
          plans={selectedModalPlans}
          submitting={submitting}
          onSave={onSaveModal}
          onClose={onCloseModal}
        />
      )}
    </div>
  )
}
