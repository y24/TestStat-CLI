# リストファイル `project:` ラッパー省略対応 改修計画

## 1. 背景・目的

CLI で読み込むリストファイル（YAML）は、現状すべての設定を最上段の `project:` キー配下にネストする必要がある。

```yaml
project:
  project_name: サンプルプロジェクト
  testing_id: 1001
  files:
    - label: ...
      path: ...
```

しかし `project:` は単なるラッパーであり、機能上の意味を持たない。リスト編集時に常に1段インデントを意識する必要があり煩雑なため、**`project:` を省略してトップレベルに直接書ける**ようにする。

```yaml
# project: ラッパー無し（新形式）
project_name: サンプルプロジェクト
testing_id: 1001
files:
  - label: ...
    path: ...
```

ただし既存のリストファイルを壊さないため、**`project:` ありの旧形式も引き続き読み込める**（後方互換）。

## 2. 現状の実装

- 読み込みロジック: [utils/ProjectList.py](../utils/ProjectList.py) `read_yaml_project_list()`
  - [L38](../utils/ProjectList.py#L38): `data` に `"project"` キーが無いとエラー
  - [L41](../utils/ProjectList.py#L41): `project_data = data["project"]` で取り出し
  - [L44](../utils/ProjectList.py#L44): `project_name`, `files` を必須フィールドとして検証
- 戻り値: `{"project_name", "testing_id", "files", "subtask_id"}`
- 利用側:
  - [test_stat_cli.py:357](../test_stat_cli.py#L357): `ProjectList.read_project_list_file(args.list)`
  - [test_stat_cli.py:245](../test_stat_cli.py#L245): `project_info.get("project_name")`（None 安全）
  - [test_stat_cli.py:584](../test_stat_cli.py#L584): `project_info['project_name']`（直接アクセス。None だと KeyError 等の懸念）
  - [utils/ReportingClient.py:121](../utils/ReportingClient.py#L121): `project_info["project_name"]`

## 3. 改修方針

### 3.1 形式の自動判別（コア変更）

`read_yaml_project_list()` で、トップレベル `data` に `project` キーが存在するかどうかで分岐する。

| 条件 | 解釈 |
| --- | --- |
| `data` が dict かつ `"project"` キーを持つ | **旧形式** → `project_data = data["project"]`（従来どおり） |
| `data` が dict かつ `"project"` キーを持たない | **新形式** → `project_data = data` をそのまま使用 |
| `data` が dict でない / None（空ファイル等） | エラー |

判別ロジック（イメージ）:

```python
if not isinstance(data, dict):
    raise ValueError("プロジェクトリストファイルの形式が不正です: トップレベルがマッピングではありません")

if "project" in data:
    # 旧形式（後方互換）: project: ラッパー配下を使用
    project_data = data["project"]
    if not isinstance(project_data, dict):
        raise ValueError("プロジェクトリストファイルの形式が不正です: 'project'の値がマッピングではありません")
else:
    # 新形式: トップレベルを直接プロジェクト定義として扱う
    project_data = data
```

これ以降の `required_fields`（`project_name`, `files`）検証以下のロジックは現状のまま流用できる。

> 注: `files` を必須とすることで、`project:` キーが無く `files` も無いような不正・空ファイルは新形式側の検証で確実にエラーになる。判別の曖昧さは生じない（トップレベルに `files` があれば新形式、`project` があれば旧形式）。

### 3.2 `project_name` の扱い（任意化の検討）

`project:` を外して編集を楽にする趣旨に沿うと、`project_name` も毎回書くのは煩雑になりうる。本改修では以下のいずれかを選択する（**推奨: 案A**）。

- **案A（推奨・最小変更）**: `project_name` は引き続き必須のままとする。
  - スコープを「`project:` ラッパー省略」に限定し、影響範囲を最小化。
  - 利用側 [test_stat_cli.py:584](../test_stat_cli.py#L584) の直接アクセスも安全なまま。
- **案B（任意化）**: `project_name` も任意フィールド化し、未指定時はリストファイル名（拡張子なし）等をデフォルトにする。
  - 併せて [test_stat_cli.py:584](../test_stat_cli.py#L584) の `project_info['project_name']` を `.get('project_name')` または `or` でのフォールバックに修正し、None 安全化が必須。

本計画では **案A** を採用する（`project:` 省略のみが目的のため）。案B は別タスクとして切り出し可能。

### 3.3 エラーメッセージの調整

- 旧 [L38](../utils/ProjectList.py#L38) の「`'project'`キーが見つかりません」というメッセージは、新形式では正常系になるため削除/置換する。
- 新形式で `files` が無い場合のメッセージは現状の必須フィールド検証（[L44-47](../utils/ProjectList.py#L44)）でカバーされるが、`project:` も `files` も無いケースでユーザーに分かりやすい文言になっているか確認する。

## 4. 変更対象ファイル

| ファイル | 変更内容 |
| --- | --- |
| [utils/ProjectList.py](../utils/ProjectList.py) | `read_yaml_project_list()` に形式自動判別を追加（3.1） |
| [tests/test_remote_source.py](../tests/test_remote_source.py) 等 | ProjectList 用テスト追加（新規 `test_project_list.py` を推奨） |
| [lists/list_sample.yaml](../lists/list_sample.yaml) | 新形式のサンプル追加 or コメントで新形式を併記（旧形式サンプルは別途残す） |
| [README.md](../README.md) | リストファイル仕様の記載更新（`project:` は任意である旨を追記） |
| [docs/requirements.md](../docs/requirements.md) | 必須フィールド説明（L247, L255 付近）の更新 |

> `build/lib/` 配下はビルド生成物のため手動編集不要（パッケージ再ビルドで反映）。

## 5. テスト計画

新規 `tests/test_project_list.py`（または既存テストへ追加）で以下を検証する。

- [ ] **旧形式**（`project:` あり）が従来どおり読み込め、戻り値が一致する（後方互換）
- [ ] **新形式**（`project:` なし、トップレベル直書き）が読み込め、旧形式と同一の戻り値になる
- [ ] 新旧形式で `testing_id` / `subtask_id` / `files` 内オプション（`target_sheets` 等）が同様に解釈される
- [ ] `files` 必須エラー: 新形式で `files` キーが無い場合にエラー
- [ ] `project_name` 必須エラー（案A）: 新形式で `project_name` が無い場合にエラー
- [ ] 空ファイル / トップレベルが dict でない場合にエラー
- [ ] リモートパス（SharePoint URL）が新形式でも `is_remote=True` として正しく扱われる

## 6. 作業ステップ

1. [ ] `read_yaml_project_list()` に形式自動判別を実装（3.1）
2. [ ] エラーメッセージ調整（3.3）
3. [ ] テスト追加・実行（セクション5）
4. [ ] `list_sample.yaml` に新形式の例を反映
5. [ ] README / requirements.md のドキュメント更新
6. [ ] 既存リストファイル（旧形式）で回帰確認（CLI 実行）

## 7. 互換性・リスク

- **後方互換**: `project:` ありの既存リストは判別ロジックでそのまま動作するため影響なし。
- **判別の曖昧さ**: トップレベルに `project` キーがあるかどうかの単純判定。新形式で誤って `project` という名前のファイル項目をトップに置くことは無いため、衝突リスクは無視できる。
- **スコープ限定**: 案A 採用により利用側コードの修正は原則不要。`project_name` 任意化（案B）は将来課題として分離。
