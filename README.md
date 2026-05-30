# TestStat

Excel テスト仕様書の集計 CLI、進捗収集バックエンド、将来のフロントエンドを管理するリポジトリです。

## 構成

```text
TestStat-CLI/
├── teststat-cli/       # Excel テスト仕様書を集計する CLI ツール
├── teststat-server/    # CLI から進捗を受け取る FastAPI バックエンド
└── teststat-frontend/  # フロントエンド用ディレクトリ（未開発）
```

## 各プロジェクト

- CLI: [teststat-cli/README.md](teststat-cli/README.md)
- Backend: [teststat-server/README.md](teststat-server/README.md)
- Frontend: 未開発

CLI を実行・インストールする場合は `teststat-cli` に移動して作業してください。

```powershell
cd teststat-cli
pip install .
tstat --help
```
