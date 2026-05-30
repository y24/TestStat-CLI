# TestStat フロントエンド開発計画

> 対象ディレクトリ: `teststat-frontend/`
> 作成日: 2026-05-31 / 改訂: 2026-05-31（計画・プロジェクト管理をスコープに追加）

---

## 0. この文書の位置づけと、今回の重要な前提

本計画は、AIとの壁打ちメモ（PB図ダッシュボード構想）を出発点に、
**既存の `teststat-server`（FastAPI）と `teststat-cli` の実装を「正」として再構成したもの**である。

### 0.1 今回（改訂）で確定した方針

ユーザーとの合意により、以下を**本プロジェクトのスコープに含める**:

1. **計画（テスト計画・テスト期間・日別消化計画）は、CLI ではなくこのプロジェクトで新規に導入する第一級概念である。**
   - CLI はあくまで**実績値を送信するのみ**で、計画やテスト予定期間を入力する手段を持たない。
   - したがって計画データを保持する**バックエンドのテーブル・API を新設する**（フロント開発とセットで進める）。
2. **実績は洗い替え（常に最新1件）だが、計画は複数バージョンを保持する。**
   - これにより「過去の計画を薄く重ねて表示」も実現可能になる（履歴が残るため）。
3. **プロジェクトはフロントエンドから新規作成する。** 作成時に `testing_id` を入力させ、合致する実績データを紐付ける。
   - `testing_id` は**外部のチケット管理システムのチケットID**（整数）。プロジェクトの実体キーとして用いる。

### 0.2 引き続きスコープ外（バグ関連）

バグ実績・バグ予測・品質リスク判定などは、**データの出どころ（チケット連携等）が未整備**のため初期版では対象外とする（§10）。

---

## 1. 現行バックエンド／CLI の実仕様（正・変更不可の前提）

新設する計画機能は、以下の**実在する実績データ**に重ね合わせる形で動く。

### 1.1 データ階層（実際の構造）

```
testings（testing_id ごとに 1 レコード, project_name を持つ）   ← CLI が UPSERT
  └─ file_progress        … ファイル(label/environment)単位のサマリ
  └─ daily_progress       … ファイル×日付ごとの実施数（completed・executed・planned・結果種別内訳）
  └─ daily_person_progress … ファイル×日付×担当者ごとの実施数
```

- 実績データは CLI (`tstat -l list.yaml`) が POST し、`testing_id` 単位で**洗い替え（全削除→全挿入）**される。
  サーバが保持する実績は常に**最新スナップショット 1 件**。
- `daily_progress.planned`（計画数）は Excel の「計画」列由来の値だが、**本プロジェクトの計画機能の出どころにはしない**（§1.4）。

### 1.2 主要メトリクスの定義（`config.json` 由来）

| 用語 | キー | 定義 |
|------|------|------|
| 全件数 | `total_cases` | シート上の全テスト項目数 |
| 対象件数 | `available_cases` | 全件数 − 除外件数（**実績バーンダウンの母数**） |
| 除外件数 | `excluded_cases` | 「対象外」「準備」等で除外 |
| 消化数 | `executed` | 何らかの結果が入った件数（Pass/Fixed/Fail/Blocked/Suspend/N/A） |
| 完了数 | `completed` | 完了扱いの結果（Pass/Fixed/Suspend/N/A。Fail・Blocked を除く） |
| 未着手 | `not_run` | 結果未入力の件数 |
| 計画数 | `planned`(CLI) | Excel 計画列由来の日別値。**本機能では未使用**（§1.4） |

`daily_progress` の `completed`/`executed` は**その日の増分**（累計ではない）。累計はフロント／サーバ側で積み上げる。

### 1.3 既存 API（実在するエンドポイント）

ベース URL: `/api/v1`（本番では IIS リバースプロキシ配下で `/tstat/api/v1` になりうる。§8.3）

| メソッド | パス | 用途 |
|---------|------|------|
| `GET` | `/testings` | CLI が登録した testing 一覧 |
| `GET` | `/progress/{testing_id}` | 実績サマリ（合算値・結果内訳・`updated_at`） |
| `GET` | `/progress/{testing_id}/files` | ファイル(label)別サマリ一覧 |
| `GET` | `/progress/{testing_id}/daily` | 日別実績明細（date×label の completed/executed/planned/結果種別） |
| `GET` | `/health` | ヘルスチェック |

