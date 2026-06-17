# SharePoint 共有ファイル ダウンロード集計 改修設計

最終更新: 2026-06-18

## 1. 目的・背景

現状の TestStat-CLI は、リストファイル（YAML）の `files[].path` に **ローカルパス**を指定し、
ローカルに存在する Excel ファイルを集計する。
これは「集計のたびに最新ファイルを手元にコピーする」運用を強制しており、
- コピー漏れ・古いファイルでの集計
- ローカルに散在するファイルの管理コスト
- 共有フォルダ（SharePoint）と手元の二重管理

といった問題がある。

本改修では、**リストファイルの `path` に SharePoint の共有 URL を指定できる**ようにする。
CLI 実行時に Graph API 経由でファイルを一時フォルダへダウンロードし、
ダウンロードしたファイルを既存の集計パイプラインにそのまま渡す。
集計完了後は一時ファイルを破棄する。これによりローカルにファイルを置く必要がなくなる。

### スコープ
- 対象: リストファイル（`-l/--list`）経由の `files[].path`
- 対象: SharePoint / OneDrive for Business 上の `.xlsx` 単一ファイル
- 対象外: 位置引数（`tstat <path>`）でのURL指定（将来拡張・5章参照）
- 対象外: URL でのフォルダ指定（共有 URL=単一ファイル前提）

---

## 2. 全体方針

### 2.1 URL → ファイル特定の肝: Graph `/shares` エンドポイント

site-id / drive-id / item-id を掘り当てず、共有 URL から直接 driveItem に到達する。
`shareId` は共有 URL を以下のルールで変換した文字列（Microsoft 公式の sharing URL エンコード）:

1. URL を UTF-8 で base64 エンコード
2. 末尾の `=`（パディング）を削除
3. `/` → `_`、`+` → `-` に置換
4. 先頭に `u!` を付ける

Python 実装（stdlib のみ）:

```python
import base64

def encode_share_id(url: str) -> str:
    b64 = base64.b64encode(url.strip().encode("utf-8")).decode("ascii")
    return "u!" + b64.rstrip("=").replace("/", "_").replace("+", "-")
```

### 2.2 ダウンロード手順（302 を避ける）

`/content` は 302 リダイレクトを返しバイナリ処理が不安定。
事前認証済みの一時直リンク `@microsoft.graph.downloadUrl` を取得してから本体を落とす2段構え。

```
GET https://graph.microsoft.com/v1.0/shares/{shareId}/driveItem
    ?$select=id,name,@microsoft.graph.downloadUrl
→ name と downloadUrl を取得

GET {downloadUrl}   # 認証ヘッダ不要（署名付き一時URL）
→ 一時フォルダへ保存（ファイル名は Graph 応答の name を採用）
```

> `name` を採用するのは、既存出力（JSON の `file` フィールド等）が `os.path.basename` で
> ファイル名を表示するため。元のファイル名を保つことで表示の一貫性を保つ。

### 2.3 認証方式

本リポジトリは HTTP に追加依存を持たず **stdlib `urllib` のみ**（`utils/ApiIntegration.py` 参照）。
この方針を踏襲し、**トークン取得だけ Azure CLI に委譲**、Graph 呼び出し・ダウンロードは `urllib` で行う。

```python
# az account get-access-token でアクセストークンを取得
token = subprocess.check_output(
    ["az", "account", "get-access-token",
     "--resource", "https://graph.microsoft.com",
     "--query", "accessToken", "-o", "tsv"],
    text=True
).strip()
```

取得したトークンを `Authorization: Bearer {token}` として `/shares` 呼び出しに付与する。

代替案（章末トレードオフ参照）として、Graph 呼び出し自体も `az rest` に丸投げする方式も検討したが、
- 出力のパース（tsv/json）が `az` のバージョンに依存
- ダウンロード本体は結局 `urllib`/`curl` が必要

という理由で、**「az でトークンだけ取り、HTTP は Python」**を採用する。
`az` が PATH に無い・未ログインの場合は明確なエラーメッセージで誘導する。

#### 権限（ハマりどころ）
- `az login` の委任トークンに `Files.Read.All` / `Sites.Read.All` 相当が乗っていないと **403**。
  → エラーメッセージで「適切な Graph スコープを持つアプリ登録でのログイン、または管理者同意」を案内。
