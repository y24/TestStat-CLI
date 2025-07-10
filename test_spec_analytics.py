import json
from utils import ReadData
import sys

if __name__ == "__main__":
    # 設定ファイル読み込み
    with open("config.json", encoding="utf-8") as f:
        settings = json.load(f)

    # 仮: ファイル名を直書き
    filepath = "input_sample/sample1.xlsx"

    # 集計実行
    result = ReadData.aggregate_results(filepath, settings)

    # 結果出力（テーブル形式/簡易）
    print("=== 集計結果 ===")
    if "error" in result:
        print(f"ERROR: {result['error']['message']}")
    else:
        print(f"ファイル: {filepath}")
        print(f"総ケース数: {result['stats']['all']}")
        print(f"有効ケース数: {result['stats']['available']}")
        print(f"除外ケース数: {result['stats']['excluded']}")
        print(f"消化数: {result['stats']['executed']}")
        print(f"完了数: {result['stats']['completed']}")
        print(f"未実施数: {result['stats']['incompleted']}")
        print(f"計画数: {result['stats']['planned']}")
        print(f"実施状況: {result['run']['status']}")
        print(f"開始日: {result['run']['start_date']}")
        print(f"最終更新日: {result['run']['last_update']}") 