### 1.4 現行仕様との整合で注意する点（設計に反映済み）

- **CLI の `daily.planned` 列は計画の出どころにしない。** ユーザー方針どおり、計画は本プロジェクトで新設する計画テーブル（§4）を正とする。CLI の `planned` は将来も参考値として残ってよいが、PB図の計画線には使わない。
- **CLI の POST は `testings.project_name` を毎回上書きする**（`_get_or_create_testing`）。よってフロントの「プロジェクト表示名」は **CLI に上書きされない別テーブル（`projects`, §4）で管理**する。`testings` は実績側のレジストリとして扱う。
- **実績レンジ指定の API パラメータは無い**。期間は計画の `start_date`〜`end_date` と実績日付の和から決める。

---

## 2. 設計の基本方針（このプロジェクトで新規に作るもの）

### 2.1 概念の対応と粒度

| 概念 | 実体 | キー | 所有者 |
|------|------|------|--------|
| プロジェクト | チケット1件に対応するテスト全体 | `testing_id`（チケットID, 整数） | **フロント新設（`projects`）** |
| テスト | プロジェクト内の個別テスト（種別） | `label`（実績の file_progress.label に対応） | **フロント新設（`plans` の単位）** |
| 計画バージョン | テストごとの計画（期間・項目数・日別配分） | version | **フロント新設（`plans`/`plan_daily`）** |
| 実績 | CLI が送る消化・完了・結果 | `testing_id`＋`label`＋`date` | CLI（既存テーブル） |

- **プロジェクト ↔ `testing_id` は 1:1。** 根拠: 実際の CLI 運用（`list_sample.yaml`）では 1 つの `testing_id` の下に複数ファイル（`label` = TEST001/002/003）がぶら下がる。
  → 「プロジェクト=チケット=testing_id、テスト=label」とする。
  （※ もし将来「1プロジェクトが複数チケット(testing_id)にまたがる」運用が必要になれば §10 の拡張で対応。今回は 1:1。）
- **計画はテスト（label）単位**で作成し、**プロジェクト表示時は各テストの有効計画を合算**する（壁打ちメモ §9 の構造を採用）。

### 2.2 実績は1件・計画は多バージョン

```
projects（testing_id 1件）
  └─ plans（テスト=label ごとに複数バージョン。is_active が現行）
       └─ plan_daily（日別の計画消化数）
  └─（実績は既存 testings/daily_progress を testing_id で参照）
```

- 計画はバージョンを**上書きせず追加**。`is_active` が現在有効な版。過去版は保持し、PB図に薄く重ねて表示できる。

---

## 3. 壁打ち案と現行仕様の対応表（改訂後）

| 壁打ち案の要素 | 判定 | 対応方針 |
|----------------|------|----------|
| 左にプロジェクト一覧、右に大きな PB図（2ペイン） | ✅ 採用 | 左ナビは**フロント新設 `GET /projects`**（実績未受信でも表示可）。 |
| 全テスト / 単一テスト切替 | ✅ 採用 | テスト=`label`。計画も実績も label で絞り込み／合算。 |
| 計画線・実績線・日別計画棒・日別実績棒の重ね描画 | ✅ 採用 | 計画は新設計画テーブル、実績は既存 `/daily`。§6。 |
| 日別棒は重ね描画（横並びにしない）・今日線 | ✅ 採用 | ECharts で実装。 |
| レイヤー ON/OFF（計画/実績/日別/過去計画） | ✅ 採用 | バグのみ初期対象外。**過去計画の重ねは採用可能に**（多バージョン保持のため）。 |
| **過去の計画を薄く重ねて表示** | ✅ **採用**（前回の❌を撤回） | 計画をバージョン管理するため履歴が残る。非有効版を薄線で重ねられる。 |
| **計画編集画面（バージョン・期間・項目数・均等配分/日別入力/CSV）** | ✅ **採用**（要バックエンド新設） | §4・§5・§7。計画は本プロジェクトで新規実装する第一級概念。 |
| **プロジェクト編集画面（新規作成・編集）** | ✅ **採用**（要バックエンド新設） | 作成時に `testing_id`(チケットID)を入力。実績は testing_id で紐付け。 |
| バグ実績エリア・右軸 | ❌ 初期対象外 | バグの保持先・連携が未整備（§10）。 |
| バグ予測 / `bug_forecasts` | ❌ 初期対象外 | 同上。空欄・無効破線も出さない。 |
| `project_id` をキーにした URL/API | 🔧 読み替え | キーは整数 `testing_id`。 |
| `GET /.../pb-chart` 専用 API | ✅ 採用（新設） | **計画と実績の両方をサーバが持つため、サーバ側で統合系列を返す API を新設**（§5・§6.4）。 |