- 共有リンク（`:x:/s/...`, `:x:/r/...`）は `/shares` で素直に解決可能。
  `_layouts/15/Doc.aspx?sourcedoc={GUID}...` 形式（発行/埋め込みURL）は解決できないことがある。
  → ドキュメントで「リンクのコピー」で得た共有 URL の使用を推奨。

---

## 3. リストファイル仕様の拡張

### 3.1 `path` で URL を許容（推奨・最小変更）

```yaml
project:
  project_name: サンプルプロジェクト
  testing_id: 1001
  files:
    - label: シナリオテスト_環境1
      path: "https://contoso.sharepoint.com/:x:/s/yoursite/Eab...xxxx"   # SharePoint 共有URL
      subtask_id: 111
      target_sheets: [テスト項目]
    - label: 性能テスト
      path: input_sample/sample2.xlsx                                    # 従来どおりローカルパスもOK
```

判定ロジック: `path` が `http://` / `https://` で始まればリモート、それ以外はローカル。
（既存の `os.path.normpath` はローカルパスのみに適用する。）

### 3.2 任意: 明示フィールド（将来の拡張余地）

URL かローカルかを明示したいケースのために、任意で `source` を許容してもよい:

```yaml
    - label: ...
      path: "https://..."
      source: sharepoint   # 省略時は path の接頭辞で自動判定
```

初期実装では **接頭辞による自動判定のみ**で十分。`source` は予約のみとする。

### 3.3 `ProjectList.read_yaml_project_list` の変更点
- `path` がリモート URL の場合は `os.path.normpath` を適用しない（URL を壊さないため）。
- 抽出 item に `is_remote: bool`（または `remote_url`）を持たせ、後段で分岐できるようにする。

---

## 4. 新規モジュール設計

### 4.1 `utils/RemoteSource.py`（新規）

リモート取得の責務を集約する。HTTP は `urllib`、認証は `az`。

```python
class RemoteSourceError(Exception): ...

def is_remote_path(path: str) -> bool:
    return path.startswith("http://") or path.startswith("https://")

def encode_share_id(url: str) -> str: ...

def get_access_token(resource="https://graph.microsoft.com",
                     logger=None) -> str:
    """az account get-access-token でトークン取得。
    az 未インストール/未ログインは RemoteSourceError に変換。"""

def resolve_download_url(share_id: str, token: str,
                         graph_endpoint: str, timeout: int,
                         logger=None) -> tuple[str, str]:
    """/shares/{shareId}/driveItem を叩き (name, download_url) を返す。
    403/404 を判別し分かりやすいメッセージにする。"""

def download_to_temp(download_url: str, file_name: str,
                     temp_dir: str, timeout: int,
                     logger=None) -> str:
    """downloadUrl からダウンロードし、temp_dir/<file_name> に保存してパスを返す。"""

class RemoteFileManager:
    """一時フォルダのライフサイクル管理。
    - tempfile.mkdtemp(prefix='teststat_') でセッション用ディレクトリ作成
    - fetch(url) -> ローカルパス（同一URLはキャッシュして二重DL回避）
    - cleanup() で再帰削除（config で無効化可）
    - context manager 対応（__enter__/__exit__）"""
    def fetch(self, url: str) -> str: ...
    def cleanup(self) -> None: ...
```

設計上のポイント:
- **トークンは1回取得して使い回す**（複数ファイルでも `az` 呼び出しは1回）。
- **同一 URL の重複ダウンロード回避**（リスト内で同一ファイルを複数 label で参照するケース。`list_sample.yaml` で sample1.xlsx を2回参照している例あり）。
- **temp ディレクトリは実行単位**。`cleanup()` を `main()` の `finally` で必ず呼ぶ。

### 4.2 設定（`config.json` / `default_config.json` に追加）

```json
"sharepoint": {
    "enabled": true,
    "auth_method": "az_cli",
    "graph_endpoint": "https://graph.microsoft.com/v1.0",
    "timeout_sec": 60,
    "temp_dir": null,
    "cleanup": true
}
```

