# TestStat

Excel テスト仕様書の集計 CLI、進捗収集バックエンド、進捗を確認・操作するフロントエンドを管理するリポジトリです。

## 構成

```text
TestStat-CLI/
├── teststat-cli/       # Excel テスト仕様書を集計する CLI ツール
├── teststat-server/    # CLI から進捗を受け取る FastAPI バックエンド
└── teststat-frontend/  # 進捗管理画面を提供する Vite + React + TypeScript フロントエンド
```

## 各プロジェクト

- CLI: [teststat-cli/README.md](teststat-cli/README.md)
- Backend: [teststat-server/README.md](teststat-server/README.md)
- Frontend: [teststat-frontend/README.md](teststat-frontend/README.md)

## TestStat-CLI: セットアップ

CLI を実行・インストールする場合は `teststat-cli` に移動して作業してください。

```powershell
cd teststat-cli
pip install -e .
tstat --help
```

## TestStat Studio: 開発環境の起動

リポジトリのルートから、別々の PowerShell で以下を実行します。

```powershell
cd teststat-server
.\.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 18000 --reload
```

```powershell
cd teststat-frontend
npm run dev
```
