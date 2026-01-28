"""Rendering and animation helpers for ASCII UI frames."""

import sys
import time
import textwrap
from dataclasses import replace
from typing import List, Optional

from app.commands.scene_commands import format_commands, scene_commands
from app.models import Frame, Player, Opponent
from app.ui.ansi import ANSI, color
from app.ui.constants import (
    NARRATIVE_INDENT,
    OPPONENT_ART_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STAT_LINES,
)
from app.ui.layout import center_ansi, format_action_lines, pad_or_trim_ansi, pad_ansi, strip_ansi
from app.combat import battle_action_delay


COLOR_BY_NAME = {
    "white": ANSI.FG_WHITE,
    "cyan": ANSI.FG_CYAN,
    "green": ANSI.FG_GREEN,
    "yellow": ANSI.FG_YELLOW,
    "red": ANSI.FG_RED,
    "blue": ANSI.FG_BLUE,
}


def mirror_line(line: str) -> str:
    swaps = str.maketrans({
        "/": "\\",
        "\\": "/",
        "(": ")",
        ")": "(",
        "<": ">",
        ">": "<",
        "[": "]",
        "]": "[",
        "{": "}",
        "}": "{",
    })
    return line[::-1].translate(swaps)


def render_venue_art(venue: dict, npc: dict, color_map_override: Optional[dict] = None) -> tuple[List[str], str]:
    art_color = COLOR_BY_NAME.get(venue.get("color", "white").lower(), ANSI.FG_WHITE)
    npc_art = npc.get("art", [])
    npc_color = COLOR_BY_NAME.get(npc.get("color", "white").lower(), ANSI.FG_WHITE)
    gap_width = int(venue.get("gap_width", 0))
    left = venue.get("left", [])
    right = venue.get("right", [])
    top = venue.get("top")
    top_color = venue.get("top_color", "")
    left_color = venue.get("left_color", [])
    right_color = venue.get("right_color", [])
    color_map = venue.get("color_map") or (color_map_override or {})

    def truecolor(code: str) -> str:
        value = code.lstrip("#")
        if len(value) != 6:
            return ""
        try:
            r = int(value[0:2], 16)
            g = int(value[2:4], 16)
            b = int(value[4:6], 16)
        except ValueError:
            return ""
        return f"\033[38;2;{r};{g};{b}m"

    color_by_key = {}
    for key, entry in color_map.items():
        if isinstance(entry, dict):
            hex_code = entry.get("hex", "") if isinstance(entry.get("hex"), str) else ""
            name = entry.get("name", "") if isinstance(entry.get("name"), str) else ""
        elif isinstance(entry, str):
            hex_code = ""
            name = entry
        else:
            continue
        name = name.strip()
        hex_code = hex_code.strip()
        if not hex_code:
            hex_start = name.find("#")
            hex_code = name[hex_start:] if hex_start != -1 else ""
        if hex_code:
            code = truecolor(hex_code)
            if code:
                color_by_key[key] = code
                continue
        lowered = name.lower()
        if lowered == "brown":
            color_by_key[key] = ANSI.FG_YELLOW + ANSI.DIM
        elif lowered in ("gray", "grey"):
            color_by_key[key] = ANSI.FG_WHITE + ANSI.DIM
        else:
            color_by_key[key] = COLOR_BY_NAME.get(lowered, ANSI.FG_WHITE)

    def apply_color_mask(line: str, mask: str) -> str:
        if not color_by_key or not mask:
            return line
        base = art_color
        out = []
        for i, ch in enumerate(line):
            code = color_by_key.get(mask[i]) if i < len(mask) else None
            if code:
                out.append(code + ch + ANSI.RESET + base)
            else:
                out.append(ch)
        return "".join(out)

    if left:
        if not right:
            right = [mirror_line(line) for line in left]
        max_left = max((len(line) for line in left), default=0)
        max_right = max((len(line) for line in right), default=0)
        left = [line.ljust(max_left) for line in left]
        right = [line.ljust(max_right) for line in right]
        raw_lines = [line[:gap_width].rstrip() for line in npc_art]
        max_len = max((len(line) for line in raw_lines), default=0)
        left_aligned = [line.ljust(max_len) for line in raw_lines]
        centered = [line.center(gap_width) for line in left_aligned]
        max_rows = max(len(left), len(right))
        start_row = max(0, max_rows - len(centered))
        art_lines = []
        for i in range(max_rows):
            left_line = left[i] if i < len(left) else (" " * max_left)
            right_line = right[i] if i < len(right) else (" " * max_right)
            left_mask = left_color[i] if i < len(left_color) else ""
            right_mask = right_color[i] if i < len(right_color) else ""
            left_line = apply_color_mask(left_line, left_mask)
            right_line = apply_color_mask(right_line, right_mask)
            gap_fill = " " * gap_width
            if top and i == 0:
                mask = ""
                if isinstance(top_color, str) and top_color:
                    mask = (top_color * gap_width)[:gap_width] if len(top_color) == 1 else top_color[:gap_width]
                gap_fill = apply_color_mask("=" * gap_width, mask)
            elif centered and start_row <= i < start_row + len(centered):
                npc_line = centered[i - start_row]
                gap_fill = npc_color + npc_line + art_color
            art_lines.append(left_line + gap_fill + right_line)
        return art_lines, art_color

    art_template = venue.get("art", [])
    if art_template:
        if gap_width > 0:
            raw_lines = [line[:gap_width].rstrip() for line in npc_art]
            max_len = max((len(line) for line in raw_lines), default=0)
            left_aligned = [line.ljust(max_len) for line in raw_lines]
            centered = [line.center(gap_width) for line in left_aligned]
            art_lines = []
            start_row = max(0, len(art_template) - len(centered))
            for i, line in enumerate(art_template):
                gap_fill = " " * gap_width
                if centered and start_row <= i < start_row + len(centered):
                    npc_line = centered[i - start_row]
                    gap_fill = npc_color + npc_line + art_color
                art_lines.append(line.replace("{GAP}", gap_fill))
            return art_lines, art_color
        return art_template, art_color
    return [], art_color


