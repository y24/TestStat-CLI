# 無効な結果の日付を集計範囲から除外する 改修設計

最終更新: 2026-06-22

## 1. 目的・背景

テスト項目の結果列に「対象外」「準備」などの**無効な結果**が入っている行でも、
日付列に値が入っていると、その日付が集計の**日付範囲（開始日・最終更新日）**や
**日次内訳（PB図のX軸）**に紛れ込んでしまう。

具体例:
- 全テストが 5/1〜5/10 に消化済みなのに、「対象外」の行に誤って 6/1 の日付が入っていると、
  最終更新日が 6/1 になり、PB図の横軸も 6/1 まで伸びる。
- 「N/A」の行に古い日付（例: 1/1）が入っていると、開始日が 1/1 に引きずられる。

ユーザー要望は「**対象外や N/A のような無効なテスト結果は、日付が入力されていても無視したい**」。

### 方針確認（合意済み）
- 無効な結果の対象範囲は **`excluded`（対象外・準備）+ 専用リスト新設**とする。
- N/A をその専用リストに入れるかは**設定で制御**する（既定では N/A も無効扱い）。
- **完了数・消化数などの既存カウント挙動は維持**し、**日付範囲算出だけを分離**する。
  - すなわち N/A を「日付無効」にしても、完了数としては従来どおりカウントされ続ける。

### スコープ
- 対象: 結果行（result_row）の値が無効な結果である行の**日付の扱い**。
- 対象: 日付範囲（`start_date` / `last_update`）、日次内訳（`daily`）、環境別内訳（`by_env`）、
  担当者別内訳（`by_name`）。
- 対象外: 計画行（plan_row / 計画数）の日付。計画は結果とは別概念のため本改修では触れない（7章参照）。
- 対象外: 「無効な結果」を**カウント対象から外す**こと（N/A は完了数に残す）。

---

## 2. 現状の問題構造

### 2.1 日付キーが結果種別と無関係に生成される

`utils/DataAggregator.py` の `aggregate_daily_results()` は、各行について
結果の種別に関係なく `initialize_result_counts()` を呼び、`result_count[date]` のキーを作る。

```python
# DataAggregator.py（抜粋・現状）
for index, row in enumerate(data):
    ...
    result, name, date = row[0], row[1], row[2]
    if not date: date = "no_date"
    initialize_result_counts(results, date, ...)   # ← 結果が「対象外」でも date キーを生成

    if result in results:            result_count[date][result] += 1
    if result in completed_results:  result_count[date][completed_label] += 1
    if result in executed_results:   result_count[date][executed_label] += 1
```

- 「対象外」「準備」は `results` / `completed_results` / `executed_results` のいずれにも含まれないため
  カウントは増えないが、**date キーだけが（全 0 の内訳で）生成される**。
- この全 0 の日付キーが `data_daily_total` に残り、後段の範囲算出に混入する。

### 2.2 範囲算出が日付キーの min/max を使う

`utils/ReadData.py` の `_aggregate_final_results()`:

```python
# ReadData.py:90-91（抜粋）
start_date  = min(data_daily_total.keys()) if data_daily_total else None
last_update = max(data_daily_total.keys()) if data_daily_total and run_status in [...] else None
```

`data_daily_total` のキー集合がそのまま範囲になるため、2.1 の余分な日付キーが
開始日・最終更新日を不正に広げる。日次内訳（`daily`）は集計APIへ送られ PB図のX軸範囲にも波及する。

### 2.3 担当者別集計も無効な結果を含む

`aggregate_daily_by_person()` は日付が空の行のみ除外し、結果値はチェックしない:

```python
# DataAggregator.py:47-60（抜粋）
data = [row for row in data if len(row) > 2 and row[2] not in ("", None)]
for row in data:
    result, name, date = row[0], row[1], row[2]
    if result:                       # ← 「対象外」でも True
        date_name_count[date][name] += 1
```

→ 担当者別内訳にも「対象外」の日付が混入する（主に verbose ログに影響）。

