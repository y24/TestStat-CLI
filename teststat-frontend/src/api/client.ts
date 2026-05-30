import type {
  HealthResponse,
  TestingItem,
  ProgressSummaryResponse,
  FileProgressItem,
  DailyProgressItem,
} from './types'

// 開発時は vite.config のプロキシ経由で localhost:18000 へ転送される。
// 本番では同一オリジン配信のため "" でよい。VITE_API_BASE_URL は未使用になるが
// 将来の別オリジン配信を想定して env ファイルに残す。
const BASE = ''

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}${text ? ': ' + text : ''}`)
  }
  return res.json() as Promise<T>
}

// ヘルスチェック
export const fetchHealth = () => get<HealthResponse>('/health')

// 実績系（既存バックエンド）
export const fetchTestings = () => get<TestingItem[]>('/api/v1/testings')
export const fetchProgressSummary = (testing_id: number) =>
  get<ProgressSummaryResponse>(`/api/v1/progress/${testing_id}`)
export const fetchProgressFiles = (testing_id: number) =>
  get<FileProgressItem[]>(`/api/v1/progress/${testing_id}/files`)
export const fetchProgressDaily = (testing_id: number) =>
  get<DailyProgressItem[]>(`/api/v1/progress/${testing_id}/daily`)