凡例: ✅ 採用 / 🔧 読み替え / ❌ 初期対象外

---

## 4. バックエンド拡張：新規データモデル

> 既存の CLI 所有テーブル（`testings`/`file_progress`/`daily_progress`/`daily_person_progress`）は**変更しない**。
> 以下を**追加**する（Alembic で新規マイグレーション）。

### 4.1 `projects`（フロント所有のプロジェクト）

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | SERIAL PK | |
| `testing_id` | INTEGER UNIQUE NOT NULL | チケットID。実績(testings/daily_progress)との結合キー |
| `name` | VARCHAR(255) | 表示名（フロント所有。CLI の project_name に上書きされない） |
| `ticket_ref` | VARCHAR(255) NULL | 任意：チケットのキーや URL |
| `archived` | BOOLEAN default false | 完了プロジェクトの折りたたみ用 |
| `created_at` / `updated_at` | TIMESTAMP | |

- 実績(testings)が未受信でもプロジェクトを作成できる（事前登録）。実績到着後に testing_id で自動マッチ。

### 4.2 `plans`（テスト=label ごとの計画バージョン）

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | SERIAL PK | |
| `testing_id` | INTEGER NOT NULL | `projects.testing_id` を参照 |
| `label` | VARCHAR(255) NULL | テスト(label)。NULL はプロジェクト全体を1テストとして計画する場合 |
| `version` | INTEGER NOT NULL | testing_id+label 内の連番 |
| `is_active` | BOOLEAN NOT NULL | 有効な計画（testing_id+label で 1 件のみ true） |
| `reason` | VARCHAR(500) NULL | 変更理由（例：仕様追加により120件増加） |
| `planned_total_cases` | INTEGER NOT NULL | 計画テスト項目数 |
| `start_date` | DATE NOT NULL | 計画開始日 |
| `end_date` | DATE NOT NULL | 計画終了日 |
| `created_at` | TIMESTAMP | |
| `created_by` | VARCHAR(255) NULL | 作成者（任意） |

### 4.3 `plan_daily`（日別の計画消化数）

| カラム | 型 | 説明 |
|--------|-----|------|
| `id` | SERIAL PK | |
| `plan_id` | INTEGER NOT NULL FK→plans.id (ON DELETE CASCADE) | |
| `date` | DATE NOT NULL | |
| `planned_count` | INTEGER NOT NULL | その日の計画消化数 |

- 入力方法（均等配分 / 日別入力 / CSVインポート）は、いずれも**最終的に `plan_daily` の行群を生成するだけ**。サーバは生成済みの日別値を受け取る。
- 制約: `Σ plan_daily.planned_count ≤ planned_total_cases` を推奨（超過は警告）。`date` は `start_date`〜`end_date` 内。