def render_scene_art(
    scene_data: dict,
    opponents: List[Opponent],
    gap_override: Optional[int] = None,
    flash_index: Optional[int] = None,
    flash_color: Optional[str] = None,
    visible_indices: Optional[set] = None,
    include_bars: bool = True,
    manual_lines_indices: Optional[set] = None
) -> tuple[List[str], str]:
    """Compose scene art with optional opponent blocks in the gap."""
    art_color = COLOR_BY_NAME.get(scene_data.get("color", "white").lower(), ANSI.FG_WHITE)
    gap_base = (
        int(scene_data.get("gap_min", 2))
        if scene_data.get("left")
        else int(scene_data.get("gap_width", 20))
    )
    gap_width = gap_override if gap_override is not None else gap_base
    opponent_blocks = []
    for i, opponent in enumerate(opponents):
        if not opponent.art_lines:
            continue
        is_visible = visible_indices is None or i in visible_indices
        if manual_lines_indices and i in manual_lines_indices:
            raw_lines = [line[:OPPONENT_ART_WIDTH] for line in opponent.art_lines]
            max_len = max((len(line) for line in raw_lines), default=0)
            left_aligned = [line.ljust(max_len) for line in raw_lines]
            art_lines = [line.center(OPPONENT_ART_WIDTH) for line in left_aligned]
        elif opponent.hp > 0 and is_visible:
            raw_lines = [line[:OPPONENT_ART_WIDTH].rstrip() for line in opponent.art_lines]
            max_len = max((len(line) for line in raw_lines), default=0)
            left_aligned = [line.ljust(max_len) for line in raw_lines]
            art_lines = [line.center(OPPONENT_ART_WIDTH) for line in left_aligned]
            if include_bars:
                art_lines.append(" " * OPPONENT_ART_WIDTH)
                art_lines.append(pad_ansi(format_opponent_bar(opponent), OPPONENT_ART_WIDTH))
        elif is_visible:
            art_lines = [" " * OPPONENT_ART_WIDTH for _ in opponent.art_lines]
            if include_bars:
                art_lines.append(" " * OPPONENT_ART_WIDTH)
                art_lines.append(" " * OPPONENT_ART_WIDTH)
        else:
            art_lines = [" " * OPPONENT_ART_WIDTH for _ in opponent.art_lines]
            if include_bars:
                art_lines.append(" " * OPPONENT_ART_WIDTH)
                art_lines.append(" " * OPPONENT_ART_WIDTH)
        if manual_lines_indices and i in manual_lines_indices and include_bars:
            art_lines.append(" " * OPPONENT_ART_WIDTH)
            art_lines.append(" " * OPPONENT_ART_WIDTH)
        color_to_use = opponent.art_color
        if flash_index == i and flash_color:
            color_to_use = flash_color
        opponent_blocks.append(
            {
                "lines": art_lines,
                "width": OPPONENT_ART_WIDTH,
                "color": color_to_use,
            }
        )
    if scene_data.get("left"):
        left = scene_data.get("left", [])
        right = scene_data.get("right", [])
        if not right:
            right = [mirror_line(line) for line in left]
        max_left = max((len(line) for line in left), default=0)
        max_right = max((len(line) for line in right), default=0)
        left = [line.ljust(max_left) for line in left]
        right = [line.ljust(max_right) for line in right]
        if opponent_blocks:
            gap_pad = 2
            inter_pad = 2
            content_width = (
                (gap_pad * 2)
                + sum(block["width"] for block in opponent_blocks)
                + (inter_pad * (len(opponent_blocks) - 1))
            )
            gap_width = max(gap_width, content_width)
        art_lines = []
        max_rows = max(len(left), len(right))
        max_opp_rows = max((len(block["lines"]) for block in opponent_blocks), default=0)
        start_row = (max_rows - max_opp_rows) // 2 if max_opp_rows else 0
        for i in range(max_rows):
            left_line = left[i] if i < len(left) else (" " * max_left)
            right_line = right[i] if i < len(right) else (" " * max_right)
            gap_fill = " " * gap_width
            if opponent_blocks and start_row <= i < start_row + max_opp_rows:
                row_index = i - start_row
                segments = []
                for block in opponent_blocks:
                    art_line = block["lines"][row_index] if row_index < len(block["lines"]) else ""
                    width = block["width"]
                    art_line = pad_ansi(art_line, width)
                    if art_line.strip():
                        segments.append(block["color"] + art_line + art_color)
                    else:
                        segments.append(" " * width)
                inter_pad = 2
                gap_pad = 2
                content = (" " * inter_pad).join(segments)
                visible_width = len(strip_ansi(content))
                content_width = (gap_pad * 2) + visible_width
                pad_left = 0
                pad_right = max(0, gap_width - content_width)
                gap_fill = (
                    (" " * pad_left)
                    + (" " * gap_pad)
                    + content
                    + (" " * gap_pad)
                    + (" " * pad_right)
                )
            art_lines.append(left_line + gap_fill + right_line)
        return art_lines, art_color
    forest_template = scene_data.get("art", [])
    forest_art = []
    for i, line in enumerate(forest_template):
        gap_fill = " " * gap_width
        if opponent_blocks:
            max_opp_rows = max((len(block["lines"]) for block in opponent_blocks), default=0)
            start_row = (len(forest_template) - max_opp_rows) // 2
            if start_row <= i < start_row + max_opp_rows:
                row_index = i - start_row
                segments = []
                for block in opponent_blocks:
                    art_line = block["lines"][row_index] if row_index < len(block["lines"]) else ""
                    width = block["width"]
                    art_line = pad_ansi(art_line, width)
                    if art_line.strip():
                        segments.append(block["color"] + art_line + art_color)
                    else:
                        segments.append(" " * width)
                inter_pad = 2
                gap_pad = 2
                content = (" " * inter_pad).join(segments)
                visible_width = len(strip_ansi(content))
                content_width = (gap_pad * 2) + visible_width
                gap_width = max(gap_width, content_width)
                pad_left = 0
                pad_right = max(0, gap_width - content_width)
                gap_fill = (
                    (" " * pad_left)
                    + (" " * gap_pad)
                    + content
                    + (" " * gap_pad)
                    + (" " * pad_right)
                )
        forest_art.append(line.replace("{GAP}", gap_fill))
    return forest_art, art_color


