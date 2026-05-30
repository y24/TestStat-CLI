import { useEffect, useState } from 'react'
import './App.css'
import { fetchHealth } from './api/client'

export default function App() {
  const [apiStatus, setApiStatus] = useState<'checking' | 'ok' | 'error'>('checking')

  useEffect(() => {
    fetchHealth()
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('error'))
  }, [])

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <SidebarHeader apiStatus={apiStatus} />
      </aside>
      <main className="main-area">
        <div className="placeholder">
          プロジェクトを選択してください
        </div>
      </main>
    </div>
  )
}

function SidebarHeader({ apiStatus }: { apiStatus: 'checking' | 'ok' | 'error' }) {
  return (
    <div style={{ padding: '18px 18px 8px', borderBottom: '1px solid var(--border)' }}>
      <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>
        テスト状況
      </div>
      <div style={{ fontSize: 11, color: apiStatus === 'ok' ? '#22a06b' : apiStatus === 'error' ? '#e0457b' : 'var(--muted)' }}>
        {apiStatus === 'checking' && 'API 接続確認中…'}
        {apiStatus === 'ok' && '● API 接続OK'}
        {apiStatus === 'error' && '● API 接続失敗'}
      </div>
    </div>
  )
}
