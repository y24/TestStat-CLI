#!/bin/bash
# TestSpecAnalyticsCLI - シンプルコマンド実行用シェルスクリプト
# 使用方法: ./test-analytics.sh [オプション] [ファイルパス/フォルダパス]

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# Python環境の確認
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "ERROR: Pythonがインストールされていません。"
        echo "Python 3.7以上をインストールしてください。"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# 仮想環境の確認とアクティベート
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    echo "WARNING: 仮想環境が見つかりません。システムのPythonを使用します。"
fi

# 依存関係の確認
if ! $PYTHON_CMD -c "import openpyxl, pyperclip" &> /dev/null; then
    echo "ERROR: 必要なライブラリがインストールされていません。"
    echo "以下のコマンドでインストールしてください："
    echo "pip install -r requirements.txt"
    exit 1
fi

# メインスクリプトの実行
$PYTHON_CMD test_spec_analytics.py "$@"

pause

# エラーコードを保持
EXIT_CODE=$?

# 仮想環境を非アクティブ化
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi

exit $EXIT_CODE 