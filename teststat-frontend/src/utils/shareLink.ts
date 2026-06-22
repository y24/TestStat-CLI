// プロジェクトの共有用ディープリンク（/tstat/<testing_id>）の生成・読取・URL 正規化。
//
// 通常のナビゲーションでは testing_id を URL に出さず、アドレスバーは常にベースパス（例 /tstat/）
// のままにする。共有リンクをコピーしたときだけ id 付き URL を作り、それを開いたときは起動時に
// id を読み取って選択へ反映したのち、アドレスバーをベースパスへ正規化する。

// import.meta.env.BASE_URL は末尾スラッシュ付き（例: '/tstat/' または '/'）。
const BASE_PATH = import.meta.env.BASE_URL

/** 共有用 URL（絶対 URL）を組み立てる。例: http://host/tstat/1001 */
export function buildProjectShareUrl(testingId: number): string {
  return `${window.location.origin}${BASE_PATH}${testingId}`
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

/** アドレスバーをベースパスへ正規化する（履歴は積まない）。 */
export function normalizeUrlToBase(): void {
  if (window.location.pathname !== BASE_PATH) {
    window.history.replaceState(null, '', BASE_PATH)
  }
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
