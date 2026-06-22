# TestStat フロントエンド URL ルーティング導入計画

> 対象ディレクトリ: `teststat-frontend/`
> 作成日: 2026-06-22
> 目的: 各画面を URL でルーティングし、`http://<host>/tstat/<testing id>` のように
> プロジェクトを直接開けるようにする（ディープリンク / ブラウザ戻る・進む / ブックマーク対応）。

---

## 0. 背景と現状

### 0.1 現在の画面遷移の仕組み（状態駆動 SPA）

現状はルーターを持たず、`App.tsx`（`AppContent`）の React state だけで画面を切り替えている。

| state | 型 | 役割 |
|-------|----|----|
| `selectedTestingId` | `number \| null` | 表示対象プロジェクトの `testing_id`（チケットID） |
| `viewMode` | `'overview' \| 'new' \| 'edit' \| 'plans' \| 'settings'` | 表示中の画面 |

- 選択中プロジェクトは `utils/uiStateStorage.ts`（`localStorage` キー `teststat:ui-state:v1`）に永続化。
  リロードしても直前のプロジェクトが復元される。
- 画面遷移は `Sidebar` / `ProjectOverview` などのコールバック（`onSelect` / `onEdit` / `onPlans` / `onCreate` / `onSettings` / `onBack`）が
  `setViewMode` / `setSelectedTestingId` を呼ぶことで成立。
- 未保存編集がある場合、遷移前に `runAfterDiscardConfirmation`（`ConfirmDialog`）で破棄確認を行う。
- `beforeunload` でタブ閉じ・リロード時にも警告。

### 0.2 現状の課題

- URL が常に `/tstat/`（ベースパス）のままで、**特定プロジェクトや画面を URL で共有・ブックマークできない**。
- ブラウザの**戻る／進むが画面遷移と連動しない**。
- 外部システム（チケット管理など）から `testing_id` 指定で直接開く導線が作れない。

### 0.3 公開構成（重要な前提）

- 開発: Vite dev server `:5173`、`base = VITE_APP_BASE_PATH`（既定 `/tstat/`）。
- 本番: IIS で `http://<host>/tstat` 配下に静的配信。API は `/tstat/api/...` にプロキシ。
- 関連ファイル: `vite.config.ts`（`base: appBase`）、`.env` / `.env.example`（`VITE_APP_BASE_PATH=/tstat/`）。

---

## 1. ゴールとなる URL 設計

ベースパス（`/tstat`）配下を以下のようにルーティングする。`<testing id>` は整数のチケットID。

| URL（ベースパス込み） | 画面 | 対応する現 state |
|----------------------|------|----------------|
| `/tstat/` | ルート。直前選択（localStorage）または先頭プロジェクトへリダイレクト | — |
| `/tstat/<testing id>` | プロジェクト概要 | `viewMode='overview'`, `selectedTestingId=<id>` |
| `/tstat/<testing id>/edit` | プロジェクト編集 | `viewMode='edit'` |
| `/tstat/<testing id>/plans` | 計画編集 | `viewMode='plans'` |
| `/tstat/new` | プロジェクト新規作成 | `viewMode='new'` |
| `/tstat/settings` | 設定 | `viewMode='settings'` |
| 上記以外 / 不正な id | Not Found（ルートへ誘導） | — |

設計上のポイント:

- `testing_id` は整数なので、`new` / `settings` のような**文字列セグメントと衝突しない**。
  ルート定義順とパラメータの数値バリデーションで安全に切り分ける。
- `edit` / `plans` は概要画面のサブ階層として `:testingId` 配下にネストする。
- **ベースパス `/tstat` はルーターの責務外**。Vite の `base` と React Router の `basename` で吸収し、
  アプリ内の `path` 定義は `/`, `/:testingId`, `/:testingId/edit` … のように**ベースパス抜き**で書く。

---

## 2. 技術選定

### 2.1 推奨: `react-router-dom` v7 を導入

- React 19 対応。データルーター（`createBrowserRouter`）でネスト・loader・ナビゲーションブロックが揃う。
- `basename` にベースパスを渡せるため、`/tstat` 配下の運用と素直に噛み合う。
- 未保存変更ガードを `useBlocker` で実装でき、既存の `ConfirmDialog` と統合しやすい。

```bash
npm install react-router-dom
```

### 2.2 代替案（不採用）: History API での自前ルーター

`window.history.pushState` + `popstate` で最小実装も可能だが、ネスト・ブロッカー・型安全な
パラメータ取得を自前で抱えることになり、画面数が今後増えると割に合わない。**react-router を採用**する。

> 判断材料: 画面は 5 種類で増加見込みあり（バグ集計などの将来拡張）。標準ライブラリ採用が妥当。

---

## 3. 改修方針

### 3.1 ベースパスの一元管理