### 2.4 呼び出し箇所
`aggregate_daily_results()` は 2 箇所から呼ばれる。両方に同じ修正が効くようにする。
- `utils/ReadData.py:56`（ファイル全体の日次集計 → 範囲算出元）
- `utils/ExcelProcessor.py:69`（環境別 `by_env` の日次集計）

---

## 3. 改修方針

### 3.1 中核アイデア: 「無効な結果の行は日付を無視（= no_date 扱い）」

「日付が入力されていても無視」を、**当該行の日付を `no_date` に倒す**ことで実現する。

- 「対象外」「準備」: もともとカウント対象外。`no_date` に倒しても合計に影響なし
  （`initialize_result_counts` は `results`＋ラベルのキーしか作らないため、`対象外` というキー自体が生成されない）。
- 「N/A」（無効リストに含めた場合）: `no_date` バケットでカウントされる。
  `calculate_total_results()` が `no_date_data` を合算するため、**完了数・消化数は従来どおり保持される**。

この「no_date へ倒す」方式により、

| 観点 | 結果 |
|------|------|
| 日付範囲（start/last） | 無効な結果の日付は `data_daily_total` に現れず、範囲から外れる ✓ |
| 日次内訳 / PB図X軸 | 同上。全 0 の余分な日付が消える ✓ |
| 完了数・消化数（N/A） | `no_date` 経由で合算され従来どおり ✓ |
| 完了率・消化率 | 分子（completed/executed）が保持されるため不変 ✓ |

### 3.2 「無効な結果」集合の定義

実効的な無効集合 = `read_definition.excluded` ∪ `read_definition.date_invalid_results`

- `excluded`（既存）: `["対象外", "準備"]` … 集計対象から除外する結果。日付も当然無視する。
- `date_invalid_results`（**新設**）: 「カウントはするが日付は無視したい」結果を列挙。既定 `["N/A"]`。

両者を和集合にすることで、「対象外は除外かつ日付無視」「N/A はカウント維持だが日付無視」を
1 つのルール（無効集合に入っていれば日付を no_date に倒す）で統一的に扱える。

---

## 4. 設定拡張

`assets/default_config.json` および `config_sample.json` の `read_definition` に追加:

```json
"read_definition": {
    "...": "...",
    "excluded": [
        "対象外",
        "準備"
    ],
    "date_invalid_results": [
        "N/A"
    ]
}
```

- `date_invalid_results`: 日付を範囲算出に使わない結果。**カウント自体は通常どおり**行う。
- 省略時は `[]` として扱う（後方互換）。実効無効集合は常に `excluded` を含む。
- N/A を日付範囲に含めたい運用なら、このリストを空 `[]` にすればよい。

> 補足: `excluded` は従来どおり「項目数 = 全数 − excluded」の算出にも使われる（`get_excluded_count`）。
> `date_invalid_results` は**カウントには関与しない**（日付の扱いのみ）。役割を分離しておく。

---

## 5. 実装変更点

### 5.1 `utils/DataAggregator.py`

#### (a) `aggregate_daily_results()` に `invalid_results` を追加

引数末尾に `invalid_results: list[str] = None` を追加し、行の日付を倒す:

```python
def aggregate_daily_results(data, results, completed_label, completed_results,
                            executed_label, executed_results, plan_label,
                            plan_data=None, invalid_results=None):
    invalid_results = invalid_results or []
    ...
    for index, row in enumerate(data):
        # plan の処理は従来どおり（変更なし）
        ...
        result, name, date = row[0], row[1], row[2]

        # 無効な結果は日付を無視（no_date に倒す）→ 範囲・日次内訳に出さない
        if not date or result in invalid_results:
            date = "no_date"

        initialize_result_counts(results, date, ...)
        if result in results:            result_count[date][result] += 1
        if result in completed_results:  result_count[date][completed_label] += 1
        if result in executed_results:   result_count[date][executed_label] += 1
    ...
```

ポイント:
- カウントの `if result in ...` 分岐は**無改修**。N/A は no_date バケットで従来どおり加算される。
- 計画（plan）ブロックは無効集合の対象外（4 章スコープ）なので手を入れない。

