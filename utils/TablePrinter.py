import unicodedata
from . import ConsoleStyle

def get_display_width(text):
    """全角・半角を考慮した表示幅を返す"""
    text = str(text)
    width = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ('F', 'W', 'A'):
            width += 2
        else:
            width += 1
    return width

def pad_display(text, width):
    """全角・半角を考慮して幅を揃える"""
    text = str(text)
    pad = width - get_display_width(text)
    return text + ' ' * pad

def _is_full_percent(value):
    value_text = str(value).strip()
    if "(" in value_text and "%)" in value_text:
        value_text = value_text.rsplit("(", 1)[1].split("%", 1)[0]
    try:
        numeric_value = float(value_text.rstrip("%"))
    except ValueError:
        return False
    return numeric_value == 100

def _cell_color(header, value=None):
    header = str(header)
    if header in ("Pass", "Fixed", "Completed"):
        return "white"
    if header in ("完了率(%)", "消化率(%)", "完了数", "消化数", "Completed", "Executed") and _is_full_percent(value):
        return "soft_green"
    if header in ("Fail", "ERROR"):
        return "soft_red"
    if header in ("Blocked",):
        return "soft_cyan"
    if header in ("Suspend",):
        return "soft_yellow"
    if header in ("N/A",):
        return "muted"
    if header in (
        "Total",
        "未実施",
        "完了数",
        "消化数",
        "完了率(%)",
        "消化率(%)",
        "完了数",
        "消化数",
        "Executed",
        "Completed",
        "Executed",
    ):
        return "white"
    return None

def _format_header_cell(text, width):
    return ConsoleStyle.color(pad_display(text, width), "white", bold=True)

def _format_data_cell(header, value, width, *, bold=False):
    return ConsoleStyle.color(pad_display(value, width), _cell_color(header, value), bold=bold)

def print_table(headers, rows, has_total_row=False):
    """全角対応テーブル出力"""
    if not rows:
        return
    col_widths = []
    for i in range(len(headers)):
        max_width = get_display_width(headers[i])
        for row in rows:
            max_width = max(max_width, get_display_width(row[i]))
        col_widths.append(max_width)
    
    # 罫線生成
    border_color = "muted"
    header_line = (
        ConsoleStyle.color("│ ", border_color)
        + ConsoleStyle.color(" │ ", border_color).join(_format_header_cell(h, w) for h, w in zip(headers, col_widths))
        + ConsoleStyle.color(" │", border_color)
    )
    separator = "├" + "┼".join("─" * (w + 2) for w in col_widths) + "┤"
    top_border = "┌" + "┬".join("─" * (w + 2) for w in col_widths) + "┐"
    bottom_border = "└" + "┴".join("─" * (w + 2) for w in col_widths) + "┘"
    
    print(ConsoleStyle.color(top_border, border_color))
    print(header_line)
    print(ConsoleStyle.color(separator, border_color))
    for i, row in enumerate(rows):
        is_total_row = has_total_row and i == len(rows) - 1 and len(rows) > 1
        if is_total_row:
            print(ConsoleStyle.color(separator, border_color))
        data_line = (
            ConsoleStyle.color("│ ", border_color)
            + ConsoleStyle.color(" │ ", border_color).join(
                _format_data_cell(header, cell, width, bold=is_total_row)
                for header, cell, width in zip(headers, row, col_widths)
            )
            + ConsoleStyle.color(" │", border_color)
        )
        print(data_line)
    print(ConsoleStyle.color(bottom_border, border_color))

def shorten_filename(filename, max_width=30):
    """ファイル名が長い場合、先頭と末尾を残して中央を...で省略する（全角半角幅考慮）"""
    if get_display_width(filename) <= max_width:
        return filename
    # 省略記号の幅
    ellipsis = '...'
    ellipsis_width = get_display_width(ellipsis)
    # 先頭・末尾に残す幅を計算
    remain_width = max_width - ellipsis_width
    head_width = remain_width // 2
    tail_width = remain_width - head_width
    
    # 先頭部分
    head = ''
    w = 0
    for ch in filename:
        ch_w = get_display_width(ch)
        if w + ch_w > head_width:
            break
        head += ch
        w += ch_w
    
    # 末尾部分
    tail = ''
    w = 0
    for ch in reversed(filename):
        ch_w = get_display_width(ch)
        if w + ch_w > tail_width:
            break
        tail = ch + tail
        w += ch_w
    
    return head + ellipsis + tail
