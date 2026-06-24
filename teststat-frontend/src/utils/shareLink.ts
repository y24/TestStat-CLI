// アプリ内ロケーションと URL（パス）の対応付け。
//
// ベースパス（例 /tstat/）自体はダッシュボード、その配下の最初のセグメントに testing_id を
// 付けた /tstat/<testing_id> は個別プロジェクトの PB 図ページを表す。共有リンクのコピーや
// ダッシュボード/プロジェクト間の遷移ではこのパスをそのままアドレスバーへ反映する。

// import.meta.env.BASE_URL は末尾スラッシュ付き（例: '/tstat/' または '/'）。
const BASE_PATH = import.meta.env.BASE_URL

/** ダッシュボードのパス（ベースパスそのもの）。例: /tstat/ */
export function buildDashboardPath(): string {
  return BASE_PATH
}

/** 個別プロジェクトのパス。例: /tstat/1001 */
export function buildProjectPath(testingId: number): string {
  return `${BASE_PATH}${testingId}`
}

/** 共有用 URL（絶対 URL）を組み立てる。例: http://host/tstat/1001 */
export function buildProjectShareUrl(testingId: number): string {
  return `${window.location.origin}${buildProjectPath(testingId)}`
}

/** 現在の URL（ベースパス配下の最初のセグメント）から testing_id を読み取る。無効なら null。 */
export function readTestingIdFromUrl(): number | null {
  const path = window.location.pathname
  if (!path.startsWith(BASE_PATH)) {
    return null
  }
  const segment = path.slice(BASE_PATH.length).replace(/\/+$/, '').split('/')[0]
  if (segment === '') {
    return null
  }
  const parsed = Number(segment)
  return Number.isInteger(parsed) ? parsed : null
}

/** クリップボードへコピー。http（非セキュアコンテキスト）でも動くようフォールバックする。 */
export async function copyTextToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // フォールバックへ
    }
  }

  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.top = '-1000px'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(textarea)
    return ok
  } catch {
    return false
  }
}