#### (b) `aggregate_daily_by_person()` に `invalid_results` を追加

無効な結果の行は担当者別内訳から除外する:

```python
def aggregate_daily_by_person(data, invalid_results=None):
    invalid_results = invalid_results or []
    data = [row for row in data
            if len(row) > 2 and row[2] not in ("", None)
            and row[0] not in invalid_results]      # ← 無効な結果を除外
    ...
```

### 5.2 `utils/ReadData.py`

`_aggregate_final_results()` で無効集合を組み立てて両関数へ渡す:

```python
read_def = settings["read_definition"]
invalid_results = list(read_def.get("excluded", [])) + list(read_def.get("date_invalid_results", []))

data_daily_total, no_date_data = DataAggregator.aggregate_daily_results(
    all_data, settings["test_status"]["results"],
    ..., all_plan_data,
    invalid_results=invalid_results,             # 追加
)

data_by_name = DataAggregator.aggregate_daily_by_person(
    all_data, invalid_results=invalid_results,   # 追加
)
```

`start_date` / `last_update` のロジック（ReadData.py:90-91）は**無改修**。
`data_daily_total` から無効日付が消えることで自動的に正しい範囲になる。

### 5.3 `utils/ExcelProcessor.py`

環境別集計の呼び出し（ExcelProcessor.py:69）にも同じ無効集合を渡す:

```python
read_def = settings.get("read_definition", {})
invalid_results = list(read_def.get("excluded", [])) + list(read_def.get("date_invalid_results", []))

env_data[set_name], _ = DataAggregator.aggregate_daily_results(
    data=processed_data,
    ...,
    plan_data=plan_data,
    invalid_results=invalid_results,             # 追加
)
```

これで `by_env` 内訳からも無効日付が除外され、CLI 全体で挙動が一貫する。

---

## 6. エッジケース

| ケース | 挙動 | 評価 |
|--------|------|------|
| 同一日に有効結果と無効結果が混在 | 有効結果が日付を保持するため、その日は範囲に残る。無効結果のみ no_date へ | 妥当（実作業がある日は範囲に含む） |
| ある日が無効結果のみ | その日付キーが消え、範囲・PB図から外れる | 要望どおり ✓ |
| N/A を `date_invalid_results` に含めた行 | 完了数・消化数には算入（no_date 経由）、範囲には出ない | 「カウント維持・範囲分離」を満たす ✓ |
| ファイルの結果が**全て無効**（全 N/A 等） | `data_daily_total` が空 → `start_date`/`last_update` が `None`。完了数は no_date 経由で残る | 仕様として許容。日付を持たない完了扱い。verbose で気付けるよう注記 |
| `date_invalid_results` 未設定（既存 config） | `excluded` のみが無効集合。N/A は従来どおり日付込み | 後方互換 ✓ |
| 日付が空 + 無効結果 | 元々 no_date。挙動不変 | ✓ |

> 「全て無効」のケースで `start_date=None` になる点は、`determine_run_status()` 自体は
> `executed`/`completed`/`available` カウントで判定するため**状態判定には影響しない**
> （N/A は executed/completed に算入されるため「完了」や「進行中」と判定され得る）。
> 日付だけが付かない、という整合した結果になる。

---

## 7. 対象外（今回触れない範囲）と理由

- **計画行（plan / 計画数）の日付**: 結果値ではなく計画日。`aggregate_daily_results` 冒頭の
  plan ブロックで独立して `plan_date` を登録している。要望は「無効な*結果*の日付」なので対象外。
  必要なら別途「計画日の妥当性」改修として切り出す。
- **N/A をカウントからも外すこと**: 今回の合意は「カウント維持・範囲分離」。N/A 自体を
  未消化扱いにする変更は挙動への影響が大きいため別案件。

---

## 8. テスト計画

`tests/test_data_aggregator.py`（新規）を追加。`DataAggregator` 単体での検証。

