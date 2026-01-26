import os
import sys
import shutil
import random
import time
import json
import textwrap
from dataclasses import replace
from typing import List, Optional

from data_access.items_data import ItemsData
from data_access.opponents_data import OpponentsData
from data_access.scenes_data import ScenesData
from data_access.npcs_data import NpcsData
from data_access.venues_data import VenuesData
from data_access.save_data import SaveData
from models import Frame, Player, Opponent

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SAVE_PATH = os.path.join(os.path.dirname(__file__), "saves", "slot1.json")

SCREEN_WIDTH = 100
SCREEN_HEIGHT = 30
STAT_LINES = 2
ACTION_LINES = 3
NARRATIVE_INDENT = 2
OPPONENT_ART_WIDTH = 10
OPPONENT_BAR_WIDTH = 8

# -----------------------------
# ANSI color helpers (UI only)
# -----------------------------

class ANSI:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    FG_WHITE = "\033[37m"
    FG_CYAN = "\033[36m"
    FG_GREEN = "\033[32m"
    FG_YELLOW = "\033[33m"
    FG_RED = "\033[31m"
    FG_BLUE = "\033[34m"
    FG_MAGENTA = "\033[35m"


def color(text: str, *codes: str) -> str:
    return "".join(codes) + text + ANSI.RESET


def spawn_opponents(player_level: int) -> List[Opponent]:
    return OPPONENTS.spawn(player_level, ANSI.FG_CYAN)


def load_scene_data() -> dict:
    return SCENES.all()


def color_from_name(name: str) -> str:
    return {
        "white": ANSI.FG_WHITE,
        "cyan": ANSI.FG_CYAN,
        "green": ANSI.FG_GREEN,
        "yellow": ANSI.FG_YELLOW,
        "red": ANSI.FG_RED,
        "blue": ANSI.FG_BLUE,
    }.get(name.lower(), ANSI.FG_WHITE)


ITEMS = ItemsData(os.path.join(DATA_DIR, "items.json"))
OPPONENTS = OpponentsData(os.path.join(DATA_DIR, "opponents.json"))
SCENES = ScenesData(os.path.join(DATA_DIR, "scenes.json"))
NPCS = NpcsData(os.path.join(DATA_DIR, "npcs.json"))
VENUES = VenuesData(os.path.join(DATA_DIR, "venues.json"))
SAVE_DATA = SaveData(SAVE_PATH)


def load_npc_data() -> dict:
    return NPCS.all()


def load_venue_data() -> dict:
    return VENUES.all()


def render_venue_art(venue: dict, npc: dict) -> tuple[List[str], str]:
    art_template = venue.get("art", [])
    art_color = color_from_name(venue.get("color", "white"))
    npc_art = npc.get("art", [])
    npc_color = color_from_name(npc.get("color", "white"))
    gap_width = int(venue.get("gap_width", 0))

    if art_template:
        if gap_width > 0:
            art_lines = []
            start_row = (len(art_template) - len(npc_art)) // 2
            for i, line in enumerate(art_template):
                gap_fill = " " * gap_width
                if npc_art and start_row <= i < start_row + len(npc_art):
                    npc_line = npc_art[i - start_row]
                    pad_left = (gap_width - len(npc_line)) // 2
                    pad_right = gap_width - len(npc_line) - pad_left
                    gap_fill = (
                        (" " * pad_left)
                        + npc_color + npc_line + art_color
                        + (" " * pad_right)
                    )
                art_lines.append(line.replace("{GAP}", gap_fill))
            return art_lines, art_color
        return art_template, art_color
    if npc_art:
        return npc_art, npc_color
    return [], ANSI.FG_WHITE


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


def format_player_stats(player: Player) -> List[str]:
    hp_text = color(f"HP: {player.hp} / {player.max_hp}", ANSI.FG_GREEN)
    mp_text = color(f"MP: {player.mp} / {player.max_mp}", ANSI.FG_MAGENTA)
    atk_text = color(f"ATK: {player.atk}", ANSI.DIM)
    def_text = color(f"DEF: {player.defense}", ANSI.DIM)
    level_text = color(f"Level: {player.level}", ANSI.FG_CYAN)
    xp_text = color(f"XP: {player.xp}", ANSI.FG_GREEN)
    gp_text = color(f"GP: {player.gold}", ANSI.FG_YELLOW)
    return [
        f"{hp_text}    {mp_text}    {atk_text}    {def_text}",
        f"{level_text}    {xp_text}    {gp_text}",
    ]


def format_opponent_bar(opponent: Opponent) -> str:
    if opponent.max_hp <= 0:
        filled = 0
    else:
        filled = int((opponent.hp / opponent.max_hp) * OPPONENT_BAR_WIDTH)
    filled = max(0, min(OPPONENT_BAR_WIDTH, filled))
    hashes = "#" * filled
    empties = "_" * (OPPONENT_BAR_WIDTH - filled)
    return (
        ANSI.FG_WHITE
        + "["
        + ANSI.FG_GREEN + hashes
        + ANSI.FG_WHITE + empties
        + "]"
    )


def build_opponent_blocks(
    opponents: List[Opponent],
    flash_index: Optional[int] = None,
    flash_color: Optional[str] = None,
    visible_indices: Optional[set] = None,
    include_bars: bool = True,
    manual_lines_indices: Optional[set] = None
) -> List[dict]:
    blocks = []
    if visible_indices is None:
        visible_indices = set()
    if manual_lines_indices is None:
        manual_lines_indices = set()
    for idx, opponent in enumerate(opponents[:3]):
        if not opponent.art_lines:
            continue
        width = OPPONENT_ART_WIDTH
        bar = format_opponent_bar(opponent)
        if idx in manual_lines_indices:
            lines = opponent.art_lines
            color = opponent.art_color
        elif opponent.hp > 0 or idx in visible_indices:
            lines = [line[:width].center(width) for line in opponent.art_lines]
            if include_bars:
                lines.append(" " * width)
                lines.append(bar)
            color = opponent.art_color
            if flash_color and flash_index == idx:
                color = flash_color
        else:
            lines = [" " * width for _ in opponent.art_lines]
            if include_bars:
                lines.append(" " * width)
                lines.append(" " * width)
            color = opponent.art_color
        blocks.append(
            {
                "lines": lines,
                "width": width,
                "color": color,
            }
        )
    return blocks


