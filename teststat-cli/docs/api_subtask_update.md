# 外部ツール連携仕様書：サブタスク進捗更新

本ドキュメントは、外部のCLIツール等からWBS管理ツールのサブタスク進捗率を更新するためのAPI仕様および連携手順について記述します。

## 1. 概要
テスト結果集計ツールなどの外部システムから、特定のサブタスクの進捗率（`progress_percent`）を自動更新することを目的とします。

## 2. API仕様

### サブタスク更新エンドポイント
サブタスクの情報を更新するには、以下のエンドポイントに対して `PATCH` リクエストを送信します。

- **URL**: `http://<server-address>:<port>/api/subtasks/{subtask_id}`
- **Method**: `PATCH`
- **Content-Type**: `application/json`

#### パスパラメータ
| パラメータ名 | 型 | 説明 |
| :--- | :--- | :--- |
| `subtask_id` | `integer` | 更新対象のサブタスクID |

#### リクエストボディ (JSON)
更新したいフィールドのみを含めて送信してください。

| フィールド名 | 型 | 説明 |
| :--- | :--- | :--- |
| `progress_percent` | `integer` | 進捗率 (0〜100) |
| `status_id` | `integer` | (任意) ステータスID。進捗が100%になった際に「完了」に変更する場合などに指定します。 |
| `actual_start_date` | `string (date)` | (任意) 実績開始日 (YYYY-MM-DD) |
| `actual_end_date` | `string (date)` | (任意) 実績終了日 (YYYY-MM-DD) |
| `memo` | `string` | (任意) 更新理由やテスト結果のサマリーなどを追記する場合に使用します。 |

**例: 進捗率を100%にし、ステータスを「完了」にする場合**
```json
{
  "progress_percent": 100,
  "status_id": 4,
  "memo": "Test tool update: All tests passed."
}
```
※デフォルト設定では `status_id: 4` が「完了」に対応します。

## 3. 連携手順とデータマッピング

外部ツールから特定のサブタスクを特定し、更新するまでの推奨フローは以下の通りです。

### ステップ1: マッピング情報の取得
外部ツール側で保持している識別子（例: チケットID）に対応する `subtask_id` を取得します。

- **Endpoint**: `GET /api/wbs`
- **処理**: レスポンスの `projects` -> `tasks` -> `subtasks` を走査し、`ticket_id` が一致するサブタスクの `id` を取得します。
- **注意**: `ticket_id` が重複している可能性がある運用の場合、親タスク名やプロジェクト名での絞り込みも検討してください。

### ステップ2: 進捗更新の実行
特定した `subtask_id` に対して `PATCH` リクエストを送信します。

## 4. システム仕様と注意点（引き継ぎ情報）

### 自動計算・波及効果
- **上位階層への波及**: サブタスクの進捗率やステータスが更新されると、親タスクおよび親プロジェクトの進捗率・ステータス・日付が自動的に再計算されます。
- **実績終了日の自動設定**: 
  - ステータスを「進行中」(2) または「レビュー中」(3) にした状態では、WBS表示時に `actual_end_date` が自動的に当日の日付に更新され続けます（バーが今日まで伸びる挙動）。
  - ステータスを「完了」(4等) にすると、その時点の `actual_end_date` で固定されます。
- **実績開始日の自動設定**: 実績開始日が未設定の状態で進捗を更新（またはステータスを進行中に変更）すると、自動的に当日の日付がセットされます。

### データ整合性
- **論理削除**: `is_deleted: true` のデータは通常フロントエンドには表示されません。外部ツールからも更新を避けるようにしてください（`GET /api/wbs` の結果にはデフォルトで含まれません）。
- **ステータスID**: ステータスIDは環境によって異なる可能性があるため、決め打ちせずに `GET /api/initial-data` から「完了」に相当するIDを動的に取得するか、設定ファイルで管理できるようにすることを推奨します。

## 5. 連携例 (PowerShell)

```powershell
# 1. 完了ステータスIDの取得（例として 4 を使用）
$doneStatusId = 4
$subtaskId = 123
$baseUrl = "http://localhost:8000/api"

# 2. 更新内容の構築
$payload = @{
    progress_percent = 100
    status_id = $doneStatusId
    memo = "Updated by TestStats CLI at $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
} | ConvertTo-Json

# 3. API実行
Invoke-RestMethod -Uri "$baseUrl/subtasks/$subtaskId" -Method Patch -Body $payload -ContentType "application/json"
```