- `enabled`: false ならリモート URL を検出した時点で警告し、そのファイルをスキップ。
- `temp_dir`: null なら OS の一時ディレクトリ（`tempfile.gettempdir()`）配下を使用。
- `cleanup`: false ならデバッグ用にダウンロードファイルを残す（保存先パスをログ出力）。
- `FileScanner.validate_config` は `sharepoint` を**任意セクション**として扱う（後方互換）。

---

## 5. `test_stat_cli.py` への組み込み

変更は `main()` のリスト→タスク変換部（現状 L352–388 付近）と終了処理。

### 5.1 リモート解決の挿入位置

```python
remote_mgr = None  # RemoteFileManager（遅延生成）

for file_info in project_info["files"]:
    raw_path = file_info["path"]

    if RemoteSource.is_remote_path(raw_path):
        sp_cfg = settings.get("sharepoint", {})
        if not sp_cfg.get("enabled", True):
            execution_warnings.append(f"SharePoint連携が無効です（スキップ）: {raw_path}")
            continue
        try:
            if remote_mgr is None:
                remote_mgr = RemoteSource.RemoteFileManager(sp_cfg, verbose_logger)
            target_path = remote_mgr.fetch(raw_path)   # → 一時ローカルパス
        except RemoteSource.RemoteSourceError as e:
            execution_warnings.append(f"SharePointダウンロード失敗: {raw_path} ({e})")
            continue
    else:
        target_path = file_info["path"]
        if not os.path.exists(target_path):
            execution_warnings.append(f"指定されたパスが存在しません: {target_path}")
            continue

    # 以降は既存ロジック（find_excel_files → task 生成）をそのまま流用
```

ポイント:
- ダウンロード後のローカル一時パスを `find_excel_files` / `ReadData.aggregate_results` に渡すため、
  **既存パイプラインは無改修**で動く。
- URL の場合 `find_excel_files` には単一 `.xlsx` ファイルが渡るため `is_valid_search=True` で1件返る。

### 5.2 表示・出力への影響
- `task["filepath"]` は一時パス（例: `C:\Users\...\Temp\teststat_xxx\sample1.xlsx`）。
  JSON 出力・テーブル表示は `os.path.basename` で**ファイル名のみ**になるため、
  元ファイル名を temp に保持していれば表示は自然（一時ディレクトリのパスは露出しない）。
- レポートAPI（`ReportingClient`）も `filepath` ベースで動くため影響なし。
- 必要なら `task` に `source_url` を持たせ、verbose ログで「URL → 一時パス」対応を出力。

### 5.3 終了時クリーンアップ

```python
try:
    ... main 本体 ...
finally:
    if remote_mgr is not None and remote_mgr.cleanup_enabled:
        remote_mgr.cleanup()
```

`sys.exit()` 経路でも消えるよう、`atexit.register(remote_mgr.cleanup)` を併用するか、
`main()` 全体を try/finally で包む。

### 5.4 将来拡張: 位置引数での URL（今回はスコープ外）
`tstat "https://..."` も同じ `RemoteSource` で解決可能。
今回はリスト経由に限定し、`args.path` での URL は「未対応」と警告する。

---

## 6. エラーハンドリング方針

| 事象 | 検出 | メッセージ方針 |
|------|------|----------------|
| `az` がPATHにない | `FileNotFoundError` | 「Azure CLI が見つかりません。インストールと `az login` を実施してください」 |
| 未ログイン | `az` 非0終了 | 「Azure にログインしていません。`az login` を実行してください」 |
| 403（権限不足） | Graph応答 | 「アクセス権がありません。Files.Read.All/Sites.Read.All 相当のスコープを持つログインが必要です」 |
| 404 / 解決不可URL | Graph応答 | 「共有URLを解決できません。発行/埋め込みURLではなく『リンクのコピー』のURLを指定してください」 |
| ネットワーク/タイムアウト | `urllib.error.URLError` | URL と原因を提示 |

- いずれも**当該ファイルのみスキップ**して `execution_warnings` に積み、他ファイルの集計は継続。
- これは既存の「パスが存在しない場合スキップ」と同じ挙動で一貫させる。

---

## 7. テスト計画

`tests/` に `test_remote_source.py` を追加（既存テストは `urllib` をモックする方針）。

