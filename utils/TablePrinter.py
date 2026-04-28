import unicodedata

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
    header_line = "│ " + " │ ".join(pad_display(h, w) for h, w in zip(headers, col_widths)) + " │"
    separator = "├" + "┼".join("─" * (w + 2) for w in col_widths) + "┤"
    top_border = "┌" + "┬".join("─" * (w + 2) for w in col_widths) + "┐"
    bottom_border = "└" + "┴".join("─" * (w + 2) for w in col_widths) + "┘"
    
    print(top_border)
    print(header_line)
    print(separator)
    for i, row in enumerate(rows):
        if has_total_row and i == len(rows) - 1 and len(rows) > 1:
            print(separator)
        data_line = "│ " + " │ ".join(pad_display(cell, w) for cell, w in zip(row, col_widths)) + " │"
        print(data_line)
    print(bottom_border)

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
