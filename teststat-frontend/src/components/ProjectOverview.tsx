import { useEffect, useRef, useState } from 'react'
import type { BugStateColorSettings, PbChartSettings, ProjectItem } from '../api/types'
import { formatDate } from '../utils/date'
import { buildProjectShareUrl, copyTextToClipboard } from '../utils/shareLink'
import type { ProgressStatusThresholds } from '../utils/statusThresholds'
import { PbChartPanel } from './PbChartPanel'
import { LockIcon } from './icons/LockIcon'
import { Check, ClipboardList, FilePenLine, Link2 } from 'lucide-react'

export function ProjectOverview({
  project,
  progressStatusThresholds,
  pbChartSettings,
  bugStateColorSettings,
  onCreate,
  onEdit,
  onPlans,
}: {
  project: ProjectItem | null
  progressStatusThresholds: ProgressStatusThresholds
  pbChartSettings: PbChartSettings
  bugStateColorSettings: BugStateColorSettings
  onCreate: () => void
  onEdit: () => void
  onPlans: () => void
}) {
  if (!project) {
    return (
      <div className="empty-state">
        <h1>プロジェクトを作成してください</h1>
        <p>Testing ID を登録すると、CLI から届いた実績と自動で紐付きます。</p>
        <button className="primary-button large" type="button" onClick={onCreate}>
          + プロジェクト作成
        </button>
      </div>
    )
  }

  const status = getProjectStatus(project)
  const needsPlanInput = project.has_actuals && project.active_plan_count === 0
  const plannedPeriod =
    project.planned_start_date && project.planned_end_date
      ? `${formatDate(project.planned_start_date)} ~ ${formatDate(project.planned_end_date)}`
      : null

  return (
    <div className="content-shell project-overview">
      <header className="content-header">
        <div>
          <h1 className="project-title">
            {project.archived && <LockIcon />}
            <span>{project.name}</span>
            <ShareLinkButton testingId={project.testing_id} />
          </h1>
          {plannedPeriod && <div className="project-planned-period">予定期間: {plannedPeriod}</div>}
          <div className="project-status-row">
            <div className={`project-status ${status.className}`}>
              <span className="status-dot" aria-hidden="true" />
              {status.label}
            </div>
            {needsPlanInput && (
              <span className="project-plan-missing-badge" title="テスト計画の入力が必要です。">
                未計画
              </span>
            )}
          </div>
        </div>
        <div className="header-actions">
          <button className="secondary-button icon-text-button" type="button" onClick={onEdit}>
            <FilePenLine className="button-icon" aria-hidden="true" />
            <span>プロジェクト設定</span>
          </button>
          <button className="primary-button icon-text-button" type="button" onClick={onPlans}>
            <ClipboardList className="button-icon" aria-hidden="true" strokeWidth={2.2} />
            <span>テスト計画・管理</span>
          </button>
        </div>
      </header>

      <PbChartPanel
        key={project.testing_id}
        project={project}
        pbChartSettings={pbChartSettings}
        bugStateColorSettings={bugStateColorSettings}
        progressStatusThresholds={progressStatusThresholds}
        onPlans={onPlans}
      />
    </div>
  )
}

function ShareLinkButton({ testingId }: { testingId: number }) {
  const [copied, setCopied] = useState(false)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
  }, [])

  const handleCopy = async () => {
    const ok = await copyTextToClipboard(buildProjectShareUrl(testingId))
    if (!ok) {
      return
    }
    setCopied(true)
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    timeoutRef.current = setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      type="button"
      className={`share-link-button${copied ? ' copied' : ''}`}
      onClick={handleCopy}
      title={copied ? 'リンクをコピーしました' : 'このプロジェクトへのリンクをコピー'}
      aria-label={copied ? 'リンクをコピーしました' : 'このプロジェクトへのリンクをコピー'}
    >
      {copied ? (
        <Check className="share-link-icon" aria-hidden="true" />
      ) : (
        <Link2 className="share-link-icon" aria-hidden="true" />
      )}
    </button>
  )
}

function getProjectStatus(project: ProjectItem): { label: string; className: string } {
  if (!project.has_actuals) {
    return { label: '未開始', className: 'not-started' }
  }
  if (project.actual_all_completed) {
    return { label: '完了', className: 'completed' }
  }
  return { label: '進行中', className: 'active' }
}


