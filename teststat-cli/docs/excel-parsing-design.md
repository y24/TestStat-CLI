# Excel 解析ロジック設計ドキュメント

TestStat-CLI が Excel（`.xlsx`）のテスト項目表を読み取り、日別・担当者別・環境別の進捗を集計するまでの内部設計をまとめる。あわせて、この挙動を制御する `config.json` の全設定値を解説する。

- 対象読者: 本ツールの解析ロジックを把握・改修したい開発者
- 関連コード: `utils/ReadData.py` / `utils/ExcelProcessor.py` / `utils/DataAggregator.py` / `utils/OpenpyxlWrapper.py` / `utils/Utility.py`
- 関連ドキュメント: [`README.md`](../README.md)（利用者向けの使い方・設定リファレンス）

---

## 1. 全体像

解析は「ファイル → シート → 結果列セット（環境）→ 行」という階層で進む。各層の責務は次のとおり。

```
aggregate_results (ReadData.py)               ← ファイル1件を処理
 ├─ ブックを開く / 対象シートを絞り込む         (OpenpyxlWrapper)
 ├─ シートごとに process_sheet (ExcelProcessor) ← シート1枚を処理
 │   ├─ ヘッダー行を検出
 │   ├─ 結果/担当者/日付/計画の列番号を特定
 │   ├─ 列を「セット（=環境）」に束ねる
 │   └─ セットごとに aggregate_daily_results   (DataAggregator) ← 日別集計
 └─ _aggregate_final_results                   ← 全シートを統合し統計を算出
```

処理の入口は `ReadData.aggregate_results(filepath, settings)` で、`settings` には `config.json` を読み込んだ辞書がそのまま渡る。リスト（YAML）で `target_sheets` や `target_environments` を指定した場合は、この `settings` の `read_definition` をファイル単位で上書きしたコピーが渡される（詳細は §6）。

---

## 2. 想定する Excel レイアウト

本ツールは「1 行 = 1 テストケース」「同一ケースを複数の環境（実行セット）でテストする」表を想定している。実際のサンプル（`input_sample/sample1.xlsx`）の構造は次のとおり。

| 行 | 役割 | 内容 |
| --- | --- | --- |
| 1 行目 | **セット名（環境名）行** | 各結果列セットの先頭列に環境名を記載（例: `環境a`、`環境b`）。改行は `_` に置換される |
| （任意の位置） | **ヘッダー行** | A 列に検出キー `#` を置いた行。各列の見出し（`期待結果`・`実施結果1`・`担当者1`・`日付1` …）を並べる |
| ヘッダー以降 | **データ行** | テストケースの実データ（結果・担当者・実施日など） |

ヘッダー行の位置は固定ではなく、A 列を上から走査して検出キー（既定 `#`）が最初に現れた行を採用する。サンプルではヘッダーは 10 行目にある。

### 結果列セットの考え方

同一環境の「結果・担当者・日付」の 3 列が 1 つの**セット**を構成する。ヘッダー例:

```
… 期待結果 … 実施結果1 担当者1 日付1 … 実施結果2 担当者2 実施日 …
```

- `結果` を含む列 → `[実施結果1, 実施結果2, …]`
- `担当者` を含む列 → `[担当者1, 担当者2, …]`
- `日付`/`実施日` を含む列 → `[日付1, 実施日, …]`

これらを列の出現順で zip（転置）して `[結果列, 担当者列, 日付列]` のセット群に束ねる。1 ファイルに複数環境ぶんのセットが並ぶ想定で、セット名（環境名）は「そのセットの結果列と同じ列の 1 行目セル」から取得する。

---

## 3. シート解析の詳細（`ExcelProcessor.process_sheet`）

### 3.1 ヘッダー行の検出

`OpenpyxlWrapper.find_row_index` で、`header.search_col`（既定 A 列）を上から走査し、セル値が `header.search_key`（既定 `#`）に**完全一致**する最初の行番号を返す。見つからなければ `header_not_found` エラーを返して打ち切る。

> 注意: 完全一致判定のため、`#` を含む長い文字列（例 `#No`）はヒットしない。検出キーはセル値そのものと一致させる必要がある。

### 3.2 列番号の特定

ヘッダー行の値リストに対し、`Utility.find_column_indices_by_keywords` で**部分一致**により列番号（1 始まり）を集める。

