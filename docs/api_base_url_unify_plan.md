# config.json APIエンドポイント `/api` 付与統一 改修計画

## 1. 背景・課題

`config.json` で指定する各APIの `base_url` の粒度が統一されていない。

| API | 現状 `base_url` | クライアントが付与するパス | 最終URL |
| --- | --- | --- | --- |
| `wbs_api` | `http://localhost:5173/api` | `/api/subtasks/{id}` | `…/api/api/subtasks/{id}` ⚠️ |
| `reporting_api` | `http://localhost:18000` | `/api/v1/progress` 等 | `…/api/v1/progress` ✓ |

問題点は2つ。

1. **粒度の不統一**：`wbs_api` は `base_url` に `/api` を含めるのに、`reporting_api` は含めない。ユーザーがどちらの流儀で書けばよいか分かりにくい。
2. **設定ファイル間でも不整合**：現状、3つの設定ファイルで `base_url` の書き方がバラバラになっている。

| ファイル | `wbs_api.base_url` | `reporting_api.base_url` |
| --- | --- | --- |
| `teststat-cli/config.json` | `http://localhost:5173/api` | `http://localhost:18000` |
| `teststat-cli/config_sample.json` | `http://your-server/wbs` | `http://your-server/tstat` |
| `teststat-cli/assets/default_config.json` | `http://localhost:5173` | `http://localhost:18000` |

クライアントコードは両APIとも `/api` をコード側で付与する実装になっている（後述）。そのため `config.json` の `wbs_api.base_url` に書かれた末尾 `/api` は二重付与となり、現状の値は実質的に不正。

## 2. 方針

ユーザー要望どおり **`base_url` に `/api` を含める流儀へ統一** する。
すなわち「`base_url` = ホスト＋`/api` まで」とし、クライアントコードはその後ろのバージョン/リソースパスのみを付与する。

統一後の構成：

| API | 統一後 `base_url` | クライアントが付与するパス | 最終URL（変化なし） |
| --- | --- | --- | --- |
| `wbs_api` | `http://localhost:5173/api` | `/subtasks/{id}` | `…/api/subtasks/{id}` |
| `reporting_api` | `http://localhost:18000/api` | `/v1/progress` 等 | `…/api/v1/progress` |

### 重要ポイント
- **最終的に組み立てられるURLは現状と変わらない**（`reporting_api` は正常系のまま、`wbs_api` は二重 `/api` バグが解消される方向）。
- **サーバ側（teststat-server）の変更は不要**。FastAPIルーターは `prefix="/api/v1/..."` 固定で、最終URLが変わらないため。
- 影響範囲はCLI側の設定ファイル・クライアントコード・ドキュメントのみ。

## 3. 改修内容

### 3-1. クライアントコード（`/api` をコード側から除去）

#### `teststat-cli/utils/ApiIntegration.py`
- L22: `url = f"{base_url.rstrip('/')}/api/subtasks/{subtask_id}"`
  → `url = f"{base_url.rstrip('/')}/subtasks/{subtask_id}"`

#### `teststat-cli/utils/ReportingClient.py`
- L129: `url = f"{base_url.rstrip('/')}/api/v1/projects/{testing_id}"`
  → `url = f"{base_url.rstrip('/')}/v1/projects/{testing_id}"`
- L161: `url = f"{base_url.rstrip('/')}/api/v1/progress"`
  → `url = f"{base_url.rstrip('/')}/v1/progress"`

### 3-2. 設定ファイル（`base_url` に `/api` を付与し、3ファイルで統一）

#### `teststat-cli/config.json`
- `reporting_api.base_url`: `http://localhost:18000` → `http://localhost:18000/api`
- `wbs_api.base_url`: `http://localhost:5173/api`（変更なし。コード修正により二重 `/api` が解消され、正しい値になる）

#### `teststat-cli/assets/default_config.json`
- `wbs_api.base_url`: `http://localhost:5173` → `http://localhost:5173/api`
- `reporting_api.base_url`: `http://localhost:18000` → `http://localhost:18000/api`

#### `teststat-cli/config_sample.json`
- `wbs_api.base_url`: `http://your-server/wbs` → `http://your-server/wbs/api`
- `reporting_api.base_url`: `http://your-server/tstat` → `http://your-server/tstat/api`

### 3-3. ドキュメント（`teststat-cli/README.md`）

- L489: `{base_url}/api/v1/progress` → `{base_url}/v1/progress`、説明文を「`base_url` に `/api` まで含める」旨へ修正。例 `http://<server-name>/tstat` → `http://<server-name>/tstat/api`
- L506: 「`/api` はツール側で付与します」→「`base_url` には末尾の `/api` まで含めて指定します」へ修正
- L525: `{reporting_api.base_url}/api/v1/progress` → `{reporting_api.base_url}/v1/progress`
- L537: `{base_url}/api/subtasks/{subtask_id}` → `{base_url}/subtasks/{subtask_id}`

## 4. 影響範囲まとめ

| 対象 | 変更 |
| --- | --- |
| `teststat-cli/utils/ApiIntegration.py` | URL組み立てから `/api` 除去 |
| `teststat-cli/utils/ReportingClient.py` | URL組み立て2箇所から `/api` 除去 |
| `teststat-cli/config.json` | `reporting_api.base_url` に `/api` 付与 |
| `teststat-cli/assets/default_config.json` | 両 `base_url` に `/api` 付与 |
| `teststat-cli/config_sample.json` | 両 `base_url` に `/api` 付与 |
| `teststat-cli/README.md` | 説明・例の更新 |
| teststat-server | **変更なし** |

## 5. 移行時の注意（既存ユーザー）

本改修は **`config.json` の書式変更を伴う破壊的変更**。すでに `reporting_api.base_url` を `/api` なしで運用している環境では、アップデート後に `base_url` の末尾へ `/api` を追記する必要がある。

- 追記漏れの場合、`reporting_api` は `…/v1/progress`（`/api` 欠落）へ送信し404となる。
- README の移行メモに「アップデート時は `base_url` に `/api` を追記」と明記する。

（任意の堅牢化案）クライアント側で `base_url` 末尾が `/api` で終わらない場合に警告ログを出す、もしくは自動補完する処理を入れる選択肢もあるが、本計画では「明示的に `/api` を含める」方針を優先し、自動補完は採用しない。

## 6. 動作確認

1. `reporting_api.enabled=true` の状態で `-l <yaml>` を実行し、`{base_url}/v1/progress` 相当（最終 `…/api/v1/progress`）へ正常送信されること。
2. teststat-server 側のログ/DBに進捗が反映されること（最終URLが現状と一致するため挙動不変）。
3. `wbs_api.enabled=true`・`subtask_id` 指定時に `…/api/subtasks/{id}` へPATCHされること（二重 `/api` が解消されていること）。
4. 既存のサーバ側テスト（`/api/v1/...` を叩く `test_*.py`）は変更不要・パスのままであること。