`basename` と Vite の `base` がずれると本番でリンクが壊れる。両者を `VITE_APP_BASE_PATH` から導出する。

- `vite.config.ts`: 既存の `base: appBase` を維持。
- ルーター側: `import.meta.env.BASE_URL`（Vite が `base` から自動で注入）を `basename` に渡す。
  末尾スラッシュを取り除いて使用（`/tstat/` → `/tstat`）。

```ts
// 例: 末尾スラッシュ除去
const basename = import.meta.env.BASE_URL.replace(/\/$/, '') || '/'
```

これにより `.env` の `VITE_APP_BASE_PATH` を変えるだけで Vite と Router の双方が追従する。

### 3.2 ルート構成（データルーター）

`main.tsx` で `RouterProvider` を用い、`App` をレイアウト（`<Outlet />` を持つ親）に再編する。

```
<App>(レイアウト: Sidebar + main + 破棄確認)
 ├─ index                 → "/"          : localStorage / 先頭プロジェクトへ redirect
 ├─ "new"                 → 新規作成
 ├─ "settings"            → 設定
 └─ ":testingId"          → 概要(ProjectOverview)
      ├─ "edit"           → 編集(ProjectEditor)
      └─ "plans"          → 計画(PlanEditor)
```

- `viewMode` state は廃止し、**表示画面はルート定義から決まる**ようにする。
- `selectedTestingId` は `useParams()` の `testingId` を数値化して導出（state から URL へ「正」を移す）。
- プロジェクト一覧・しきい値・API ステータスといった**全画面共通データ**は引き続き
  レイアウト（`App`）で取得し、`Outlet` の `context`（`useOutletContext`）または軽量な Context で子に配布する。

### 3.3 ナビゲーションの置き換え

各コールバックを `useNavigate()` ベースに置換する。リンクとして提供できる箇所は `<Link>` / `<NavLink>` を使う。

| 現コールバック | 置換後 |
|---------------|-------|
| `Sidebar onSelect(id)` | `navigate(\`/${id}\`)`（`NavLink` で選択状態も自動化） |
| `ProjectOverview onEdit` | `navigate(\`/${id}/edit\`)` |
| `ProjectOverview onPlans` | `navigate(\`/${id}/plans\`)` |
| `onCreate` | `navigate('/new')` |
| `onSettings` | `navigate('/settings')` |
| `onBack` / `onCancel` / `onSaved` | `navigate(\`/${id}\`)` など概要へ |
| `handleDeleted` | 削除後に `navigate('/')`（次の対象へ誘導） |

`Sidebar` の選択ハイライトは `selectedTestingId` プロップではなく `NavLink` の active 状態に寄せられる
（移行段階では現行プロップ併用でも可）。

### 3.4 ルート → 状態の解決とエッジケース

- `:testingId` が非数値、または読込済みプロジェクトに存在しない `testing_id` の場合:
  - 一覧ロード前 → ローディング表示。
  - ロード後も不在 → **Not Found 画面**を表示し、ルート（`/`）への導線を出す。
    （無言リダイレクトより誤り検知に有利。挙動はレビューで確定）
- `/`（index）アクセス時:
  - `getStoredSelectedTestingId()` が有効なら `/<id>` へ `redirect`。
  - 無ければ先頭プロジェクトの `/<id>` へ。
  - プロジェクトが 0 件なら空状態（新規作成導線）を表示。
- `localStorage`（`uiStateStorage`）の役割は「**URL 未指定時の既定遷移先**」に縮退。
  プロジェクト選択時は `setStoredSelectedTestingId` を引き続き更新し、次回 `/` 直アクセスを賢くする。

### 3.5 未保存変更ガードの移行（要注意）

現状 `runAfterDiscardConfirmation` が遷移を仲介しているが、URL 遷移（戻る/進む含む）でも
同じ確認を出す必要がある。react-router の **`useBlocker`** に集約する。

- `hasUnsavedChanges === true` の間だけ `useBlocker` を有効化。
- ブロック発火時に既存 `ConfirmDialog`（`useConfirmDialog`）で破棄確認 →
  OK なら `blocker.proceed()`、キャンセルなら `blocker.reset()`。
- `beforeunload` ハンドラ（タブ閉じ・リロード）は現状のまま残す。
- これにより、ボタン遷移・サイドバー遷移・**ブラウザ戻る/進む**すべてで一貫した破棄確認になる。

### 3.6 本番（IIS）でのディープリンク対応（必須）

`pushState` ベース（BrowserRouter）では、`/tstat/123/edit` を**直接リロード**すると
IIS が物理ファイルを探して 404 になる。SPA フォールバックが必須。