- `result_row.keys`（既定 `["結果"]`）で結果列を検索。ただし `result_row.ignores`（既定 `["期待結果"]`）に**完全一致**する見出しは除外。→ `期待結果` を結果列と誤認しないための除外。
- `person_row.keys`（既定 `["担当者"]`）→ 担当者列
- `date_row.keys`（既定 `["日付","実施日"]`）→ 日付列
- `plan_row.keys`（既定 `["計画"]`）→ 計画列（任意）
- `tobe_row.keys`（既定 `["期待","実施対象"]`）→ 期待結果/実施対象列（テストケース総数の数え上げに使用）

### 3.3 整合性チェック

- 結果・担当者・日付の 3 列は**同数**でなければならない（`inconsistent_result_set` エラー）。1 セット = 3 列 1 組が崩れていないことの保証。
- 計画列が存在する場合、結果列と計画列も同数でなければならない（`inconsistent_plan_set` エラー）。

### 3.4 セット単位の抽出と環境フィルタ

各セットについて次を行う。

1. **セット名の取得**: 結果列と同じ列の 1 行目セル値。空なら `セット{n}` を採番。改行は `_` に置換。
2. **環境フィルタ**（リスト由来の上書き設定）:
   - `target_environments` 指定時 … セット名にいずれのキーワードも**含まれない**セットはスキップ。
   - `ignore_environments` 指定時 … セット名にいずれかのキーワードを**含む**セットはスキップ。
   - いずれも部分一致。`config.json` には既定キーがなく、リスト（YAML）側でのみ与える運用。
3. **データ整形**: `[結果, 担当者, 日付]` を行ごとに取得。日付型セルは `YYYY-MM-DD` 文字列へ整形（`get_column_values_formatted`）。結果と日付があるのに担当者が空の行は担当者を `NO_NAME` で補完し、末尾にシート名を付与して `[結果, 担当者, 日付, シート名]` にする。
4. **日別集計**: セットごとに `DataAggregator.aggregate_daily_results` を呼び、環境別集計 `env_data[セット名]` に格納。

### 3.5 テストケース総数

`tobe_row`（期待結果/実施対象）列の非 None 行数をケース総数 `case_count` とする。取得できなければ `no_testcases` エラー。計画列があれば同様に計画総数 `plan_count` を数える。

### 3.6 シート解析の戻り値

```jsonc
{
  "data":              [[結果, 担当者, 日付, シート名], ...],  // 全セット分の生データ
  "plan_data":         [[計画日], ...],
  "env_data":          { "環境a": { "2025-02-15": {...}, ... }, ... },
  "sheet_name_mapping": { "環境a": "テスト項目1", ... },
  "counts": { "sheet_name": ..., "env_count": セット数, "all": ケース総数, "all_plan": 計画総数 }
}
```

---

## 4. 日別集計ロジック（`DataAggregator.aggregate_daily_results`）

行データを走査し、`result_count[日付][結果種別]` のカウンタを積み上げる。

- **計画列**（`plan_data`）がある行は、計画日をキーに `計画数` を +1。
- **日付の扱い**: 日付が空、または結果が「無効扱い結果」（`excluded` + `date_invalid_results`）に該当する行は、日付を `no_date` に倒す。カウント自体は維持されるが、日付軸には乗らない（バーンダウン等の日付系集計から外れる）。
- 各行の結果値について:
  - `results` に含まれれば、その結果種別を +1
  - `completed_results` に含まれれば `完了数` を +1
  - `executed_results` に含まれれば `消化数` を +1
- 戻り値は「日付ありデータ（昇順）」と「`no_date` データ」を分けて返す。

担当者別集計 `aggregate_daily_by_person` は、無効結果と日付なし行を除外したうえで `date_name_count[日付][担当者]` を集計する。

---

## 5. ファイル全体の統合と統計（`ReadData._aggregate_final_results`）

全シートの `data` / `plan_data` / `env_data` を連結し、次の統計 `stats` を算出する。

| 指標 | 算出方法 |
| --- | --- |
| `all` | ケース総数 × 環境数（シートごとの `env_count * all` の総和） |
| `excluded` | 結果が `excluded` に一致する行数 |
| `available` | `all - excluded`（有効ケース数） |
| `executed` | 日別合計の全結果カウント総和（= 消化数の実体） |
| `completed` | 完了系結果（`completed_results`）の合計 |
| `incompleted` | `max(0, available - executed)`（未実施） |
| `planned` | 計画日が入っている行数 |

さらに:

- **実施状況判定** `determine_run_status`:
  - `executed == 0` → 未着手
  - `completed == available` かつ `incompleted == 0` → 完了
  - `executed > 0` → 進行中
- **開始日 / 最終更新日**: 日別データの最小・最大キー（最終更新は完了/進行中のときのみ）。
- **完了率 / 消化率**: それぞれ `completed / available`、`executed / available` を百分率。
- **警告**: ケース総数が 0（`no_data`）、または消化数が有効ケース数を超過（`inconsistent_count`）の場合に付与。

複数ファイルを一括処理した場合は `merge_multiple_file_results` が各ファイルの `total`/`stats`/`daily` を合算し、全体の完了率・消化率を再計算する。

---

## 6. 設定値リファレンス（`config.json`）

`config.json` はツールと同じディレクトリに置く。存在しなければ `assets/default_config.json` を複製して自動生成される。`-c/--config` で任意パスを指定可能。全項目を網羅した見本は `config_sample.json`。

`read_definition`・`test_status`・`output_definition` は必須セクション（`FileScanner.validate_config` が検証）。

### 6.1 `read_definition` — Excel の読み取り方

| キー | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `target_sheets` | string[] | `["テスト項目"]` | 集計対象シートを検索するキーワード（部分一致）。空配列なら全シートが対象。 |
| `ignore_sheets` | string[] | `[]` | 除外シートのキーワード（部分一致）。`target_sheets` に一致してもこれを含むシートは除外。 |
| `include_hidden_sheets` | bool | `false` | `true` で Excel 上の非表示シートも対象に含める。 |
| `header.search_col` | string | `"A"` | ヘッダー行を探す列（列名）。 |
| `header.search_key` | string | `"#"` | ヘッダー行を特定するセル値。**完全一致**で判定。 |
| `tobe_row.keys` | string[] | `["期待","実施対象"]` | 期待結果/実施対象列の見出しキーワード（部分一致）。ケース総数の数え上げに使用。 |
| `result_row.keys` | string[] | `["結果"]` | 結果列の見出しキーワード（部分一致）。 |
| `result_row.ignores` | string[] | `["期待結果"]` | 結果列から除外する見出し（**完全一致**）。`期待結果` を結果と誤認しないため。 |
| `person_row.keys` | string[] | `["担当者"]` | 担当者列の見出しキーワード（部分一致）。 |
| `date_row.keys` | string[] | `["日付","実施日"]` | 実施日列の見出しキーワード（部分一致）。 |
| `plan_row.keys` | string[] | `["計画"]` | 計画（予定日）列の見出しキーワード（部分一致）。任意。 |
| `excluded` | string[] | `["対象外","準備"]` | この結果値の行は「対象外」として有効ケース数から除外し、日付を `no_date` に倒す。 |
| `date_invalid_results` | string[] | `[]` | カウントは残しつつ日付軸から外したい結果値。`excluded` と合わせて「無効扱い結果」を構成する。 |

> `target_environments` / `ignore_environments` は `config.json` には既定で置かず、リスト（YAML）のファイル単位設定として与える（§6.5）。指定するとセット名（環境名）に対する部分一致で対象/除外を絞り込む。

### 6.2 `test_status` — 結果種別の定義

| キー | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `results` | string[] | `["Pass","Fixed","Fail","Blocked","Suspend","N/A"]` | 集計対象の結果種別の**名称と表示順**。ここに無い結果値はどのカウントにも入らない。 |
| `completed_results` | string[] | `["Pass","Fixed","Suspend","N/A"]` | 「完了」とみなす結果種別。完了数・完了率の分子。 |
| `executed_results` | string[] | `["Pass","Fixed","Fail","Blocked","Suspend","N/A"]` | 「消化（着手済み）」とみなす結果種別。消化数・消化率の分子。 |
| `labels.completed` | string | `"完了数"` | 完了数の集計キー/表示ラベル。 |
| `labels.executed` | string | `"消化数"` | 消化数の集計キー/表示ラベル。 |
| `labels.planned` | string | `"計画数"` | 計画数の集計キー/表示ラベル。 |
| `labels.not_run` | string | `"未着手"` | 未着手の表示ラベル。 |

> `completed_results` と `executed_results` の差（例: `Fail`・`Blocked`）が「着手したが未完了」を意味する。完了/消化の定義を変えたいときはこの 2 配列を調整する。

### 6.3 `output_definition` — 出力・ステータス表示