- **`aggregate_daily_results`**
  - 「対象外」+日付ありの行 → `daily` にその日付が**現れない**こと。
  - 「N/A」を `invalid_results` に含めた行 → `daily` に日付は出ないが、
    `no_date_data` 側に completed/executed が計上されること。
  - 有効結果（Pass 等）+日付 → 従来どおり `daily` にその日付が出ること。
  - 同一日に Pass と 対象外が混在 → その日は残り、件数は Pass の分のみ。
  - `invalid_results=None`（未指定）→ 従来挙動（後方互換）。
- **`aggregate_daily_by_person`**
  - 「対象外」の行が担当者別内訳に**含まれない**こと。
- **結合（`ReadData` 経由）**
  - 無効結果に未来日が入ったダミーデータで `start_date`/`last_update` が
    有効結果の範囲に収まること（範囲が広がらないこと）。
  - 完了数・完了率が修正前後で不変であること（N/A をカウントに残す回帰確認）。

サンプル Excel を使う結合確認は `input_sample/` の既存ファイル＋手動で
無効結果行に未来日を仕込んだケースで `tstat -v` の開始日/最終更新日を目視確認する。

---

## 9. 実装フェーズ

### フェーズ1: 集計コア（単体テスト可能）
1. `utils/DataAggregator.py`
   - `aggregate_daily_results` に `invalid_results` 引数追加・日付を no_date に倒す処理
   - `aggregate_daily_by_person` に `invalid_results` 引数追加・行フィルタ
2. `tests/test_data_aggregator.py` 新規（8 章）

### フェーズ2: 設定・配線
3. `assets/default_config.json` / `config_sample.json` に `date_invalid_results` 追加
4. `utils/ReadData.py`：無効集合を組み立て、両関数へ受け渡し
5. `utils/ExcelProcessor.py`：環境別集計に無効集合を受け渡し

### フェーズ3: 検証
6. `input_sample/` のファイルに無効結果＋未来日を仕込み、`tstat -v` で
   開始日・最終更新日・PB図範囲が広がらないことを確認
7. 完了数・完了率が回帰していないことを確認

### フェーズ4: ドキュメント
8. `README.md` に `date_invalid_results` の説明（N/A の日付を範囲から外す設定）を追記
9. 必要に応じて `config_sample.json` のコメント的サンプルを整備

---

## 10. 影響ファイル一覧

| ファイル | 変更種別 | 内容 |
|----------|----------|------|
| `utils/DataAggregator.py` | 変更 | `aggregate_daily_results` / `aggregate_daily_by_person` に `invalid_results` 追加 |
| `utils/ReadData.py` | 変更 | 無効集合の組み立てと受け渡し |
| `utils/ExcelProcessor.py` | 変更 | 環境別集計への受け渡し |
| `assets/default_config.json` | 変更 | `read_definition.date_invalid_results` 追加 |
| `config_sample.json` | 変更 | 同上（サンプル） |
| `tests/test_data_aggregator.py` | 新規 | 集計ロジックの単体/回帰テスト |
| `README.md` | 変更 | 新設定の説明追記 |

---

## 11. トレードオフ・代替案

| 論点 | 採用 | 代替 | 理由 |
|------|------|------|------|
| 無効結果の日付処理 | 当該行を no_date へ倒す | 範囲算出時に min/max を計算する前にキーをフィルタ | no_date 方式は N/A のカウントを自然に保持でき、`calculate_total_results` の既存合算に乗る。フィルタ方式は範囲は直せてもカウント保持の追加配慮が必要 |
| 無効集合の定義 | `excluded` ∪ 新設 `date_invalid_results` | `excluded` だけを流用 | N/A は集計上は有効（完了）なので `excluded` に入れられない。日付無視専用リストを分けることで役割が明確 |
| N/A の既定 | `date_invalid_results: ["N/A"]`（既定で日付無視） | 既定空で運用者が設定 | ユーザー要望が「N/A の日付も無視」。既定で要望を満たしつつ、空にすれば従来挙動へ戻せる |
| 計画日 | スコープ外 | 同様に無効化 | 要望は結果値が対象。計画は別概念のため切り分け |