- IIS: URL Rewrite で `/tstat/*` の未マッチを `/tstat/index.html` に rewrite するルールを追加。
- 代替: `index.html` を 404 ドキュメントに割り当てる方式でも可。
- Vite dev server は `base` 配下を自動でフォールバックするため開発時は追加対応不要。
- （リスク回避を最優先するなら `HashRouter` で `/tstat/#/123` 形式も可能だが、
  URL 体裁が要件の `/tstat/<id>` と異なるため**非推奨**。BrowserRouter + IIS Rewrite を本線とする。）

---

## 4. 影響ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `package.json` | `react-router-dom` 追加 |
| `src/main.tsx` | `RouterProvider` + ルート定義（`basename` 設定） |
| `src/App.tsx` | レイアウト化（`<Outlet />`）。`viewMode` 廃止、共通データ供給に専念 |
| `src/router.tsx`（新規） | ルートツリー定義（`createBrowserRouter`） |
| `src/routes/*`（新規 or 既存ラップ） | 各画面を route 要素化（概要/編集/計画/新規/設定/NotFound） |
| `src/components/Sidebar.tsx` | `onSelect` → `NavLink`/`navigate` ベースへ |
| `src/components/ProjectOverview.tsx` | `onEdit`/`onPlans` → `navigate` |
| `src/components/ProjectEditor.tsx` | `onCancel`/`onSaved`/`onDeleted` → `navigate` |
| `src/components/PlanEditor.tsx` | `onBack` → `navigate` |
| `src/types/ui.ts` | `ViewMode` を削除（または当面 deprecated 化） |
| `src/utils/uiStateStorage.ts` | 役割を「既定遷移先の記憶」に縮退（API は維持） |
| `src/hooks/useUnsavedChangesBlocker.ts`（新規） | `useBlocker` + `ConfirmDialog` 統合フック |
| `.env` / `.env.example` | 既存の `VITE_APP_BASE_PATH` をそのまま流用（追記不要の見込み） |
| IIS 配信設定 / `web.config` | URL Rewrite による SPA フォールバック追加 |

---

## 5. 実装フェーズ

1. **準備**: `react-router-dom` 導入。`basename` 導出ユーティリティ（`BASE_URL` 末尾スラッシュ処理）。
2. **骨組み**: `App` をレイアウト化し `RouterProvider` 化。まず `/:testingId` と `/`（リダイレクト）だけ通す。
3. **画面のルート化**: `new` / `settings` / `:testingId/edit` / `:testingId/plans` を順次移植。`viewMode` を撤去。
4. **ナビゲーション置換**: 各コールバックを `navigate`/`Link` 化。Sidebar の active 表示を `NavLink` に。
5. **未保存ガード移行**: `useBlocker` フックへ集約し、`runAfterDiscardConfirmation` の役割を移す。
6. **エッジケース**: 不正 `testingId` の Not Found、0 件時の空状態、削除後遷移。
7. **本番フォールバック**: IIS URL Rewrite（または `web.config`）を整備し、ディープリンク直アクセスを検証。
8. **クリーンアップ**: 不要 state / 旧プロップの削除、`ViewMode` 型整理。

---

## 6. 動作確認チェックリスト

- [ ] `/tstat/<既存id>` 直アクセスで概要が開く。
- [ ] `/tstat/<既存id>/edit`・`/plans` 直アクセスで該当画面が開く。
- [ ] `/tstat/new`・`/tstat/settings` が開く。
- [ ] `/tstat/`（id なし）で直前選択 or 先頭プロジェクトへ遷移。
- [ ] 存在しない id / 非数値で Not Found が表示される。
- [ ] サイドバー選択・概要からの編集/計画遷移で URL が変わる。
- [ ] ブラウザ戻る/進むで画面が連動する。
- [ ] 未保存編集中の遷移（ボタン・サイドバー・戻る/進む）すべてで破棄確認が出る。
- [ ] 未保存編集中のリロード/タブ閉じで `beforeunload` 警告が出る。
- [ ] 本番（IIS, `/tstat` 配下）でディープリンクをリロードしても 404 にならない。
- [ ] `VITE_APP_BASE_PATH` を変更しても Vite `base` と Router `basename` が追従する。

---

## 7. リスクと留意点

- **basename と base の不一致**は本番リンク崩壊に直結。`BASE_URL` 一本化で吸収する（§3.1）。
- **IIS の SPA フォールバック未整備**だとディープリンク直アクセスが 404。デプロイ手順に必須項目として明記（§3.6）。
- **未保存ガードの抜け**（戻る/進むで確認が出ない）は移行時の典型バグ。`useBlocker` への完全移行で塞ぐ（§3.5）。
- localStorage と URL の二重ソース化を避け、**URL を唯一の正**とし localStorage は既定値専用に縮退する（§3.4）。
- React Router v7 / React 19 の StrictMode 二重実行下での `redirect`・loader 挙動は早期に確認する。
