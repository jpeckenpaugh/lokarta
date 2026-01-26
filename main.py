import os
import sys
import shutil
import random
import json
import textwrap
from dataclasses import dataclass
from typing import List, Optional

SCREEN_WIDTH = 100
SCREEN_HEIGHT = 30
STAT_LINES = 2
ACTION_LINES = 3
NARRATIVE_INDENT = 2

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


# -----------------------------
# Frame model (engine output)
# -----------------------------

@dataclass
class Frame:
    title: str
    body_lines: List[str]
    action_lines: List[str]
    stat_lines: List[str]
    footer_hint: str  # shows available keys
    location: str
    art_lines: List[str]
    art_color: str
    status_lines: List[str]


# -----------------------------
# Engine (pure)
# -----------------------------

@dataclass
class Player:
    name: str
    level: int
    xp: int
    stat_points: int
    gold: int
    hp: int
    max_hp: int
    mp: int
    max_mp: int
    atk: int
    defense: int
    location: str
    inventory: dict


@dataclass
class Monster:
    name: str
    level: int
    hp: int
    max_hp: int
    atk: int
    defense: int
    stunned_turns: int
    art_lines: List[str]
    art_color: str
    arrival: str


def create_monster(data: dict) -> Monster:
    name = data.get("name", "Slime")
    level = int(data.get("level", 1))
    hp = int(data.get("hp", 10))
    atk = int(data.get("atk", 5))
    defense = int(data.get("defense", 5))
    art_lines = data.get("art", [])
    arrival = data.get("arrival", "appears")
    return Monster(
        name=name,
        level=level,
        hp=hp,
        max_hp=hp,
        atk=atk,
        defense=defense,
        stunned_turns=0,
        art_lines=art_lines,
        art_color=ANSI.FG_CYAN,
        arrival=arrival
    )


def spawn_monsters(player_level: int) -> List[Monster]:
    monsters = load_monster_data()
    if not monsters:
        return []
    candidates = list(monsters.values())
    total_level = 0
    spawned = []
    attempts = 0
    while len(spawned) < 3 and attempts < 10:
        attempts += 1
        remaining = max(1, player_level - total_level)
        choices = [m for m in candidates if int(m.get("level", 1)) <= remaining]
        if not choices:
            break
        data = random.choice(choices)
        spawned.append(create_monster(data))
        total_level += int(data.get("level", 1))
        if total_level >= player_level:
            break
    if not spawned:
        spawned.append(create_monster(candidates[0]))
    return spawned