| キー | 型 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `state.completed.name` | string | `"完了"` | 全ケース完了時のステータス表示名。 |
| `state.in_progress.name` | string | `"進行中"` | 一部着手時のステータス表示名。 |
| `state.not_started.name` | string | `"未着手"` | 未着手時のステータス表示名。 |
| `state.*.foreground` / `background` | string | （sample のみ） | ターミナル表示の文字色/背景色。`config_sample.json` に色名の例あり。`NO_COLOR` 環境変数で無効化可。 |
| `use_plan_row` | bool | `false` | `true` で日別内訳に計画列の情報を反映する。 |

### 6.4 外部連携セクション

| セクション | キー | 既定値 | 説明 |
| --- | --- | --- | --- |
| `reporting_api` | `enabled` | `true` | TestStat サーバー連携全体の有効/無効。`false` で `-t/--testing-id` によるリスト取得も含め無効化。 |
| | `send` | `true` | 進捗データ送信のみのスキップ。`enabled: true` のままダウンロード/集計は実行しつつ送信だけ止められる。 |
| | `base_url` | `http://localhost:18000/api` | TestStat サーバーの API ベース URL（末尾 `/api` まで）。 |
| | `sender` | `null` | 送信元識別子（任意）。 |
| `wbs_api` | `enabled` | `false` | WBS 管理ツール連携の有効/無効。 |
| | `base_url` | — | WBS ツールの API ベース URL。 |
| `sharepoint` | `enabled` | `true` | SharePoint 共有 URL からの一時ダウンロード機能の有効/無効。 |
| | `auth_method` | `"az_cli"` | 認証方式。`az` CLI のトークンを使用。 |
| | `graph_endpoint` | `https://graph.microsoft.com/v1.0` | Microsoft Graph の `/shares` 経由取得に使うエンドポイント。 |
| | `timeout_sec` | `60` | ダウンロードのタイムアウト秒。 |
| | `temp_dir` | `null` | 一時保存先。`null` で OS 既定の一時フォルダ。 |
| | `cleanup` | `true` | 実行後に一時ファイルを削除するか。 |

### 6.5 リスト（YAML）によるファイル単位の上書き

`-l/--list` で渡す YAML では、`read_definition` の一部をファイルごとに上書きできる（`config.json` より優先）。解析ロジックに影響するのは以下。

| 項目 | 上書き対象 | 説明 |
| --- | --- | --- |
| `target_sheets` | `read_definition.target_sheets` | 対象シートのキーワード。 |
| `ignore_sheets` | `read_definition.ignore_sheets` | 除外シートのキーワード。 |
| `include_hidden_sheets` | `read_definition.include_hidden_sheets` | 非表示シートを含めるか。 |
| `target_environments` | （追加） | セット名（環境名）に対する対象キーワード。部分一致で絞り込み。 |
| `ignore_environments` | （追加） | セット名（環境名）に対する除外キーワード。部分一致で除外。 |

これらの上書きは `test_stat_cli.py` がタスクの `overrides` として構築し、ファイルごとに `settings` のディープコピーへ適用する（元の `config.json` は書き換えない）。

---

## 7. エラー / 警告一覧

| type | 発生箇所 | 意味 |
| --- | --- | --- |
| `sheet_not_found` | ReadData | `target_sheets` に一致するシートが無い |
| `header_not_found` | ExcelProcessor | `header.search_key` の行が見つからない |
| `inconsistent_result_set` | ExcelProcessor | 結果/担当者/日付の列数が不一致 |
| `inconsistent_plan_set` | ExcelProcessor | 結果列と計画列の数が不一致 |
| `no_tobe_row` | ExcelProcessor | 期待結果/実施対象列が見つからない |
| `no_testcases` | ExcelProcessor | ケース総数が 0 |
| `no_data`（警告） | ReadData | ケース総数が 0 |
| `inconsistent_count`（警告） | ReadData | 消化数が有効ケース数を超過 |

---

## 8. 改修時の指針

- **見出しの表記ゆれ対応** → `*_row.keys` にキーワードを追加（部分一致）。誤検出は `result_row.ignores`（完全一致）で除外。
- **新しい結果種別の追加** → `test_status.results` に追加し、完了/消化の扱いに応じて `completed_results` / `executed_results` にも入れる。
- **「対象外」を集計から外したい** → `read_definition.excluded` に結果値を追加。
- **カウントは残すが日付集計から外したい** → `read_definition.date_invalid_results` に追加。
- **ヘッダー検出位置の変更** → `header.search_col` / `header.search_key`（完全一致である点に注意）。