def compute_forest_gap_target(scene_data: dict, opponents: List[Opponent]) -> int:
    gap_min = int(scene_data.get("gap_min", 2))
    gap_width = int(scene_data.get("gap_width", gap_min))
    left = scene_data.get("left", [])
    opponent_blocks = build_opponent_blocks(opponents)
    if not opponent_blocks:
        return gap_min if left else gap_width
    gap_pad = 2
    inter_pad = 2
    content_width = (
        (gap_pad * 2)
        + sum(block["width"] for block in opponent_blocks)
        + (inter_pad * (len(opponent_blocks) - 1))
    )
    if left:
        return max(gap_min, content_width)
    return max(gap_width, content_width)


def battle_action_delay(player: Player) -> float:
    speeds = {
        "fast": 0.2,
        "normal": 0.45,
        "slow": 0.75,
    }
    return speeds.get(player.battle_speed, speeds["normal"])


def render_forest_art(
    scene_data: dict,
    opponents: List[Opponent],
    gap_override: Optional[int] = None,
    flash_index: Optional[int] = None,
    flash_color: Optional[str] = None,
    visible_indices: Optional[set] = None,
    include_bars: bool = True,
    manual_lines_indices: Optional[set] = None
) -> tuple[List[str], str]:
    art_color = color_from_name(scene_data.get("color", "green"))
    opponent_blocks = build_opponent_blocks(
        opponents,
        flash_index=flash_index,
        flash_color=flash_color,
        visible_indices=visible_indices,
        include_bars=include_bars,
        manual_lines_indices=manual_lines_indices
    )
    left = scene_data.get("left", [])
    right = scene_data.get("right")

    if left:
        if right is None:
            right = [mirror_line(line) for line in left]
        gap_min = int(scene_data.get("gap_min", 2))
        if gap_override is not None:
            gap_min = gap_override
        gap_pad = 2
        inter_pad = 2
        gap_width = gap_min
        if opponent_blocks:
            content_width = (
                (gap_pad * 2)
                + sum(block["width"] for block in opponent_blocks)
                + (inter_pad * (len(opponent_blocks) - 1))
            )
            gap_width = max(gap_min, content_width)
        art_lines = []
        max_rows = max(len(left), len(right))
        max_opp_rows = max((len(block["lines"]) for block in opponent_blocks), default=0)
        start_row = (max_rows - max_opp_rows) // 2 if max_opp_rows else 0
        for i in range(max_rows):
            left_line = left[i] if i < len(left) else ""
            right_line = right[i] if i < len(right) else ""
            gap_fill = " " * gap_width
            if opponent_blocks and start_row <= i < start_row + max_opp_rows:
                row_index = i - start_row
                segments = []
                for block in opponent_blocks:
                    line = block["lines"][row_index] if row_index < len(block["lines"]) else ""
                    line = line.ljust(block["width"])
                    if line.strip():
                        segments.append(block["color"] + line + art_color)
                    else:
                        segments.append(" " * block["width"])
                content = (" " * inter_pad).join(segments)
                content_width = (gap_pad * 2) + len(content)
                pad_left = max(0, (gap_width - content_width) // 2)
                pad_right = max(0, gap_width - content_width - pad_left)
                gap_fill = (
                    (" " * pad_left)
                    + (" " * gap_pad)
                    + content
                    + (" " * gap_pad)
                    + (" " * pad_right)
                )
            art_lines.append(left_line + gap_fill + right_line)
        return art_lines, art_color

        gap_width = int(scene_data.get("gap_width", 20))
        if gap_override is not None:
            gap_width = gap_override
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
                    line = block["lines"][row_index] if row_index < len(block["lines"]) else ""
                    width = block["width"]
                    line = line.ljust(width)
                    if line.strip():
                        segments.append(block["color"] + line + art_color)
                    else:
                        segments.append(" " * width)
                inter_pad = 2
                gap_pad = 2
                content = (" " * inter_pad).join(segments)
                content_width = (gap_pad * 2) + len(content)
                gap_width = max(gap_width, content_width)
                pad_left = max(0, (gap_width - content_width) // 2)
                pad_right = max(0, gap_width - content_width - pad_left)
                gap_fill = (
                    (" " * pad_left)
                    + (" " * gap_pad)
                    + content
                    + (" " * gap_pad)
                    + (" " * pad_right)
                )
        forest_art.append(line.replace("{GAP}", gap_fill))
    return forest_art, art_color


def has_save() -> bool:
    return SAVE_DATA.exists()


def delete_save():
    SAVE_DATA.delete()


def new_player() -> Player:
    return Player(
        name="WARRIOR",
        level=1,
        xp=0,
        stat_points=0,
        gold=10,
        battle_speed="normal",
        hp=10,
        max_hp=10,
        mp=10,
        max_mp=10,
        atk=10,
        defense=10,
        location="Town",
        inventory={},
    )


def format_action_lines(actions: List[str]) -> List[str]:
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


def format_inventory(player: Player) -> str:
    return player.format_inventory(ITEMS)


def purchase_item(player: Player, key: str) -> str:
    item = ITEMS.get(key)
    if not item:
        return "That item is not available."
    price = int(item.get("price", 0))
    if player.gold < price:
        return "Not enough GP."
    player.gold -= price
    player.add_item(key, 1)
    return f"Purchased {item.get('name', key)}."


def list_inventory_items(player: Player) -> List[tuple[str, str]]:
    return player.list_inventory_items(ITEMS)


def use_item(player: Player, key: str) -> str:
    return player.use_item(key, ITEMS)


def list_opponent_descriptions() -> List[str]:
    return OPPONENTS.list_descriptions()


def list_item_descriptions() -> List[str]:
    return ITEMS.list_descriptions()


def grant_xp(player: Player, amount: int) -> int:
    player.xp += amount
    levels_gained = 0
    while player.xp >= player.level * 50:
        player.level += 1
        player.stat_points += 10
        levels_gained += 1
    return levels_gained


def generate_demo_frame(
    player: Player,
    opponents: List[Opponent],
    message: str = "",
    leveling_mode: bool = False,
    shop_mode: bool = False,
    inventory_mode: bool = False,
    inventory_items: Optional[List[tuple[str, str]]] = None,
    hall_mode: bool = False,
    hall_view: str = "menu",
    spell_mode: bool = False
) -> Frame:
    if leveling_mode:
        body = [
            "Level Up!",
            "",
            f"You reached level {player.level}.",
            "",
            f"Stat points available: {player.stat_points}",
            "",
            "Choose how to spend your points:",
            "  [1] +HP",
            "  [2] +MP",
            "  [3] +ATK",
            "  [4] +DEF",
            "",
            "  [B] Balanced allocation",
            "  [X] Random allocation",
        ]
        actions = format_action_lines([])
        art_lines = []
        art_color = ANSI.FG_WHITE
    elif player.location == "Town" and shop_mode:
        rations = ITEMS.get("rations", {})
        elixir = ITEMS.get("elixir", {})
        venue = load_venue_data().get("town_shop", {})
        npc_lines = []
        npc_ids = venue.get("npc_ids", [])
        npc = {}
        if npc_ids:
            npc_lines = NPCS.format_greeting(npc_ids[0])
            npc = load_npc_data().get(npc_ids[0], {})
        body = []
        if npc_lines:
            body += npc_lines + [""]
        body += [
            f"Rations (+5 HP/MP)  {rations.get('price', 0)} GP",
            f"Elixir (+20 HP/MP)  {elixir.get('price', 0)} GP",
            "",
            "Choose an item to purchase.",
        ]
        art_lines, art_color = render_venue_art(venue, npc)
        actions = [
            "  [1] Buy Rations",
            "  [2] Buy Elixir",
            "  [B] Back",
            "  [Q] Quit",
        ]
        actions = format_action_lines(actions)
    elif player.location == "Town" and hall_mode:
        venue = load_venue_data().get("town_hall", {})
        npc_lines = []
        npc_ids = venue.get("npc_ids", [])
        npc = {}
        if npc_ids:
            npc_lines = NPCS.format_greeting(npc_ids[0])
            npc = load_npc_data().get(npc_ids[0], {})
        if hall_view == "items":
            info_lines = list_item_descriptions()
        elif hall_view == "opponents":
            info_lines = list_opponent_descriptions()
        else:
            info_lines = []
        body = []
        if npc_lines:
            body += npc_lines + [""]
        body += info_lines
        actions = [
            "  [1] Opponents",
            "  [2] Items",
            "  [B] Back",
            "  [Q] Quit",
        ]
        actions = format_action_lines(actions)
        art_lines, art_color = render_venue_art(venue, npc)
    elif inventory_mode:
        items = inventory_items or []
        body = ["Inventory", ""]
        if items:
            for i, (_, label) in enumerate(items[:9], start=1):
                body.append(f"{i}. {label}")
        else:
            body.append("Inventory is empty.")
        actions = [
            "  [1-9] Use item",
            "  [B] Back",
            "  [Q] Quit",
        ]
        actions = format_action_lines(actions)
        art_lines = []
        art_color = ANSI.FG_WHITE
    elif spell_mode:
        body = ["Spellbook", "", "Healing (2 MP)", "Spark (2 MP)"]
        actions = [
            "  [1] Healing",
            "  [2] Spark",
            "  [B] Back",
            "  [Q] Quit",
        ]
        actions = format_action_lines(actions)
        art_lines = []
        art_color = ANSI.FG_WHITE
    elif player.location == "Town":
        scene_data = load_scene_data().get("town", {})
        art_lines = scene_data.get("art", [])
        art_color = color_from_name(scene_data.get("color", "yellow"))
        body = [
            "You arrive in town, safe behind sturdy wooden walls.",
            "",
            "The inn's lantern glows warmly in the evening light.",
            "A local shop can provide you with basic items.",
            "If you are lost, check the town hall for instructions."
        ]
        actions = [
            "  [F] Set out for the Forrest",
            "  [S] Shop",
            "  [H] Hall",
        ]
        if player.hp < player.max_hp or player.mp < player.max_mp:
            actions.insert(0, "  [I] Inn (Rest, 10 GP)")
        actions += [
            "  [O] Open inventory",
            "  [Q] Quit",
        ]
        actions = format_action_lines(actions)
    else:
        scene_data = load_scene_data().get("forest", {})
        forest_art, art_color = render_forest_art(scene_data, opponents)
        opponent_lines = []
        for i, m in enumerate(opponents[:3], start=1):
            line = f"{i}) {m.name} L{m.level} HP {m.hp}/{m.max_hp} ATK {m.atk} DEF {m.defense}"
            if m.stunned_turns > 0:
                line += f" (Stun {m.stunned_turns})"
            opponent_lines.append(line)
        primary = primary_opponent(opponents)
        body = [
            (
                f"A {primary.name} {primary.arrival}."
                if primary
                else "All is quiet. No enemies in sight."
            ),
            "",
            *opponent_lines,
        ]
        if primary:
            actions = [
                f"  [A] Attack the {primary.name.lower()}",
            ]
            actions += [
                "  [M] Magic",
                "  [O] Open inventory",
                "  [T] Return to Town",
                "  [Q] Quit",
            ]
        else:
            actions = [
                "  [F] Find an opponent to fight",
            ]
            actions += [
                "  [M] Magic",
                "  [O] Open inventory",
                "  [T] Return to Town",
                "  [Q] Quit",
            ]
        actions = format_action_lines(actions)
        art_lines = forest_art

    status_lines = (
        textwrap.wrap(message, width=SCREEN_WIDTH - 4)
        if message
        else []
    )

    stats = format_player_stats(player)

    return Frame(
        title="World Builder — PROTOTYPE",
        body_lines=body,
        action_lines=actions,
        stat_lines=stats,
        footer_hint=(
            "Keys: 1-4=Assign  B=Balanced  X=Random  Q=Quit"
            if leveling_mode
            else (
                "Keys: A=Attack  H=Heal  S=Spark  I=Inventory  "
                "R=Rest  N=Next  T=Town  F=Forrest  Q=Quit"
            )
        ),
        location=player.location,
        art_lines=art_lines,
        art_color=art_color,
        status_lines=status_lines,
    )


def roll_damage(attacker_atk: int, defender_def: int) -> tuple[int, bool, bool]:
    base = max(1, attacker_atk - defender_def)
    low = max(1, base - 2)
    high = base + 2
    if random.random() < 0.05:
        return 0, False, True
    damage = random.randint(low, high)
    crit = random.random() < 0.10
    if crit:
        damage *= 2
    return damage, crit, False


def apply_stat_point(player: Player, stat: str):
    if stat == "HP":
        player.max_hp += 1
        player.hp += 1
    elif stat == "MP":
        player.max_mp += 1
        player.mp += 1
    elif stat == "ATK":
        player.atk += 1
    elif stat == "DEF":
        player.defense += 1


def allocate_balanced(player: Player):
    points = player.stat_points
    if points <= 0:
        return
    per_stat = points // 4
    remainder = points % 4
    if per_stat > 0:
        player.max_hp += per_stat
        player.hp += per_stat
        player.max_mp += per_stat
        player.mp += per_stat
        player.atk += per_stat
        player.defense += per_stat
    for stat in ["HP", "MP", "ATK", "DEF"][:remainder]:
        apply_stat_point(player, stat)
    player.stat_points = 0


def allocate_random(player: Player):
    stats = ["HP", "MP", "ATK", "DEF"]
    while player.stat_points > 0:
        apply_stat_point(player, random.choice(stats))
        player.stat_points -= 1


def try_stun(opponent: Opponent, chance: float) -> int:
    if random.random() < chance:
        turns = random.randint(1, 3)
        opponent.stunned_turns = max(opponent.stunned_turns, turns)
        return turns
    return 0


def alive_opponents(opponents: List[Opponent]) -> List[Opponent]:
    return [opponent for opponent in opponents if opponent.hp > 0]


def primary_opponent(opponents: List[Opponent]) -> Optional[Opponent]:
    for opponent in opponents:
        if opponent.hp > 0:
            return opponent
    return None


def add_loot(loot: dict, xp: int, gold: int):
    loot["xp"] = loot.get("xp", 0) + xp
    loot["gold"] = loot.get("gold", 0) + gold


def cast_spark(
    player: Player,
    opponents: List[Opponent],
    boosted: bool,
    loot: dict
) -> str:
    opponent = primary_opponent(opponents)
    if not opponent:
        return "There is nothing to target."
    mp_cost = 4 if boosted else 2
    if player.mp < mp_cost:
        return "Not enough MP to cast Spark."
    player.mp -= mp_cost
    damage, crit, miss = roll_damage(player.atk + 2, opponent.defense)
    if boosted:
        damage *= 2
    if miss:
        return f"Your Spark misses the {opponent.name}."
    opponent.hp = max(0, opponent.hp - damage)
    if opponent.hp == 0:
        xp_gain = random.randint(opponent.max_hp // 2, opponent.max_hp)
        gold_gain = random.randint(opponent.max_hp // 2, opponent.max_hp)
        add_loot(loot, xp_gain, gold_gain)
        opponent.melted = False
        message = (
            f"Your Spark fells the {opponent.name}."
        )
        return message
    stun_chance = 0.80 if boosted else 0.40
    stunned_turns = try_stun(opponent, stun_chance)
    if crit:
        message = f"Critical Spark! You hit the {opponent.name} for {damage}."
    else:
        message = f"You hit the {opponent.name} with Spark for {damage}."
    if stunned_turns > 0:
        message += f" It is stunned for {stunned_turns} turn(s)."
    return message


def cast_heal(player: Player, boosted: bool) -> str:
    mp_cost = 4 if boosted else 2
    if player.mp < mp_cost:
        return "Not enough MP to cast Healing."
    if player.hp == player.max_hp:
        return "Your HP is already full."
    player.mp -= mp_cost
    heal_amount = 20 if boosted else 10
    heal = min(heal_amount, player.max_hp - player.hp)
    player.hp += heal
    return f"You cast Healing and restore {heal} HP."


def apply_command(
    command: str,
    player: Player,
    opponents: List[Opponent],
    loot: dict
) -> str:
    # Placeholder for real game logic: return a message to display.
    if command == "ATTACK":
        opponent = primary_opponent(opponents)
        if not opponent:
            return "There is nothing to attack."
        damage, crit, miss = roll_damage(player.atk, opponent.defense)
        if miss:
            return f"You miss the {opponent.name}."
        opponent.hp = max(0, opponent.hp - damage)
        if opponent.hp == 0:
            xp_gain = random.randint(opponent.max_hp // 2, opponent.max_hp)
            gold_gain = random.randint(opponent.max_hp // 2, opponent.max_hp)
            add_loot(loot, xp_gain, gold_gain)
            opponent.melted = False
            message = (
                f"You strike down the {opponent.name}."
            )
            return message
        if crit:
            return f"Critical hit! You hit the {opponent.name} for {damage}."
        return f"You hit the {opponent.name} for {damage}."
    if command == "HEAL":
        return cast_heal(player, boosted=False)
    if command == "INVENTORY":
        return format_inventory(player)
    if command == "SPARK":
        return cast_spark(player, opponents, boosted=False, loot=loot)
    return "Unknown action."


# -----------------------------
# UI / Renderer
# -----------------------------

def clear_screen():
    sys.stdout.write("\033[2J\033[H\033[3J")
    sys.stdout.flush()


def pad_or_trim(text: str, width: int) -> str:
    return text[:width].ljust(width)


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
    total_padding = width - visible_len
    left = total_padding // 2
    right = total_padding - left
    return (" " * left) + text + (" " * right)


def render_frame(frame: Frame):
    clear_screen()

    border = color("+" + "-" * (SCREEN_WIDTH - 2) + "+", ANSI.FG_BLUE)

    print(border)

    location_line = f" {frame.location} "
    location_row = location_line.center(SCREEN_WIDTH - 2, " ")

    used_rows = (
        1 +  # top border
        1 +  # location line
        1 +  # location separator border
        1 +  # actions separator border
        ACTION_LINES +
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

    narrative_index = 0
    for i in range(narrative_space):
        raw = (
            frame.body_lines[narrative_index]
            if narrative_index < len(frame.body_lines)
            else ""
        )
        narrative_index += 1
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

    for i in range(ACTION_LINES):
        line = frame.action_lines[i] if i < len(frame.action_lines) else ""
        print(
            color("| ", ANSI.FG_BLUE)
            + pad_or_trim_ansi(line, SCREEN_WIDTH - 4)
            + color(" |", ANSI.FG_BLUE)
        )

    label = "---Player-Stats---"
    label_row = label.center(SCREEN_WIDTH - 2, "-")
    print(color(f"+{label_row}+", ANSI.FG_BLUE))

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


def render_forest_frame(
    player: Player,
    opponents: List[Opponent],
    message: str,
    gap_override: int,
    art_opponents: Optional[List[Opponent]] = None,
    flash_index: Optional[int] = None,
    flash_color: Optional[str] = None,
    visible_indices: Optional[set] = None,
    include_bars: bool = True,
    manual_lines_indices: Optional[set] = None
):
    scene_data = load_scene_data().get("forest", {})
    forest_art, art_color = render_forest_art(
        scene_data,
        art_opponents if art_opponents is not None else opponents,
        gap_override=gap_override,
        flash_index=flash_index,
        flash_color=flash_color,
        visible_indices=visible_indices,
        include_bars=include_bars,
        manual_lines_indices=manual_lines_indices
    )
    opponent_lines = []
    for i, m in enumerate(opponents[:3], start=1):
        line = f"{i}) {m.name} L{m.level} HP {m.hp}/{m.max_hp} ATK {m.atk} DEF {m.defense}"
        if m.stunned_turns > 0:
            line += f" (Stun {m.stunned_turns})"
        opponent_lines.append(line)
    primary = primary_opponent(opponents)
    body = [
        (
            f"A {primary.name} {primary.arrival}."
            if primary
            else "All is quiet. No enemies in sight."
        ),
        "",
        *opponent_lines,
    ]
    if primary:
        actions = [
            f"  [A] Attack the {primary.name.lower()}",
        ]
        actions += [
            "  [M] Magic",
            "  [O] Open inventory",
            "  [T] Return to Town",
            "  [Q] Quit",
        ]
    else:
        actions = [
            "  [F] Find an opponent to fight",
        ]
        actions += [
            "  [M] Magic",
            "  [O] Open inventory",
            "  [T] Return to Town",
            "  [Q] Quit",
        ]
    frame = Frame(
        title="World Builder — PROTOTYPE",
        body_lines=body,
        action_lines=format_action_lines(actions),
        stat_lines=format_player_stats(player),
        footer_hint=(
            "Keys: A=Attack  H=Heal  S=Spark  I=Inventory  "
            "R=Rest  N=Next  T=Town  F=Forrest  Q=Quit"
        ),
        location=player.location,
        art_lines=forest_art,
        art_color=art_color,
        status_lines=(
            textwrap.wrap(message, width=SCREEN_WIDTH - 4)
            if message
            else []
        ),
    )
    render_frame(frame)


def animate_forest_gap(
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
        render_forest_frame(player, opponents, message, gap, art_opponents)
        time.sleep(delay)


def animate_battle_start(player: Player, opponents: List[Opponent], message: str):
    if player.location != "Forrest" or not opponents:
        return
    scene_data = load_scene_data().get("forest", {})
    gap_base = (
        int(scene_data.get("gap_min", 2))
        if scene_data.get("left")
        else int(scene_data.get("gap_width", 20))
    )
    gap_target = compute_forest_gap_target(scene_data, opponents)
    animate_forest_gap(player, opponents, message, gap_base, gap_target, art_opponents=[])


def animate_battle_end(player: Player, opponents: List[Opponent], message: str):
    if player.location != "Forrest" or not opponents:
        return
    scene_data = load_scene_data().get("forest", {})
    gap_base = (
        int(scene_data.get("gap_min", 2))
        if scene_data.get("left")
        else int(scene_data.get("gap_width", 20))
    )
    gap_target = compute_forest_gap_target(scene_data, opponents)
    animate_forest_gap(player, opponents, message, gap_target, gap_base, art_opponents=[])


def primary_opponent_index(opponents: List[Opponent]) -> Optional[int]:
    for idx, opponent in enumerate(opponents):
        if opponent.hp > 0:
            return idx
    return None


def flash_opponent(
    player: Player,
    opponents: List[Opponent],
    message: str,
    index: Optional[int],
    flash_color: str
):
    if index is None or player.location != "Forrest":
        return
    scene_data = load_scene_data().get("forest", {})
    gap_target = compute_forest_gap_target(scene_data, opponents)
    render_forest_frame(
        player,
        opponents,
        message,
        gap_target,
        flash_index=index,
        flash_color=flash_color
    )
    time.sleep(max(0.08, battle_action_delay(player) / 2))


def melt_opponent(
    player: Player,
    opponents: List[Opponent],
    message: str,
    index: Optional[int]
):
    if index is None or player.location != "Forrest":
        return
    if index < 0 or index >= len(opponents):
        return
    opponent = opponents[index]
    if not opponent.art_lines:
        return
    width = OPPONENT_ART_WIDTH
    bar = format_opponent_bar(opponent)
    display_lines = [line[:width].center(width) for line in opponent.art_lines]
    display_lines.append(" " * width)
    display_lines.append(bar)
    scene_data = load_scene_data().get("forest", {})
    gap_target = compute_forest_gap_target(scene_data, opponents)
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
        render_forest_frame(
            player,
            opponents,
            message,
            gap_target,
            art_opponents=art_overrides,
            visible_indices={index},
            manual_lines_indices={index}
        )
        time.sleep(max(0.05, battle_action_delay(player) / 3))


# -----------------------------
# Single-key input (macOS/Linux)
# -----------------------------

def read_keypress() -> str:
    """
    Read a single keypress without requiring Enter (POSIX terminals).
    Returns a single-character string.
    """
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):
            msvcrt.getch()
            return ""
        try:
            return ch.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    else:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)  # cbreak: immediate input, but still handles signals
            ch = sys.stdin.read(1)
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def map_key_to_command(ch: str) -> Optional[str]:
    c = ch.lower()
    if c == "1":
        return "NUM1"
    if c == "2":
        return "NUM2"
    if c == "3":
        return "NUM3"
    if c == "4":
        return "NUM4"
    if c == "5":
        return "NUM5"
    if c == "6":
        return "NUM6"
    if c == "7":
        return "NUM7"
    if c == "8":
        return "NUM8"
    if c == "9":
        return "NUM9"
    if c == "a":
        return "ATTACK"
    if c == "b":
        return "B_KEY"
    if c == "i":
        return "REST"
    if c == "o":
        return "INVENTORY"
    if c == "s":
        return "S_KEY"
    if c == "t":
        return "TOWN"
    if c == "f":
        return "F_KEY"
    if c == "h":
        return "HALL"
    if c == "m":
        return "SPELLBOOK"
    if c == "p":
        return "SPELLBOOK"
    if c == "x":
        return "X_KEY"
    if c == "q":
        return "QUIT"
    return None


# -----------------------------
# Main loop
# -----------------------------

def main():
    cols, rows = shutil.get_terminal_size(fallback=(0, 0))
    if cols < SCREEN_WIDTH or rows < SCREEN_HEIGHT:
        print(f"WARNING: Terminal size is {cols}x{rows}. Recommended is 100x30.")
        print("Resize your terminal for best results.")
        input("Press Enter to continue anyway...")

    player = new_player()
    opponents: List[Opponent] = []
    loot_bank = {"xp": 0, "gold": 0}

    last_message = ""
    leveling_mode = False
    boost_prompt: Optional[str] = None
    shop_mode = False
    inventory_mode = False
    inventory_items: List[tuple[str, str]] = []
    hall_mode = False
    hall_view = "menu"
    spell_mode = False
    quit_confirm = False
    title_mode = True
    title_confirm = False
    while True:
        if title_mode:
            title_scene = load_scene_data().get("title", {})
            title_art = title_scene.get("art", [])
            title_color = color_from_name(title_scene.get("color", "cyan"))
            if title_confirm:
                title_body = [
                    "World Builder",
                    "",
                    "Overwrite existing save?",
                    "",
                    "[Y] Yes, start new",
                    "[N] No, go back",
                ]
            elif has_save():
                title_body = [
                    "World Builder",
                    "",
                    "A modular engine for world creation",
                ]
            else:
                title_body = [
                    "World Builder",
                    "",
                    "A modular engine for world creation",
                ]
            if title_confirm:
                actions = [
                    "  [Y] Yes, start new",
                    "  [N] No, go back",
                    "  [Q] Quit",
                ]
            elif has_save():
                actions = [
                    "  [C] Continue",
                    "  [N] New Game",
                    "  [Q] Quit",
                ]
            else:
                actions = [
                    "  [N] New Game",
                    "  [Q] Quit",
                ]

            if has_save():
                saved_player = SAVE_DATA.load_player()
                if saved_player:
                    hp_text = color(
                        f"HP: {saved_player.hp} / {saved_player.max_hp}",
                        ANSI.FG_GREEN
                    )
                    mp_text = color(
                        f"MP: {saved_player.mp} / {saved_player.max_mp}",
                        ANSI.FG_MAGENTA
                    )
                    atk_text = color(f"ATK: {saved_player.atk}", ANSI.DIM)
                    def_text = color(f"DEF: {saved_player.defense}", ANSI.DIM)
                    stats = [
                        f"{hp_text}  {mp_text}  {atk_text}  {def_text}",
                        (
                            f"Level: {saved_player.level}  XP: {saved_player.xp}  "
                            f"GP: {saved_player.gold}"
                        ),
                    ]
                else:
                    stats = ["", ""]
            else:
                stats = ["", ""]

            frame = Frame(
                title="World Builder — PROTOTYPE",
                body_lines=title_body,
                action_lines=format_action_lines(actions),
                stat_lines=stats,
                footer_hint="",
                location="World Builder",
                art_lines=title_art,
                art_color=title_color,
                status_lines=[],
            )
        else:
            if inventory_mode:
                inventory_items = list_inventory_items(player)
            frame = generate_demo_frame(
                player,
                opponents,
                last_message,
                leveling_mode,
                shop_mode,
                inventory_mode,
                inventory_items,
                hall_mode,
                hall_view,
                spell_mode
            )
        render_frame(frame)

        ch = read_keypress()
        if quit_confirm:
            if ch.lower() == "y":
                SAVE_DATA.save_player(player)
                clear_screen()
                print("Goodbye.")
                return
            if ch.lower() == "n":
                quit_confirm = False
                last_message = "Quit cancelled."
                continue
            last_message = "Quit? (Y/N)"
            continue
        if title_mode:
            if title_confirm:
                if ch.lower() == "y":
                    delete_save()
                    player = new_player()
                    opponents = []
                    loot_bank = {"xp": 0, "gold": 0}
                    title_mode = False
                    title_confirm = False
                    last_message = "You arrive in town."
                    continue
                if ch.lower() == "n":
                    title_confirm = False
                    continue
                if ch.lower() == "q":
                    clear_screen()
                    print("Goodbye.")
                    return
                last_message = "Choose Y to confirm or N to cancel."
                continue
            if ch.lower() == "c" and has_save():
                loaded = SAVE_DATA.load_player()
                if loaded:
                    player = loaded
                else:
                    player = new_player()
            elif ch.lower() == "n":
                if has_save():
                    title_confirm = True
                    continue
                player = new_player()
            elif ch.lower() == "q":
                clear_screen()
                print("Goodbye.")
                return
            else:
                last_message = "Choose C to continue, N for a new game, or Q to quit."
                continue
            opponents = []
            loot_bank = {"xp": 0, "gold": 0}
            player.location = "Town"
            title_mode = False
            shop_mode = False
            inventory_mode = False
            hall_mode = False
            spell_mode = False
            last_message = "You arrive in town."
            continue
        action_cmd = None
        handled_boost = False
        if boost_prompt:
            if ch.lower() == "y":
                boosted = True
            elif ch.lower() == "n":
                boosted = False
            else:
                last_message = "Choose Y or N to boost the spell."
                continue

            if boost_prompt == "HEAL":
                last_message = cast_heal(player, boosted)
                action_cmd = "HEAL"
            else:
                last_message = cast_spark(player, opponents, boosted, loot=loot_bank)
                action_cmd = "SPARK"
            boost_prompt = None
            handled_boost = True

        if not handled_boost:
            cmd = map_key_to_command(ch)
        else:
            cmd = None

        if cmd == "QUIT":
            quit_confirm = True
            last_message = "Quit? (Y/N)"
            continue

        if cmd is None and not handled_boost:
            continue

        if leveling_mode and not handled_boost:
            if cmd == "B_KEY":
                allocate_balanced(player)
                last_message = "Balanced allocation complete."
            elif cmd == "X_KEY":
                allocate_random(player)
                last_message = "Random allocation complete."
            elif cmd in ("NUM1", "NUM2", "NUM3", "NUM4"):
                if player.stat_points <= 0:
                    last_message = "No stat points to spend."
                else:
                    player.stat_points -= 1
                    if cmd == "NUM1":
                        apply_stat_point(player, "HP")
                        last_message = "HP increased by 1."
                    elif cmd == "NUM2":
                        apply_stat_point(player, "MP")
                        last_message = "MP increased by 1."
                    elif cmd == "NUM3":
                        apply_stat_point(player, "ATK")
                        last_message = "ATK increased by 1."
                    else:
                        apply_stat_point(player, "DEF")
                        last_message = "DEF increased by 1."
            else:
                last_message = "Spend all stat points to continue."

            if player.stat_points == 0:
                leveling_mode = False
                player.hp = player.max_hp
                player.mp = player.max_mp
                last_message = "Level up complete."
            continue

        if inventory_mode and not handled_boost:
            if cmd == "B_KEY":
                inventory_mode = False
                last_message = "Closed inventory."
            elif cmd and cmd.startswith("NUM"):
                idx = int(cmd.replace("NUM", "")) - 1
                if 0 <= idx < len(inventory_items):
                    key, _ = inventory_items[idx]
                    last_message = use_item(player, key)
                    SAVE_DATA.save_player(player)
                    inventory_items = list_inventory_items(player)
                    if not inventory_items:
                        inventory_mode = False
                else:
                    last_message = "Invalid item selection."
            continue

        if spell_mode and not handled_boost:
            if cmd == "B_KEY":
                spell_mode = False
                last_message = "Closed spellbook."
            elif cmd == "NUM1":
                spell_mode = False
                cmd = "HEAL"
            elif cmd == "NUM2":
                spell_mode = False
                cmd = "SPARK"
            else:
                continue

        if hall_mode and not handled_boost:
            if cmd == "B_KEY":
                hall_mode = False
                last_message = "You leave the hall."
            elif cmd == "NUM1":
                hall_view = "opponents"
                last_message = "Viewing opponent info."
            elif cmd == "NUM2":
                hall_view = "items"
                last_message = "Viewing item info."
            continue

        if shop_mode and not handled_boost:
            if cmd == "B_KEY":
                shop_mode = False
                last_message = "You leave the shop."
            elif cmd == "NUM1":
                last_message = purchase_item(player, "rations")
                SAVE_DATA.save_player(player)
            elif cmd == "NUM2":
                last_message = purchase_item(player, "elixir")
                SAVE_DATA.save_player(player)
            continue

        if cmd == "B_KEY":
            continue
        if cmd == "X_KEY":
            continue

        if cmd == "S_KEY":
            if player.location == "Town":
                shop_mode = True
                last_message = "Welcome to the shop."
                continue
            continue

        if cmd == "HALL":
            if player.location == "Town":
                hall_mode = True
                hall_view = "menu"
                last_message = "Welcome to the hall."
                continue

        if cmd == "SPELLBOOK":
            spell_mode = True
            shop_mode = False
            inventory_mode = False
            hall_mode = False
            last_message = "Open spellbook."
            continue

        if cmd == "F_KEY":
            if player.location == "Town":
                player.location = "Forrest"
                opponents = spawn_opponents(player.level)
                loot_bank = {"xp": 0, "gold": 0}
                if opponents:
                    last_message = f"A {opponents[0].name} appears."
                    animate_battle_start(player, opponents, last_message)
                else:
                    last_message = "All is quiet. No enemies in sight."
                shop_mode = False
                inventory_mode = False
                hall_mode = False
                spell_mode = False
                SAVE_DATA.save_player(player)
            else:
                primary = primary_opponent(opponents)
                if primary:
                    last_message = f"You are already facing a {primary.name}."
                else:
                    opponents = spawn_opponents(player.level)
                    loot_bank = {"xp": 0, "gold": 0}
                    if opponents:
                        last_message = f"A {opponents[0].name} appears."
                        animate_battle_start(player, opponents, last_message)
                    else:
                        last_message = "All is quiet. No enemies in sight."
                SAVE_DATA.save_player(player)
            continue

        if cmd == "NEXT":
            primary = primary_opponent(opponents)
            if primary:
                last_message = f"You are already facing a {primary.name}."
            else:
                opponents = spawn_opponents(player.level)
                loot_bank = {"xp": 0, "gold": 0}
                if opponents:
                    last_message = f"A {opponents[0].name} appears."
                    animate_battle_start(player, opponents, last_message)
                else:
                    last_message = "All is quiet. No enemies in sight."
            SAVE_DATA.save_player(player)
            continue

        if cmd == "REST":
            if player.location != "Town":
                last_message = "The inn is only in town."
            elif player.gold < 10:
                last_message = "Not enough GP to rest at the inn."
            else:
                player.gold -= 10
                player.hp = player.max_hp
                player.mp = player.max_mp
                last_message = "You rest at the inn and feel fully restored."
                SAVE_DATA.save_player(player)
            continue

        if cmd == "TOWN":
            if player.location == "Town":
                last_message = "You are already in town."
            else:
                player.location = "Town"
                opponents = []
                loot_bank = {"xp": 0, "gold": 0}
                last_message = "You return to town."
            shop_mode = False
            inventory_mode = False
            hall_mode = False
            spell_mode = False
            SAVE_DATA.save_player(player)
            continue

        if cmd == "FOREST":
            if player.location == "Forrest":
                last_message = "You are already in the Forrest."
            else:
                player.location = "Forrest"
                opponents = spawn_opponents(player.level)
                loot_bank = {"xp": 0, "gold": 0}
                if opponents:
                    last_message = f"A {opponents[0].name} appears."
                    animate_battle_start(player, opponents, last_message)
                else:
                    last_message = "All is quiet. No enemies in sight."
            shop_mode = False
            inventory_mode = False
            hall_mode = False
            spell_mode = False
            SAVE_DATA.save_player(player)
            continue

        if not handled_boost:
            if cmd == "HEAL":
                if player.hp == player.max_hp:
                    last_message = "Your HP is already full."
                    continue
                if player.mp < 2:
                    last_message = "Not enough MP to cast Healing."
                    continue
                if player.mp >= 4:
                    boost_prompt = "HEAL"
                    last_message = "Boost Healing? (Y/N)"
                    continue
                last_message = cast_heal(player, boosted=False)
                action_cmd = "HEAL"
            elif cmd == "SPARK":
                if not alive_opponents(opponents):
                    last_message = "There is nothing to target."
                    continue
                if player.mp < 2:
                    last_message = "Not enough MP to cast Spark."
                    continue
                if player.mp >= 4:
                    boost_prompt = "SPARK"
                    last_message = "Boost Spark? (Y/N)"
                    continue
                last_message = cast_spark(player, opponents, boosted=False, loot=loot_bank)
                action_cmd = "SPARK"
            else:
                if cmd == "INVENTORY":
                    inventory_items = list_inventory_items(player)
                    if not inventory_items:
                        last_message = "Inventory is empty."
                    else:
                        inventory_mode = True
                        last_message = "Choose an item to use."
                    continue
                last_message = apply_command(cmd, player, opponents, loot=loot_bank)
                if cmd == "ATTACK":
                    action_cmd = "ATTACK"

        if player.stat_points > 0 and not alive_opponents(opponents):
            leveling_mode = True

        if action_cmd in ("ATTACK", "SPARK"):
            target_index = primary_opponent_index(opponents)
            flash_opponent(
                player,
                opponents,
                last_message,
                target_index,
                ANSI.FG_YELLOW
            )
            defeated_indices = [
                i for i, m in enumerate(opponents)
                if m.hp <= 0 and not m.melted
            ]
            for index in defeated_indices:
                melt_opponent(player, opponents, last_message, index)
                opponents[index].melted = True

        player_defeated = False
        if action_cmd in ("ATTACK", "SPARK", "HEAL") and alive_opponents(opponents):
            if player.location == "Forrest":
                frame = generate_demo_frame(
                    player,
                    opponents,
                    last_message,
                    leveling_mode,
                    shop_mode,
                    inventory_mode,
                    inventory_items,
                    hall_mode,
                    hall_view,
                    spell_mode
                )
                render_frame(frame)
                time.sleep(battle_action_delay(player))
            acting = [(i, m) for i, m in enumerate(opponents) if m.hp > 0]
            for idx, (opp_index, m) in enumerate(acting):
                if m.stunned_turns > 0:
                    m.stunned_turns -= 1
                    last_message += f" The {m.name} is stunned."
                elif random.random() > m.action_chance:
                    last_message += f" The {m.name} hesitates."
                else:
                    damage, crit, miss = roll_damage(m.atk, player.defense)
                    if miss:
                        last_message += f" The {m.name} misses you."
                    else:
                        player.hp = max(0, player.hp - damage)
                        if crit:
                            last_message += (
                                f" Critical hit! The {m.name} hits you for {damage}."
                            )
                        else:
                            last_message += f" The {m.name} hits you for {damage}."
                    flash_opponent(
                        player,
                        opponents,
                        last_message,
                        opp_index,
                        ANSI.FG_RED
                    )
                    if player.hp == 0:
                        lost_gp = player.gold // 2
                        player.gold -= lost_gp
                        player.location = "Town"
                        player.hp = player.max_hp
                        player.mp = player.max_mp
                        opponents = []
                        loot_bank = {"xp": 0, "gold": 0}
                        last_message = (
                            "You were defeated and wake up at the inn. "
                            f"You lost {lost_gp} GP."
                        )
                        player_defeated = True
                        break
                if player.location == "Forrest" and idx < len(acting) - 1:
                    frame = generate_demo_frame(
                        player,
                        opponents,
                        last_message,
                        leveling_mode,
                        shop_mode,
                        inventory_mode,
                        inventory_items,
                        hall_mode,
                        hall_view,
                        spell_mode
                    )
                    render_frame(frame)
                    time.sleep(battle_action_delay(player))

        if player_defeated:
            SAVE_DATA.save_player(player)
            continue

        if action_cmd in ("ATTACK", "SPARK"):
            if not alive_opponents(opponents):
                animate_battle_end(player, opponents, last_message)
                opponents = []
                if loot_bank["xp"] or loot_bank["gold"]:
                    grant_xp(player, loot_bank["xp"])
                    player.gold += loot_bank["gold"]
                    last_message += (
                        f" You gain {loot_bank['xp']} XP and "
                        f"{loot_bank['gold']} gold."
                    )
                    if player.stat_points > 0:
                        leveling_mode = True
                loot_bank = {"xp": 0, "gold": 0}

        if action_cmd in ("ATTACK", "SPARK", "HEAL"):
            SAVE_DATA.save_player(player)


if __name__ == "__main__":
    main()