def compute_scene_gap_target(scene_data: dict, opponents: List[Opponent]) -> int:
    if not scene_data:
        return 0
    gap_base = (
        int(scene_data.get("gap_min", 2))
        if scene_data.get("left")
        else int(scene_data.get("gap_width", 20))
    )
    opponent_blocks = [m for m in opponents if m.art_lines]
    if not opponent_blocks:
        return gap_base
    widest_block = max(OPPONENT_ART_WIDTH, 0)
    blocks_width = widest_block * len(opponent_blocks)
    inter_pad = 2
    gap_pad = 2
    total = blocks_width + (inter_pad * max(0, len(opponent_blocks) - 1)) + (gap_pad * 2)
    return max(gap_base, total)


def render_scene_frame(
    scenes_data,
    commands_data,
    scene_id: str,
    player: Player,
    opponents: List[Opponent],
    message: str,
    gap_override: int,
    art_opponents: Optional[List[Opponent]] = None,
    flash_index: Optional[int] = None,
    flash_color: Optional[str] = None,
    visible_indices: Optional[set] = None,
    include_bars: bool = True,
    manual_lines_indices: Optional[set] = None,
    suppress_actions: bool = False,
    show_target_prompt: bool = False,
):
    scene_data = scenes_data.get(scene_id, {})
    art_lines, art_color = render_scene_art(
        scene_data,
        art_opponents if art_opponents is not None else opponents,
        gap_override=gap_override,
        flash_index=flash_index,
        flash_color=flash_color,
        visible_indices=visible_indices,
        include_bars=include_bars,
        manual_lines_indices=manual_lines_indices
    )
    alive = [o for o in opponents if o.hp > 0]
    if alive:
        if len(alive) > 1:
            body = ["Opponents emerge from the forest."]
        else:
            primary = alive[0]
            body = [f"A {primary.name} {primary.arrival}."]
    else:
        body = ["All is quiet. No enemies in sight."]
    if message:
        lines = [line for line in message.splitlines() if line.strip() != ""]
        if lines:
            body += lines
    commands = scene_commands(scenes_data, commands_data, scene_id, player, opponents)
    actions = format_action_lines(format_commands(commands))
    if suppress_actions:
        actions = format_action_lines([])
    frame = Frame(
        title="World Builder — PROTOTYPE",
        body_lines=body,
        action_lines=actions,
        stat_lines=format_player_stats(player),
        footer_hint="" if suppress_actions else "Keys: use the action panel",
        location=player.location,
        art_lines=art_lines,
        art_color=art_color,
        status_lines=["Select target (←/→, Enter)"] if show_target_prompt else [],
    )
    render_frame(frame)


