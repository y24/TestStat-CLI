# TestStat Frontend

TestStat のフロントエンドです。Vite + React + TypeScript で構成されています。

## 前提

- Node.js 20.19.0 以上、または 22.12.0 以上
- npm
- バックエンド API
  - 開発時のデフォルト接続先: `http://localhost:18000`
  - 開発サーバーでは `/api` と `/health` がバックエンドへプロキシされます。

## 初期セットアップ

PowerShell でこのディレクトリへ移動し、依存パッケージをインストールします。

```powershell
# ディレクトリへ移動
cd teststat-frontend

# 依存パッケージをインストール
npm ci

# 環境変数ファイルを作成
Copy-Item .env.example .env
```

必要に応じて `.env` の `VITE_API_BASE_URL` を変更してください。

```env
VITE_API_BASE_URL=http://localhost:18000
```

## 開発サーバーの起動

```powershell
npm run dev
```

デフォルトでは `http://localhost:5173` で起動します。

バックエンド API を別の URL で起動している場合は、`.env` の `VITE_API_BASE_URL` をその URL に合わせてください。

## ビルド

```powershell
npm run build
```

TypeScript のビルドチェック後、Vite が本番用ファイルを `dist/` に出力します。

## ビルド結果の確認

```powershell
npm run preview
```

`dist/` の内容をローカルでプレビューできます。事前に `npm run build` を実行してください。

## Lint

```powershell
npm run lint
```

ESLint でソースコードを検査します。