def load_monster_data() -> dict:
    path = os.path.join(os.path.dirname(__file__), "monsters.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def load_scene_data() -> dict:
    path = os.path.join(os.path.dirname(__file__), "scenes.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def color_from_name(name: str) -> str:
    return {
        "white": ANSI.FG_WHITE,
        "cyan": ANSI.FG_CYAN,
        "green": ANSI.FG_GREEN,
        "yellow": ANSI.FG_YELLOW,
        "red": ANSI.FG_RED,
        "blue": ANSI.FG_BLUE,
    }.get(name.lower(), ANSI.FG_WHITE)


def load_item_data() -> dict:
    path = os.path.join(os.path.dirname(__file__), "items.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_game(player: Player):
    path = os.path.join(os.path.dirname(__file__), "save.json")
    data = {
        "name": player.name,
        "level": player.level,
        "xp": player.xp,
        "stat_points": player.stat_points,
        "gold": player.gold,
        "hp": player.hp,
        "max_hp": player.max_hp,
        "mp": player.mp,
        "max_mp": player.max_mp,
        "atk": player.atk,
        "defense": player.defense,
        "location": player.location,
        "inventory": player.inventory,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_game() -> Optional[Player]:
    path = os.path.join(os.path.dirname(__file__), "save.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return Player(
        name=data.get("name", "WARRIOR"),
        level=int(data.get("level", 1)),
        xp=int(data.get("xp", 0)),
        stat_points=int(data.get("stat_points", 0)),
        gold=int(data.get("gold", 10)),
        hp=int(data.get("hp", 10)),
        max_hp=int(data.get("max_hp", 10)),
        mp=int(data.get("mp", 10)),
        max_mp=int(data.get("max_mp", 10)),
        atk=int(data.get("atk", 10)),
        defense=int(data.get("defense", 10)),
        location="Town",
        inventory=data.get("inventory", {}),
    )


def has_save() -> bool:
    path = os.path.join(os.path.dirname(__file__), "save.json")
    return os.path.exists(path)


def delete_save():
    path = os.path.join(os.path.dirname(__file__), "save.json")
    try:
        os.remove(path)
    except OSError:
        pass


def new_player() -> Player:
    return Player(
        name="WARRIOR",
        level=1,
        xp=0,
        stat_points=0,
        gold=10,
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


def add_item(inventory: dict, key: str, amount: int = 1):
    inventory[key] = int(inventory.get(key, 0)) + amount


def format_inventory(player: Player) -> str:
    items = load_item_data()
    if not player.inventory:
        return "Inventory is empty."
    parts = []
    for key, count in player.inventory.items():
        item = items.get(key, {"name": key})
        parts.append(f"{item.get('name', key)} x{count}")
    return "Inventory: " + ", ".join(parts)


def purchase_item(player: Player, key: str) -> str:
    items = load_item_data()
    item = items.get(key)
    if not item:
        return "That item is not available."
    price = int(item.get("price", 0))
    if player.gold < price:
        return "Not enough GP."
    player.gold -= price
    add_item(player.inventory, key, 1)
    return f"Purchased {item.get('name', key)}."


def list_inventory_items(player: Player) -> List[tuple[str, str]]:
    items = load_item_data()
    entries = []
    for key in sorted(player.inventory.keys()):
        count = int(player.inventory.get(key, 0))
        if count <= 0:
            continue
        item = items.get(key, {"name": key})
        name = item.get("name", key)
        hp = int(item.get("hp", 0))
        mp = int(item.get("mp", 0))
        entries.append((key, f"{name} x{count} (+{hp} HP/+{mp} MP)"))
    return entries


def use_item(player: Player, key: str) -> str:
    items = load_item_data()
    item = items.get(key)
    if not item:
        return "That item is not available."
    if int(player.inventory.get(key, 0)) <= 0:
        return "You do not have that item."
    if player.hp == player.max_hp and player.mp == player.max_mp:
        return "HP and MP are already full."
    hp_gain = int(item.get("hp", 0))
    mp_gain = int(item.get("mp", 0))
    player.hp = min(player.max_hp, player.hp + hp_gain)
    player.mp = min(player.max_mp, player.mp + mp_gain)
    player.inventory[key] = int(player.inventory.get(key, 0)) - 1
    if player.inventory[key] <= 0:
        player.inventory.pop(key, None)
    return f"Used {item.get('name', key)}."


def list_monster_descriptions() -> List[str]:
    monsters = load_monster_data()
    lines = []
    for data in monsters.values():
        name = data.get("name", "Unknown")
        desc = data.get("desc", "")
        lines.append(f"{name}: {desc}")
    return lines


def list_item_descriptions() -> List[str]:
    items = load_item_data()
    lines = []
    for data in items.values():
        name = data.get("name", "Unknown")
        desc = data.get("desc", "")
        lines.append(f"{name}: {desc}")
    return lines


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
    monsters: List[Monster],
    message: str = "",
    leveling_mode: bool = False,
    shop_mode: bool = False,
    inventory_mode: bool = False,
    inventory_items: Optional[List[tuple[str, str]]] = None,
    hall_mode: bool = False,
    hall_view: str = "monsters",
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
        items = load_item_data()
        rations = items.get("rations", {})
        elixir = items.get("elixir", {})
        body = [
            "Town Shop",
            "",
            f"Rations (+5 HP/MP)  {rations.get('price', 0)} GP",
            f"Elixir (+20 HP/MP)  {elixir.get('price', 0)} GP",
            "",
            f"Your GP: {player.gold}",
            "",
            "Choose an item to purchase.",
        ]
        actions = [
            "  [1] Buy Rations",
            "  [2] Buy Elixir",
            "  [B] Back",
            "  [Q] Quit",
        ]
        actions = format_action_lines(actions)
        art_lines = []
        art_color = ANSI.FG_WHITE
    elif player.location == "Town" and hall_mode:
        if hall_view == "items":
            info_lines = list_item_descriptions()
            title = "Town Hall - Items"
        else:
            info_lines = list_monster_descriptions()
            title = "Town Hall - Monsters"
        body = [title, ""] + info_lines
        actions = [
            "  [1] Monsters",
            "  [2] Items",
            "  [B] Back",
            "  [Q] Quit",
        ]
        actions = format_action_lines(actions)
        art_lines = []
        art_color = ANSI.FG_WHITE
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
        gap_width = int(scene_data.get("gap_width", 20))
        forest_template = scene_data.get("art", [])
        forest_art = []
        for i, line in enumerate(forest_template):
            gap_fill = " " * gap_width
            primary = monsters[0] if monsters else None
            if primary and primary.art_lines:
                art = primary.art_lines or []
                start_row = (len(forest_template) - len(art)) // 2
                if start_row <= i < start_row + len(art):
                    monster_line = art[i - start_row]
                    pad_left = (gap_width - len(monster_line)) // 2
                    pad_right = gap_width - len(monster_line) - pad_left
                    monster_colored = (
                        primary.art_color + monster_line + ANSI.FG_GREEN
                    )
                    gap_fill = (" " * pad_left) + monster_colored + (" " * pad_right)
            forest_art.append(line.replace("{GAP}", gap_fill))
        monster_lines = []
        for i, m in enumerate(monsters[:3], start=1):
            line = f"{i}) {m.name} L{m.level} HP {m.hp}/{m.max_hp} ATK {m.atk} DEF {m.defense}"
            if m.stunned_turns > 0:
                line += f" (Stun {m.stunned_turns})"
            monster_lines.append(line)
        body = [
            (
                f"A {monsters[0].name} {monsters[0].arrival}."
                if monsters
                else "All is quiet. No enemies in sight."
            ),
            "",
            *monster_lines,
        ]
        if monsters:
            actions = [
                f"  [A] Attack the {monsters[0].name.lower()}",
            ]
            actions += [
                "  [M] Magic",
                "  [O] Open inventory",
                "  [T] Return to Town",
                "  [Q] Quit",
            ]
        else:
            actions = [
                "  [F] Find a monster to fight",
            ]
            actions += [
                "  [M] Magic",
                "  [O] Open inventory",
                "  [T] Return to Town",
                "  [Q] Quit",
            ]
        actions = format_action_lines(actions)
        art_lines = forest_art
        art_color = color_from_name(scene_data.get("color", "green"))

    status_lines = (
        textwrap.wrap(message, width=SCREEN_WIDTH - 4)
        if message
        else []
    )

    hp_text = color(f"HP: {player.hp} / {player.max_hp}", ANSI.FG_GREEN)
    mp_text = color(f"MP: {player.mp} / {player.max_mp}", ANSI.FG_MAGENTA)
    atk_text = color(f"ATK: {player.atk}", ANSI.DIM)
    def_text = color(f"DEF: {player.defense}", ANSI.DIM)
    level_text = color(f"Level: {player.level}", ANSI.FG_CYAN)
    xp_text = color(f"XP: {player.xp}", ANSI.FG_GREEN)
    gp_text = color(f"GP: {player.gold}", ANSI.FG_YELLOW)
    stats = [
        f"{hp_text}    {mp_text}    {atk_text}    {def_text}",
        f"{level_text}    {xp_text}    {gp_text}",
    ]

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


def try_stun(monster: Monster, chance: float) -> int:
    if random.random() < chance:
        turns = random.randint(1, 3)
        monster.stunned_turns = max(monster.stunned_turns, turns)
        return turns
    return 0


def cast_spark(player: Player, monsters: List[Monster], boosted: bool) -> str:
    if not monsters:
        return "There is nothing to target."
    monster = monsters[0]
    mp_cost = 4 if boosted else 2
    if player.mp < mp_cost:
        return "Not enough MP to cast Spark."
    player.mp -= mp_cost
    damage, crit, miss = roll_damage(player.atk + 2, monster.defense)
    if boosted:
        damage *= 2
    if miss:
        return f"Your Spark misses the {monster.name}."
    monster.hp = max(0, monster.hp - damage)
    if monster.hp == 0:
        xp_gain = random.randint(monster.max_hp // 2, monster.max_hp)
        gold_gain = random.randint(monster.max_hp // 2, monster.max_hp)
        grant_xp(player, xp_gain)
        player.gold += gold_gain
        message = (
            f"Your Spark fells the {monster.name}. You gain "
            f"{xp_gain} XP and {gold_gain} gold."
        )
        return message
    stun_chance = 0.80 if boosted else 0.40
    stunned_turns = try_stun(monster, stun_chance)
    if crit:
        message = f"Critical Spark! You hit the {monster.name} for {damage}."
    else:
        message = f"You hit the {monster.name} with Spark for {damage}."
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
    monsters: List[Monster]
) -> str:
    # Placeholder for real game logic: return a message to display.
    if command == "ATTACK":
        if not monsters:
            return "There is nothing to attack."
        monster = monsters[0]
        damage, crit, miss = roll_damage(player.atk, monster.defense)
        if miss:
            return f"You miss the {monster.name}."
        monster.hp = max(0, monster.hp - damage)
        if monster.hp == 0:
            xp_gain = random.randint(monster.max_hp // 2, monster.max_hp)
            gold_gain = random.randint(monster.max_hp // 2, monster.max_hp)
            grant_xp(player, xp_gain)
            player.gold += gold_gain
            message = (
                f"You strike down the {monster.name} and gain "
                f"{xp_gain} XP and {gold_gain} gold."
            )
            return message
        if crit:
            return f"Critical hit! You hit the {monster.name} for {damage}."
        return f"You hit the {monster.name} for {damage}."
    if command == "HEAL":
        return cast_heal(player, boosted=False)
    if command == "INVENTORY":
        return format_inventory(player)
    if command == "SPARK":
        return cast_spark(player, monsters, boosted=False)
    return "Unknown action."


# -----------------------------
# UI / Renderer
# -----------------------------

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


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


# -----------------------------
# Single-key input (macOS/Linux)
# -----------------------------

def read_keypress() -> str:
    """
    Read a single keypress without requiring Enter (POSIX terminals).
    Returns a single-character string.
    """
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
    monsters: List[Monster] = []

    last_message = ""
    leveling_mode = False
    boost_prompt: Optional[str] = None
    shop_mode = False
    inventory_mode = False
    inventory_items: List[tuple[str, str]] = []
    hall_mode = False
    hall_view = "monsters"
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
                saved_player = load_game()
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
                monsters,
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
                save_game(player)
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
                    monsters = []
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
                loaded = load_game()
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
            monsters = []
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
                last_message = cast_spark(player, monsters, boosted)
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
                    save_game(player)
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
                hall_view = "monsters"
                last_message = "Viewing monster info."
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
                save_game(player)
            elif cmd == "NUM2":
                last_message = purchase_item(player, "elixir")
                save_game(player)
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
                hall_view = "monsters"
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
                monsters = spawn_monsters(player.level)
                if monsters:
                    last_message = f"A {monsters[0].name} appears."
                else:
                    last_message = "All is quiet. No enemies in sight."
                shop_mode = False
                inventory_mode = False
                hall_mode = False
                spell_mode = False
                save_game(player)
            else:
                if monsters:
                    last_message = f"You are already facing a {monsters[0].name}."
                else:
                    monsters = spawn_monsters(player.level)
                    if monsters:
                        last_message = f"A {monsters[0].name} appears."
                    else:
                        last_message = "All is quiet. No enemies in sight."
                save_game(player)
            continue

        if cmd == "NEXT":
            if monsters:
                last_message = f"You are already facing a {monsters[0].name}."
            else:
                monsters = spawn_monsters(player.level)
                if monsters:
                    last_message = f"A {monsters[0].name} appears."
                else:
                    last_message = "All is quiet. No enemies in sight."
            save_game(player)
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
                save_game(player)
            continue

        if cmd == "TOWN":
            if player.location == "Town":
                last_message = "You are already in town."
            else:
                player.location = "Town"
                monsters = []
                last_message = "You return to town."
            shop_mode = False
            inventory_mode = False
            hall_mode = False
            spell_mode = False
            save_game(player)
            continue

        if cmd == "FOREST":
            if player.location == "Forrest":
                last_message = "You are already in the Forrest."
            else:
                player.location = "Forrest"
                monsters = spawn_monsters(player.level)
                if monsters:
                    last_message = f"A {monsters[0].name} appears."
                else:
                    last_message = "All is quiet. No enemies in sight."
            shop_mode = False
            inventory_mode = False
            hall_mode = False
            spell_mode = False
            save_game(player)
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
                if not monsters:
                    last_message = "There is nothing to target."
                    continue
                if player.mp < 2:
                    last_message = "Not enough MP to cast Spark."
                    continue
                if player.mp >= 4:
                    boost_prompt = "SPARK"
                    last_message = "Boost Spark? (Y/N)"
                    continue
                last_message = cast_spark(player, monsters, boosted=False)
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
                last_message = apply_command(cmd, player, monsters)
                if cmd == "ATTACK":
                    action_cmd = "ATTACK"

        if player.stat_points > 0:
            leveling_mode = True

        if action_cmd in ("ATTACK", "SPARK", "HEAL") and monsters:
            for m in list(monsters):
                if m.hp <= 0:
                    continue
                if m.stunned_turns > 0:
                    m.stunned_turns -= 1
                    last_message += f" The {m.name} is stunned."
                    continue
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
                if player.hp == 0:
                    lost_gp = player.gold // 2
                    player.gold -= lost_gp
                    player.location = "Town"
                    player.hp = player.max_hp
                    player.mp = player.max_mp
                    monsters = []
                    last_message = (
                        "You were defeated and wake up at the inn. "
                        f"You lost {lost_gp} GP."
                    )
                    break

        if action_cmd in ("ATTACK", "SPARK"):
            monsters = [m for m in monsters if m.hp > 0]

        if action_cmd in ("ATTACK", "SPARK", "HEAL"):
            save_game(player)


if __name__ == "__main__":
    main()