def animate_scene_gap(
    scenes_data,
    commands_data,
    scene_id: str,
    player: Player,
    opponents: List[Opponent],
    message: str,
    start_gap: int,
    end_gap: int,
    steps: int = 6,
    delay: float = 0.06,
    art_opponents: Optional[List[Opponent]] = None
):
    if start_gap == end_gap or steps <= 0:
        return
    for step in range(1, steps + 1):
        t = step / steps
        gap = int(round(start_gap + (end_gap - start_gap) * t))
        render_scene_frame(
            scenes_data,
            commands_data,
            scene_id,
            player,
            opponents,
            message,
            gap,
            art_opponents,
            suppress_actions=True
        )
        time.sleep(delay)


def animate_battle_start(
    scenes_data,
    commands_data,
    scene_id: str,
    player: Player,
    opponents: List[Opponent],
    message: str
):
    if not opponents:
        return
    scene_data = scenes_data.get(scene_id, {})
    gap_base = (
        int(scene_data.get("gap_min", 2))
        if scene_data.get("left")
        else int(scene_data.get("gap_width", 20))
    )
    gap_target = compute_scene_gap_target(scene_data, opponents)
    animate_scene_gap(
        scenes_data,
        commands_data,
        scene_id,
        player,
        opponents,
        message,
        gap_base,
        gap_target,
        art_opponents=[]
    )


def animate_battle_end(
    scenes_data,
    commands_data,
    scene_id: str,
    player: Player,
    opponents: List[Opponent],
    message: str
):
    if not opponents:
        return
    scene_data = scenes_data.get(scene_id, {})
    gap_base = (
        int(scene_data.get("gap_min", 2))
        if scene_data.get("left")
        else int(scene_data.get("gap_width", 20))
    )
    gap_target = compute_scene_gap_target(scene_data, opponents)
    animate_scene_gap(
        scenes_data,
        commands_data,
        scene_id,
        player,
        opponents,
        message,
        gap_target,
        gap_base,
        art_opponents=[]
    )