### 4.4 計画線の算出根拠
- 計画未実施[d] = `planned_total_cases` − Σ_{d'≤d} `planned_count`
- テスト(label)単位の計画を、プロジェクト表示時は有効版を合算。

---

## 5. バックエンド拡張：新規 API

> プレフィックスは既存に合わせ `/api/v1`。認証なし（LAN前提）。

### 5.1 プロジェクト

| メソッド | パス | 用途 |
|---------|------|------|
| `GET` | `/projects` | プロジェクト一覧（実績の有無・更新日時も付与） |
| `POST` | `/projects` | 新規作成 `{testing_id, name, ticket_ref?}` |
| `PATCH` | `/projects/{testing_id}` | 表示名・archived の更新 |
| `DELETE` | `/projects/{testing_id}` | 削除（計画も連鎖削除。実績テーブルは触らない） |

`GET /projects` レスポンス例:
```json
[
  { "testing_id": 1001, "name": "サンプルプロジェクト", "archived": false,
    "has_actuals": true, "actuals_updated_at": "2026-05-20T18:42:00", "active_plan_count": 3 }
]
```

### 5.2 計画

| メソッド | パス | 用途 |
|---------|------|------|
| `GET` | `/projects/{testing_id}/plans` | 計画一覧（テスト(label)別・全バージョン） |
| `POST` | `/projects/{testing_id}/plans` | 新バージョン作成（下記ボディ） |
| `GET` | `/plans/{plan_id}` | 計画詳細（plan_daily 含む） |
| `POST` | `/plans/{plan_id}/activate` | 当該テストの有効版に切替 |
| `DELETE` | `/plans/{plan_id}` | バージョン削除 |

`POST /projects/{testing_id}/plans` ボディ例:
```json
{
  "label": "TEST001",
  "reason": "仕様追加により120件増加",
  "planned_total_cases": 920,
  "start_date": "2026-05-01",
  "end_date": "2026-06-10",
  "activate": true,
  "daily": [
    { "date": "2026-05-01", "planned_count": 60 },
    { "date": "2026-05-02", "planned_count": 60 }
  ]
}
```
- `version` はサーバが採番。`activate:true` なら同 (testing_id,label) の既存有効版を false にして当版を true に。

### 5.3 PB図統合系列（新設・推奨データ源）

計画（新テーブル）と実績（既存テーブル）の**両方をサーバが持つ**ため、描画系列の統合はサーバ側で行うのが素直。

| メソッド | パス | クエリ |
|---------|------|--------|
| `GET` | `/projects/{testing_id}/pb-chart` | `label`（任意。未指定=全テスト合算）, `include_past_plans`（任意 bool） |

レスポンス例（壁打ちメモ §13 の形に準拠。ただしキーは `testing_id`、バグは含めない）:
```json
{
  "testing_id": 1001,
  "label": null,
  "range": { "from": "2026-05-01", "to": "2026-06-12" },
  "actuals_updated_at": "2026-05-20T18:42:00",
  "available_cases": 800,
  "planned_total_cases": 920,
  "series": [
    {
      "date": "2026-05-02",
      "planned_remaining": 860,
      "actual_remaining": 765,
      "planned_completed_daily": 60,
      "actual_completed_daily": 35
    }
  ],
  "past_plans": [
    { "version": 1, "series": [ { "date": "2026-05-02", "planned_remaining": 880 } ] }
  ]
}
```
- `actual_remaining` = `available_cases` − 累計 `executed`（実績の母数で算出）。
- `planned_remaining` = `planned_total_cases` − 累計 `planned_count`（計画の母数で算出）。
- 実績未受信なら `actual_*` は欠落（計画のみ描画）。計画未作成なら `planned_*` は欠落。

> 初期実装の負担を抑えるなら、`pb-chart` を作らず**フロントで `/plans` と `/daily` を合成**する選択肢もある（§9 未確定事項）。本計画は**サーバ統合方式を推奨**する（クライアントが軽く、両データの整合をサーバで取れるため）。

---

## 6. PB図の系列（描画仕様）

### 6.1 重ねる系列（初期版）
```
未実施件数:   計画線（破線, planned_remaining）・実績線（実線, actual_remaining）
日別消化件数: 計画棒（薄・背面, planned_completed_daily）・実績棒（濃・前面, actual_completed_daily）
過去計画:     非有効版の planned_remaining を薄い破線で重ね（トグルON時）
基準線:       今日（縦線）
```

### 6.2 軸
- 左軸（件数）に「未実施件数」と「日別消化件数」を共用（壁打ちメモ §7）。右軸はバグ実装時に追加（初期はなし）。
- 横軸（日付）は `range.from`〜`range.to`。`pb-chart` がレンジを返す。

### 6.3 完了 vs 消化
- 実績線は**消化（executed）ベース**を既定。計画も消化計画なので軸が揃う。完了（completed）ベースは任意の追加レイヤー。

### 6.4 欠損・異常系
- 計画未作成: 計画線・計画棒を出さない。実績のみ表示。
- 実績未受信: 実績線・実績棒を出さない。計画のみ表示。
- 日別実績が負: そのまま下方向に表示＋ツールチップ（壁打ちメモ §11 の方針）。

PB図イメージ: [pb_chart_mockup.html](pb_chart_mockup.html)

---

## 7. 画面構成（初期版は3画面）

### 7.1 PB図ダッシュボード（メイン）
```text
┌──────────────────┬───────────────────────────────────────────────┐
│ テスト状況         │ サンプルプロジェクト  (testing_id: 1001)        │
│ プロジェクト       │ 表示対象:[全テスト▼]   [計画を編集]            │
│ ● サンプルP       │ 表示期間: 2026/05/01 ～ 2026/06/12             │
│   認証基盤移行     │ 表示: ☑計画線 ☑実績線 ☑日別消化 ☐過去計画     │
│   帳票改修         │ ┌───────────── PB図 ─────────────┐           │
│   …               │ └─────────────────────────────────┘           │
│ [+ プロジェクト]  │ 最終更新: 2026/05/20 18:42                     │
└──────────────────┴───────────────────────────────────────────────┘
```
- 左ナビ=`GET /projects`（archived は折りたたみ）。`[+ プロジェクト]`→プロジェクト編集へ。
- `[計画を編集]`→計画編集へ。

### 7.2 プロジェクト編集画面
- 新規作成: `testing_id`（チケットID, 必須・整数）、表示名、チケット参照(任意)を入力 → `POST /projects`。
  - testing_id の重複は弾く。実績の有無は問わない（事前登録可）。
- 編集: 表示名・archived の変更。削除（計画も連鎖削除、実績は不変）。
- 補助: 入力した testing_id に実績があれば「実績受信済み（最終更新 …）」、無ければ「実績未受信」を表示。

### 7.3 計画編集画面
壁打ちメモ §10 に準拠。画面イメージ: [plan_edit_mockup.html](plan_edit_mockup.html)
```text
サンプルプロジェクト > テスト計画
┌──────────────┬──────┬───────────────┬──────────┬────────┐
│ テスト(label) │ 項目数 │ 期間          │ 有効な計画 │ 操作    │
├──────────────┼──────┼───────────────┼──────────┼────────┤
│ TEST001      │  920 │ 05/01 - 06/10 │ v2       │[編集][履歴]│
│ TEST002      │ 1200 │ 05/08 - 06/12 │ v1       │[編集][履歴]│
└──────────────┴──────┴───────────────┴──────────┴────────┘
```
- テスト(label) は、実績がある場合 `/files` の label から候補提示。無ければ手入力（実績到着時に label 一致で紐付くため、表記を合わせる旨を注意表示）。
- 新バージョン作成フォーム: 変更理由・テスト項目数・開始日・終了日・入力方法。
  - **均等配分**: 期間と項目数から日別を自動生成（営業日考慮は将来）。
  - **日別入力**: 日付ごとに手入力（テーブル）。
  - **CSVインポート**: `date,planned_count` を取り込み。
  - いずれも `daily[]` を組み立てて `POST /projects/{testing_id}/plans` 送信。
- 履歴: バージョン一覧、`activate` で有効版切替、削除。

---

## 8. 技術スタックと構成

### 8.1 推奨スタック
| 項目 | 推奨 | 理由 |
|------|------|------|
| ビルド/開発 | Vite | 軽量・高速 |
| フレームワーク | React + TypeScript | レスポンス契約を型で固定 |
| チャート | Apache ECharts | 線＋棒の重ね、複数Y軸（将来バグ）、`markLine`（今日線）、`dataZoom` を標準サポート |
| フォーム/状態 | React Hook Form + 軽量状態管理 | 計画編集の日別入力・CSV取込に対応 |
| HTTP | fetch ラッパ | 認証なし・少数エンドポイント |

### 8.2 ディレクトリ構成（案）
```
teststat-frontend/
├── docs/  (development_plan.md / pb_chart_mockup.html / plan_edit_mockup.html)
├── index.html / package.json / vite.config.ts / .env.example
└── src/
    ├── api/        (client.ts, types.ts)
    ├── features/
    │   ├── projects/   (一覧・作成・編集)
    │   ├── plans/      (計画編集・バージョン・CSV)
    │   └── pbchart/    (pb-chart 取得・ECharts オプション)
    ├── components/
    └── App.tsx
```

### 8.3 API ベース URL・配信
- 開発: `VITE_API_BASE_URL=http://localhost:18000`。本番は IIS 配下で `/tstat/api/v1`。**環境変数で切替**しハードコードしない。
- 同一オリジン配信（ビルド成果物を `/tstat` 配下に置く）にすれば CORS 回避。別オリジンならサーバ側 CORS 設定が必要。

---

## 9. 開発フェーズ

> バックエンド拡張（§4・§5）とフロントを並行。バックエンドは別リポジトリ `teststat-server` 側で実装。

| Phase | 内容 | 完了条件 |
|-------|------|----------|
| 0. 足場 | Vite+React+TS、`api/client.ts`/`types.ts`、`.env`、`/health` 疎通 | 空画面が API に到達 |
| B1. BE:プロジェクト | `projects` テーブル＋ Alembic、`/projects` CRUD | 作成/一覧/編集/削除が動く |
| B2. BE:計画 | `plans`/`plan_daily`＋ `/plans` 系 API（採番・activate・CASCADE） | バージョン作成・有効版切替が動く |
| B3. BE:統合系列 | `/projects/{id}/pb-chart`（計画×実績の合成・過去計画） | 期待 JSON を返す |
| F1. 左ナビ＋プロジェクト編集 | `/projects` 一覧・作成・編集画面 | testing_id 入力で作成・選択できる |
| F2. PB図 | `/pb-chart` 取得→ ECharts 描画（計画線/実績線/日別棒/今日線） | モックと同等の見た目 |
| F3. 計画編集 | テスト一覧・新版作成（均等/日別/CSV）・履歴・activate | 計画作成が PB図に反映 |
| F4. 仕上げ | 全テスト/label 切替、過去計画トグル、欠損・負値・実績未受信の表示、ローディング/エラー | 異常系も破綻しない |

---

## 10. 将来拡張（引き続きスコープ外）

- **バグ実績（積み上げエリア・右軸）**: 保持テーブル＋チケット連携 or CLI 送信が前提。整い次第、右軸を追加。
- **バグ予測（forecast）**: バグ実績の履歴蓄積後。`forecast_*` がある時だけ予測線を描く。
- **品質リスク判定・アラート・レポート出力**。
- **1プロジェクトが複数 testing_id（チケット）にまたがる構成**: 今回は 1:1。必要になれば projects に複数 testing_id を束ねる中間テーブルで拡張。
- **均等配分の営業日（休日除外）考慮**。

---

## 11. 未確定事項（要確認・デフォルト判断あり）

1. **フレームワーク**: React+TS を推奨（Vue 希望なら差し替え）。
2. **テスト(label)単位 vs プロジェクト単位の計画**: 本計画は**テスト(label)単位**で設計（壁打ちメモ §9）。
   1プロジェクト＝1テストで運用するなら、label を1つ（または NULL=全体）にするだけで成立。
3. **PB図系列の合成場所**: **サーバ `pb-chart` 推奨**。フロント合成（`/plans`＋`/daily`）にする場合はこの API を作らない。
4. **計画の母数と実績の母数の差**: 計画線は `planned_total_cases`、実績線は実績 `available_cases` を基準にする（乖離自体が情報）。共通母数に揃えたい要望があれば調整。
5. **配信方式**: 同一オリジン（IIS `/tstat` 配下）配信で CORS 回避を既定とする。
6. **テスト(label)の表記揺れ対策**: 計画の label と実績の label は文字列一致で紐付く。実績がある場合は候補から選ばせ、手入力時は注意喚起する。
```