- **単体**
  - `encode_share_id`: 既知URL→既知shareId（Microsoft 仕様の固定ベクタで検証）。
  - `is_remote_path`: http/https/ローカルパスの判定。
  - `resolve_download_url`: `urllib` をモックし name/downloadUrl 抽出、403/404 の例外変換。
  - `download_to_temp`: モック応答を temp に書き出し、ファイル名・内容を検証。
  - `RemoteFileManager`: 同一URLキャッシュ、cleanup でディレクトリ削除。
- **結合**
  - `RemoteSource` をモックした状態で `main()` のリスト処理が一時パスを集計に渡すこと。
  - `sharepoint.enabled=false` でスキップ＋警告が出ること。
- **モックモード**（任意・azure_devops 連携と同様の思想）
  - 環境変数 `TESTSTAT_SHAREPOINT_MOCK=1` 時、`az`/Graph を呼ばず
    ローカルの固定 `.xlsx` を返す。CI・オフライン開発用。

---

## 8. 実装計画（フェーズ分割）

### フェーズ1: リモート取得コア（依存なしで単体テスト可能）
1. `utils/RemoteSource.py` 新規作成
   - `is_remote_path`, `encode_share_id`, `get_access_token`,
     `resolve_download_url`, `download_to_temp`, `RemoteFileManager`
2. `tests/test_remote_source.py`（`urllib`/`subprocess` モック）

### フェーズ2: リスト仕様・設定の拡張
3. `utils/ProjectList.py`: URL の場合 `normpath` を回避、`is_remote` を付与
4. `default_config.json` / `config.json` に `sharepoint` セクション追加
5. `FileScanner.validate_config`: `sharepoint` を任意セクションとして許容

### フェーズ3: CLI 統合
6. `test_stat_cli.py` の `main()`：
   - リモート解決の分岐挿入（5.1）
   - `try/finally` + `atexit` でクリーンアップ（5.3）
   - verbose ログ（URL→一時パス）
7. 位置引数 URL は「未対応」警告（5.4）

### フェーズ4: ドキュメント・サンプル
8. `lists/list_sample.yaml` にコメント付きの SharePoint URL 例を追記
9. `README.md` / `assets/.../SKILL.md` / `assets/.../tstat.md` に
   「SharePoint URL 指定」「事前に `az login` が必要」を追記
10. 権限不足時の対処（アプリ登録/管理者同意）を README に記載

### フェーズ5: 検証
11. 実環境の共有 URL で疎通（403/404 のメッセージ確認含む）
12. `cleanup` の動作（成功時/例外時とも一時ファイルが残らない）確認

---

## 9. トレードオフ・代替案

| 論点 | 採用 | 代替 | 理由 |
|------|------|------|------|
| HTTP | `urllib`（stdlib） | `requests` 追加 | 既存方針（追加依存ゼロ）を維持 |
| トークン取得 | `az account get-access-token` | 独自アプリ登録+MSAL | 既存環境（az login 済み）を活用、追加依存なし。権限不足時はアプリ登録へ案内 |
| Graph 呼び出し | Python `urllib` | `az rest` 丸投げ | 出力パースが az 版依存になるのを避け、ダウンロードと実装を統一 |
| URL 指定方法 | `path` 接頭辞で自動判定 | 新フィールド必須化 | リストファイルの後方互換を保ち、記述を最小化 |
| 一時ファイル | 実行単位で mkdtemp→finally削除 | 永続キャッシュ | 「ローカルに置かない」目的に合致。キャッシュは将来拡張 |

---

## 10. 影響ファイル一覧

| ファイル | 変更種別 | 内容 |
|----------|----------|------|
| `utils/RemoteSource.py` | 新規 | リモート取得・一時管理コア |
| `tests/test_remote_source.py` | 新規 | 単体/結合テスト |
| `utils/ProjectList.py` | 変更 | URL の normpath 回避・`is_remote` 付与 |
| `test_stat_cli.py` | 変更 | `main()` にリモート解決・クリーンアップ統合 |
| `utils/FileScanner.py` | 変更 | `validate_config` で `sharepoint` を任意許容 |
| `assets/default_config.json`, `config.json` | 変更 | `sharepoint` セクション追加 |
| `lists/list_sample.yaml` | 変更 | SharePoint URL のサンプル追記 |
| `README.md`, `assets/.../SKILL.md`, `assets/.../tstat.md` | 変更 | 利用手順・前提（az login/権限）追記 |
