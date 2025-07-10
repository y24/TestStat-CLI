from utils import Utility

def make_graph_tooltip(display_data: dict) -> str:
    """グラフのツールチップ用のラベルを生成する

    Args:
        display_data: 表示データ

    Returns:
        str: ツールチップ用のラベル
    """
    return f"項目数: {display_data['available']} (Total: {display_data['all']} / 対象外: {display_data['excluded']})\nState: {display_data['state']}\n{make_results_text(display_data['total_data'], display_data['incompleted'])}"

def make_results_text(results: dict, incompleted: int) -> str:
    """テスト結果のテキストを生成する

    Args:
        results: テスト結果データ
        incompleted: 未着手数

    Returns:
        str: テスト結果のテキスト
    """
    # 各結果テキストの生成
    items = [f'{key}:{value}' for key, value in results.items() if value > 0]
    
    # 未着手数を付加
    not_run_text = f'未着手:{incompleted}'
    if incompleted: items.append(not_run_text)
    
    # 結果テキストの結合
    if len(items):
        return ', '.join(items)
    else:
        return "有効なデータがありません。エラーのないファイルのみが集計されます。"

def make_count_and_rate_text(top: int, bottom: int) -> str:
    return f"{top}/{bottom} ({(top/bottom*100):.1f}%)" if bottom else "-"