import os
import sys

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

COLORS = {
    "muted": "\033[90m",
    "red": "\033[31m",
    "green": "\033[32m",
    "soft_green": "\033[38;5;70m",
    "yellow": "\033[33m",
    "light_yellow": "\033[93m",
    "soft_yellow": "\033[38;5;222m",
    "orange": "\033[38;5;208m",
    "blue": "\033[34m",
    "soft_cyan": "\033[38;5;74m",
    "logo_mint": "\033[38;5;115m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "soft_red": "\033[38;5;203m",
    "white": "\033[37m",
}


def use_color(stream=None):
    """ANSIカラーを使える場合だけTrueを返す。NO_COLORを尊重する。"""
    if "NO_COLOR" in os.environ:
        return False
    if os.environ.get("FORCE_COLOR") not in (None, "", "0"):
        return True

    stream = stream or sys.stdout
    return hasattr(stream, "isatty") and stream.isatty() and os.environ.get("TERM") != "dumb"


def color(text, fg=None, *, bold=False, dim=False):
    """色指定が有効なときだけANSI装飾を付ける。"""
    text = str(text)
    if not use_color():
        return text

    parts = []
    if bold:
        parts.append(BOLD)
    if dim:
        parts.append(DIM)
    if fg:
        parts.append(COLORS[fg])
    if not parts:
        return text
    return "".join(parts) + text + RESET


def section_title(text):
    return color(text, "logo_mint", bold=True)


def subsection_title(text):
    return color(text, "logo_mint", bold=True)


def label(text):
    return color(text, "muted")


def status(text):
    status_text = str(text)
    status_colors = {
        "完了": "green",
        "進行中": "cyan",
        "未開始": "muted",
        "遅延": "red",
    }
    return color(status_text, status_colors.get(status_text, "white"), bold=status_text != "進行中")


def metric(label_text, value):
    return f"{label(label_text + ':')} {color(value, 'white', bold=True)}"