def flash_opponent(
    scenes_data,
    commands_data,
    scene_id: str,
    player: Player,
    opponents: List[Opponent],
    message: str,
    index: Optional[int],
    flash_color: str
):
    if index is None:
        return
    scene_data = scenes_data.get(scene_id, {})
    gap_target = compute_scene_gap_target(scene_data, opponents)
    render_scene_frame(
        scenes_data,
        commands_data,
        scene_id,
        player,
        opponents,
        message,
        gap_target,
        flash_index=index,
        flash_color=flash_color,
        suppress_actions=True
    )
    time.sleep(max(0.08, battle_action_delay(player) / 2))


def melt_opponent(
    scenes_data,
    commands_data,
    scene_id: str,
    player: Player,
    opponents: List[Opponent],
    message: str,
    index: Optional[int]
):
    if index is None:
        return
    if index < 0 or index >= len(opponents):
        return
    opponent = opponents[index]
    if not opponent.art_lines:
        return
    width = OPPONENT_ART_WIDTH
    raw_lines = [line[:width].rstrip() for line in opponent.art_lines]
    max_len = max((len(line) for line in raw_lines), default=0)
    left_aligned = [line.ljust(max_len) for line in raw_lines]
    display_lines = [line.center(width) for line in left_aligned]
    scene_data = scenes_data.get(scene_id, {})
    gap_target = compute_scene_gap_target(scene_data, opponents)
    for removed in range(1, len(display_lines) + 1):
        trimmed = (
            [" " * width for _ in range(removed)]
            + display_lines[removed:]
        )
        art_overrides = []
        for i, current in enumerate(opponents):
            if i == index:
                art_overrides.append(replace(current, art_lines=trimmed, hp=0))
            else:
                art_overrides.append(current)
        render_scene_frame(
            scenes_data,
            commands_data,
            scene_id,
            player,
            opponents,
            message,
            gap_target,
            art_opponents=art_overrides,
            manual_lines_indices={index},
            suppress_actions=True
        )
        time.sleep(max(0.05, battle_action_delay(player) / 3))


def format_player_stats(player: Player) -> List[str]:
    hp_text = color(f"HP: {player.hp} / {player.max_hp}", ANSI.FG_GREEN)
    mp_text = color(f"MP: {player.mp} / {player.max_mp}", ANSI.FG_MAGENTA)
    atk_text = color(f"ATK: {player.atk}", ANSI.DIM)
    def_text = color(f"DEF: {player.defense}", ANSI.DIM)
    level_text = color(f"Level: {player.level}", ANSI.FG_CYAN)
    xp_text = color(f"XP: {player.xp}", ANSI.FG_GREEN)
    gp_text = color(f"GP: {player.gold}", ANSI.FG_YELLOW)
    return [
        f"{hp_text}  {mp_text}  {atk_text}  {def_text}",
        f"{level_text}    {xp_text}    {gp_text}",
    ]


def clear_screen():
    sys.stdout.write("\033[2J\033[H\033[3J")
    sys.stdout.flush()



def format_gradient_location_text(location: str) -> str:
    """Applies a gradient color effect to the location text and its embellishments."""
    left_embellishment = "*-----<{([  "
    right_embellishment = "  ])}>-----*"

    def _truecolor(r, g, b):
        return f"\033[38;2;{r};{g};{b}m"

    def _gradient(text, start_color, end_color):
        colored_text = ""
        n = len(text)
        for i, char in enumerate(text):
            r = int(start_color[0] + (end_color[0] - start_color[0]) * i / (n - 1))
            g = int(start_color[1] + (end_color[1] - start_color[1]) * i / (n - 1))
            b = int(start_color[2] + (end_color[2] - start_color[2]) * i / (n - 1))
            colored_text += f"{_truecolor(r, g, b)}{char}"
        return colored_text

    start_color = (192, 192, 192)
    end_color = (0, 0, 128)

    left_colored = _gradient(left_embellishment, start_color, end_color)
    right_colored = _gradient(right_embellishment, end_color, start_color)

    return f"{left_colored}{ANSI.FG_WHITE}{location}{right_colored}{ANSI.RESET}"


