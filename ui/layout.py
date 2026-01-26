from typing import Optional

from commands.scene_commands import format_commands
from ui.constants import ACTION_LINES, SCREEN_WIDTH


def strip_ansi(s: str) -> str:
    # Minimal ANSI stripping for accurate padding when we add colors inside lines.
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def pad_or_trim_ansi(text: str, width: int) -> str:
    # Pad based on visible length, not raw length.
    visible = strip_ansi(text)
    if len(visible) >= width:
        # naive trim: trim visible; for demo purposes this is fine
        return text[:width]
    return text + (" " * (width - len(visible)))


def center_ansi(text: str, width: int) -> str:
    visible_len = len(strip_ansi(text))
    if visible_len >= width:
        return text[:width]
    left = (width - visible_len) // 2
    right = width - visible_len - left
    return (" " * left) + text + (" " * right)


def format_action_lines(actions: list[str]) -> list[str]:
    clean = [a for a in actions if a.strip()]
    count = len(clean)
    if count <= 3:
        cols = 1
    elif count <= 6:
        cols = 2
    else:
        cols = 3
    content_width = SCREEN_WIDTH - 4
    gap = 2
    col_width = (content_width - gap * (cols - 1)) // cols
    rows = ACTION_LINES
    lines = []
    for r in range(rows):
        parts = []
        for c in range(cols):
            idx = r + c * rows
            if idx < count:
                parts.append(pad_or_trim_ansi(clean[idx], col_width))
            else:
                parts.append(" " * col_width)
        lines.append((" " * gap).join(parts))
    return lines


def format_command_lines(commands: list[dict]) -> list[str]:
    return format_action_lines(format_commands(commands))


def format_menu_actions(menu_data: dict, replacements: Optional[dict] = None) -> list[str]:
    actions = []
    replacements = replacements or {}
    for command in menu_data.get("actions", []):
        key = str(command.get("key", "")).upper()
        label = str(command.get("label", "")).strip()
        if not key or not label:
            continue
        for token, value in replacements.items():
            label = label.replace(token, value)
        actions.append(f"  [{key}] {label}")
    return format_action_lines(actions)