def render_frame(frame: Frame):
    clear_screen()

    border = color("+" + "-" * (SCREEN_WIDTH - 2) + "+", ANSI.FG_BLUE)
    print(border)

    gradient_location = format_gradient_location_text(frame.location)
    location_row = center_ansi(gradient_location, SCREEN_WIDTH - 2)



    used_rows = (
        1 +  # top border
        1 +  # location line
        1 +  # location separator border
        1 +  # actions separator border
        len(frame.action_lines) +
        1 +  # stat separator border
        STAT_LINES +
        1    # bottom border
    )
    body_height = SCREEN_HEIGHT - used_rows

    print(color(f"|{location_row}|", ANSI.FG_CYAN))
    print(border)

    status_lines = frame.status_lines[:]
    art_count = len(frame.art_lines)
    divider_count = 1 if art_count > 0 else 0
    max_status = max(0, body_height - art_count - divider_count)
    if len(status_lines) > max_status:
        status_lines = status_lines[-max_status:]
    status_count = len(status_lines)

    narrative_space = body_height - art_count - divider_count - status_count
    narrative_space = max(0, narrative_space)
    body_rows = []

    for i in range(art_count):
        art_line = frame.art_lines[i]
        styled = color(art_line, frame.art_color)
        body_rows.append(center_ansi(styled, SCREEN_WIDTH - 4))

    if art_count > 0:
        divider_row = "-" * (SCREEN_WIDTH - 4)
        body_rows.append(color(divider_row, ANSI.FG_BLUE))

    if frame.location == "Forest":
        visible_lines = frame.body_lines[-narrative_space:] if narrative_space > 0 else []
    else:
        visible_lines = frame.body_lines[:narrative_space]

    for i in range(narrative_space):
        raw = visible_lines[i] if i < len(visible_lines) else ""
        if raw:
            raw = (" " * NARRATIVE_INDENT) + raw
        body_rows.append(pad_or_trim_ansi(raw, SCREEN_WIDTH - 4))

    for line in status_lines:
        colored = color(line, ANSI.FG_YELLOW)
        body_rows.append(center_ansi(colored, SCREEN_WIDTH - 4))

    for i in range(body_height):
        line = body_rows[i] if i < len(body_rows) else ""
        print(
            color("| ", ANSI.FG_BLUE)
            + line
            + color(" |", ANSI.FG_BLUE)
        )

    actions_label = "---Actions---"
    actions_label_row = actions_label.center(SCREEN_WIDTH - 2, "-")
    print(color(f"+{actions_label_row}+", ANSI.FG_BLUE))

    for i in range(len(frame.action_lines)):
        line = frame.action_lines[i] if i < len(frame.action_lines) else ""
        print(
            color("| ", ANSI.FG_BLUE)
            + pad_or_trim_ansi(line, SCREEN_WIDTH - 4)
            + color(" |", ANSI.FG_BLUE)
        )

    stats_label = "---Player-Stats---"
    stats_label_row = stats_label.center(SCREEN_WIDTH - 2, "-")
    print(color(f"+{stats_label_row}+", ANSI.FG_BLUE))
    for i in range(STAT_LINES):
        raw = frame.stat_lines[i] if i < len(frame.stat_lines) else ""
        styled = raw
        if raw.startswith("HP:"):
            styled = color(raw, ANSI.FG_RED)
        elif raw.startswith("Level:"):
            styled = color(raw, ANSI.FG_YELLOW)
        elif raw.startswith("Name:"):
            styled = color(raw, ANSI.FG_GREEN, ANSI.BOLD)
        elif raw.startswith("Location:"):
            styled = color(raw, ANSI.FG_CYAN)

        centered = center_ansi(styled, SCREEN_WIDTH - 4)
        print(
            color("| ", ANSI.FG_BLUE)
            + centered
            + color(" |", ANSI.FG_BLUE)
        )

    print(border)


def format_opponent_bar(opponent: Opponent) -> str:
    if opponent.max_hp <= 0:
        ratio = 0
    else:
        ratio = max(0.0, min(1.0, opponent.hp / opponent.max_hp))
    filled = int(ratio * (OPPONENT_ART_WIDTH - 2))
    filled = max(0, min(OPPONENT_ART_WIDTH - 2, filled))
    bar = "#" * filled + "_" * ((OPPONENT_ART_WIDTH - 2) - filled)
    return (
        ANSI.FG_WHITE
        + "["
        + ANSI.FG_GREEN + ("#" * filled)
        + ANSI.FG_WHITE + ("_" * ((OPPONENT_ART_WIDTH - 2) - filled))
        + "]"
    )
