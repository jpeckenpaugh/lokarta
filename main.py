import os
import sys
import shutil
import random
import time
import json
import textwrap
from dataclasses import replace
from typing import List, Optional

from combat import cast_spell, primary_opponent, roll_damage
from commands import build_registry
from commands.keymap import map_key_to_command
from commands.registry import CommandContext
from commands.scene_commands import format_commands, scene_commands
from data_access.commands_data import CommandsData
from data_access.items_data import ItemsData
from data_access.opponents_data import OpponentsData
from data_access.scenes_data import ScenesData
from data_access.npcs_data import NpcsData
from data_access.venues_data import VenuesData
from data_access.spells_data import SpellsData
from data_access.save_data import SaveData
from models import Frame, Player, Opponent
from ui.ansi import ANSI, color
from ui.constants import (
    OPPONENT_ART_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from ui.layout import format_action_lines
from ui.rendering import (
    COLOR_BY_NAME,
    animate_scene_gap,
    clear_screen,
    compute_scene_gap_target,
    format_opponent_bar,
    format_player_stats,
    render_frame,
    render_scene_art,
    render_scene_frame,
    render_venue_art,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SAVE_PATH = os.path.join(os.path.dirname(__file__), "saves", "slot1.json")

ITEMS = ItemsData(os.path.join(DATA_DIR, "items.json"))
OPPONENTS = OpponentsData(os.path.join(DATA_DIR, "opponents.json"))
SCENES = ScenesData(os.path.join(DATA_DIR, "scenes.json"))
NPCS = NpcsData(os.path.join(DATA_DIR, "npcs.json"))
VENUES = VenuesData(os.path.join(DATA_DIR, "venues.json"))
SPELLS = SpellsData(os.path.join(DATA_DIR, "spells.json"))
COMMANDS_DATA = CommandsData(os.path.join(DATA_DIR, "commands.json"))
SAVE_DATA = SaveData(SAVE_PATH)
COMMANDS = build_registry()


def battle_action_delay(player: Player) -> float:
    speeds = {
        "fast": 0.2,
        "normal": 0.45,
        "slow": 0.75,
    }
    return speeds.get(player.battle_speed, speeds["normal"])


def delete_save():
    SAVE_DATA.delete()


def format_command_lines(commands: List[dict]) -> List[str]:
    return format_action_lines(format_commands(commands))


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
    spell_mode: bool = False,
    suppress_actions: bool = False
) -> Frame:
    healing = SPELLS.get("healing", {})
    spark = SPELLS.get("spark", {})
    heal_name = healing.get("name", "Healing")
    spark_name = spark.get("name", "Spark")
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
        venue = VENUES.get("town_shop", {})
        npc_lines = []
        npc_ids = venue.get("npc_ids", [])
        npc = {}
        if npc_ids:
            npc_lines = NPCS.format_greeting(npc_ids[0])
            npc = NPCS.get(npc_ids[0], {})
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
        venue = VENUES.get("town_hall", {})
        npc_lines = []
        npc_ids = venue.get("npc_ids", [])
        npc = {}
        if npc_ids:
            npc_lines = NPCS.format_greeting(npc_ids[0])
            npc = NPCS.get(npc_ids[0], {})
        if hall_view == "items":
            info_lines = ITEMS.list_descriptions()
        elif hall_view == "opponents":
            info_lines = OPPONENTS.list_descriptions()
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
        heal_cost = int(healing.get("mp_cost", 2))
        spark_cost = int(spark.get("mp_cost", 2))
        body = [
            "Spellbook",
            "",
            f"{heal_name} ({heal_cost} MP)",
            f"{spark_name} ({spark_cost} MP)",
        ]
        actions = [
            f"  [1] {heal_name}",
            f"  [2] {spark_name}",
            "  [B] Back",
            "  [Q] Quit",
        ]
        actions = format_action_lines(actions)
        art_lines = []
        art_color = ANSI.FG_WHITE
    elif player.location == "Town":
        scene_data = SCENES.get("town", {})
        art_lines = scene_data.get("art", [])
        art_color = COLOR_BY_NAME.get(scene_data.get("color", "yellow").lower(), ANSI.FG_WHITE)
        body = [
            "You arrive in town, safe behind sturdy wooden walls.",
            "",
            "The inn's lantern glows warmly in the evening light.",
            "A local shop can provide you with basic items.",
            "If you are lost, check the town hall for instructions."
        ]
        actions = format_command_lines(
            scene_commands(SCENES, COMMANDS_DATA, "town", player, opponents)
        )
    else:
        scene_data = SCENES.get("forest", {})
        forest_art, art_color = render_scene_art(scene_data, opponents)
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
        actions = format_command_lines(
            scene_commands(SCENES, COMMANDS_DATA, "forest", player, opponents)
        )
        art_lines = forest_art
    if suppress_actions:
        actions = format_action_lines([])

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
            else "Keys: use the action panel"
        ),
        location=player.location,
        art_lines=art_lines,
        art_color=art_color,
        status_lines=status_lines,
    )


def apply_command(
    command: str,
    player: Player,
    opponents: List[Opponent],
    loot: dict
) -> str:
    ctx = CommandContext(
        player=player,
        opponents=opponents,
        loot=loot,
        spells_data=SPELLS,
        items_data=ITEMS,
    )
    handled = COMMANDS.dispatch(command, ctx)
    if handled is not None:
        return handled
    return "Unknown action."


def animate_battle_start(player: Player, opponents: List[Opponent], message: str):
    if player.location != "Forest" or not opponents:
        return
    scene_data = SCENES.get("forest", {})
    gap_base = (
        int(scene_data.get("gap_min", 2))
        if scene_data.get("left")
        else int(scene_data.get("gap_width", 20))
    )
    gap_target = compute_scene_gap_target(scene_data, opponents)
    animate_scene_gap(
        SCENES,
        COMMANDS_DATA,
        "forest",
        player,
        opponents,
        message,
        gap_base,
        gap_target,
        art_opponents=[]
    )


def animate_battle_end(player: Player, opponents: List[Opponent], message: str):
    if player.location != "Forest" or not opponents:
        return
    scene_data = SCENES.get("forest", {})
    gap_base = (
        int(scene_data.get("gap_min", 2))
        if scene_data.get("left")
        else int(scene_data.get("gap_width", 20))
    )
    gap_target = compute_scene_gap_target(scene_data, opponents)
    animate_scene_gap(
        SCENES,
        COMMANDS_DATA,
        "forest",
        player,
        opponents,
        message,
        gap_target,
        gap_base,
        art_opponents=[]
    )


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
    if index is None or player.location != "Forest":
        return
    scene_data = SCENES.get("forest", {})
    gap_target = compute_scene_gap_target(scene_data, opponents)
    render_scene_frame(
        SCENES,
        COMMANDS_DATA,
        "forest",
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
    player: Player,
    opponents: List[Opponent],
    message: str,
    index: Optional[int]
):
    if index is None or player.location != "Forest":
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
    scene_data = SCENES.get("forest", {})
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
            SCENES,
            COMMANDS_DATA,
            "forest",
            player,
            opponents,
            message,
            gap_target,
            art_opponents=art_overrides,
            visible_indices={index},
            manual_lines_indices={index},
            suppress_actions=True
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


def read_keypress_timeout(timeout_sec: float) -> Optional[str]:
    if os.name == "nt":
        import msvcrt
        end = time.monotonic() + timeout_sec
        while time.monotonic() < end:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in (b"\x00", b"\xe0"):
                    msvcrt.getch()
                    return ""
                try:
                    return ch.decode("utf-8", errors="ignore")
                except Exception:
                    return ""
            time.sleep(0.01)
        return None
    else:
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            ready, _, _ = select.select([sys.stdin], [], [], timeout_sec)
            if ready:
                return sys.stdin.read(1)
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


# -----------------------------
# Main loop
# -----------------------------

def main():
    cols, rows = shutil.get_terminal_size(fallback=(0, 0))
    if cols < SCREEN_WIDTH or rows < SCREEN_HEIGHT:
        print(f"WARNING: Terminal size is {cols}x{rows}. Recommended is 100x30.")
        print("Resize your terminal for best results.")
        input("Press Enter to continue anyway...")

    player = Player.from_dict({})
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
            title_scene = SCENES.get("title", {})
            title_art = title_scene.get("art", [])
            title_color = COLOR_BY_NAME.get(title_scene.get("color", "cyan").lower(), ANSI.FG_WHITE)
            if title_confirm:
                title_body = [
                    "World Builder",
                    "",
                    "Overwrite existing save?",
                    "",
                    "[Y] Yes, start new",
                    "[N] No, go back",
                ]
            elif SAVE_DATA.exists():
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
            elif SAVE_DATA.exists():
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

            if SAVE_DATA.exists():
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
                inventory_items = player.list_inventory_items(ITEMS)
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

        if boost_prompt:
            choice = None
            for remaining in range(3, 0, -1):
                countdown_message = f"{last_message} ({remaining})"
                frame = generate_demo_frame(
                    player,
                    opponents,
                    countdown_message,
                    leveling_mode,
                    shop_mode,
                    inventory_mode,
                    inventory_items,
                    hall_mode,
                    hall_view,
                    spell_mode
                )
                render_frame(frame)
                choice = read_keypress_timeout(1.0)
                if choice and choice.lower() in ("y", "n"):
                    break
            ch = choice if choice else "n"
        else:
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
                    player = Player.from_dict({})
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
            if ch.lower() == "c" and SAVE_DATA.exists():
                loaded = SAVE_DATA.load_player()
                if loaded:
                    player = loaded
                else:
                    player = Player.from_dict({})
            elif ch.lower() == "n":
                if SAVE_DATA.exists():
                    title_confirm = True
                    continue
                player = Player.from_dict({})
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
                last_message = cast_spell(player, opponents, "healing", boosted, loot_bank, SPELLS)
                action_cmd = "HEAL"
            else:
                last_message = cast_spell(player, opponents, "spark", boosted, loot_bank, SPELLS)
                action_cmd = "SPARK"
            boost_prompt = None
            handled_boost = True

        if not handled_boost:
            available_commands = None
            if not any(
                [
                    title_mode,
                    leveling_mode,
                    shop_mode,
                    inventory_mode,
                    hall_mode,
                    spell_mode,
                    boost_prompt,
                ]
            ):
                scene_id = "town" if player.location == "Town" else "forest"
                available_commands = scene_commands(
                    SCENES,
                    COMMANDS_DATA,
                    scene_id,
                    player,
                    opponents
                )
            cmd = map_key_to_command(ch, available_commands)
        else:
            cmd = None

        if cmd == "QUIT":
            quit_confirm = True
            last_message = "Quit? (Y/N)"
            continue

        if cmd is None and not handled_boost:
            continue

        if leveling_mode and not handled_boost:
            last_message, leveling_done = player.handle_level_up_input(cmd)
            if leveling_done:
                leveling_mode = False
            continue

        if inventory_mode and not handled_boost:
            if cmd == "B_KEY":
                inventory_mode = False
                last_message = "Closed inventory."
            elif cmd and cmd.startswith("NUM"):
                idx = int(cmd.replace("NUM", "")) - 1
                if 0 <= idx < len(inventory_items):
                    key, _ = inventory_items[idx]
                    last_message = player.use_item(key, ITEMS)
                    SAVE_DATA.save_player(player)
                    inventory_items = player.list_inventory_items(ITEMS)
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
                player.location = "Forest"
                opponents = OPPONENTS.spawn(player.level, ANSI.FG_CYAN)
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
                    opponents = OPPONENTS.spawn(player.level, ANSI.FG_CYAN)
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
                opponents = OPPONENTS.spawn(player.level, ANSI.FG_CYAN)
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
            if player.location == "Forest":
                primary = primary_opponent(opponents)
                if primary:
                    last_message = f"You are already facing a {primary.name}."
                else:
                    opponents = OPPONENTS.spawn(player.level, ANSI.FG_CYAN)
                    loot_bank = {"xp": 0, "gold": 0}
                    if opponents:
                        last_message = f"A {opponents[0].name} appears."
                        animate_battle_start(player, opponents, last_message)
                    else:
                        last_message = "All is quiet. No enemies in sight."
            else:
                player.location = "Forest"
                opponents = OPPONENTS.spawn(player.level, ANSI.FG_CYAN)
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
                healing = SPELLS.get("healing", {})
                heal_cost = int(healing.get("mp_cost", 2))
                boosted_heal_cost = int(healing.get("boosted_mp_cost", 4))
                if player.mp < heal_cost:
                    last_message = f"Not enough MP to cast {healing.get('name', 'Healing')}."
                    continue
                if player.mp >= boosted_heal_cost:
                    boost_prompt = "HEAL"
                    last_message = f"Boost {healing.get('name', 'Healing')}? (Y/N)"
                    continue
                last_message = cast_spell(player, opponents, "healing", boosted=False, loot=loot_bank, spells_data=SPELLS)
                action_cmd = "HEAL"
            elif cmd == "SPARK":
                if not any(opponent.hp > 0 for opponent in opponents):
                    last_message = "There is nothing to target."
                    continue
                spark = SPELLS.get("spark", {})
                spark_cost = int(spark.get("mp_cost", 2))
                boosted_spark_cost = int(spark.get("boosted_mp_cost", 4))
                if player.mp < spark_cost:
                    last_message = f"Not enough MP to cast {spark.get('name', 'Spark')}."
                    continue
                if player.mp >= boosted_spark_cost:
                    boost_prompt = "SPARK"
                    last_message = f"Boost {spark.get('name', 'Spark')}? (Y/N)"
                    continue
                last_message = cast_spell(player, opponents, "spark", boosted=False, loot=loot_bank, spells_data=SPELLS)
                action_cmd = "SPARK"
            else:
                if cmd == "INVENTORY":
                    inventory_items = player.list_inventory_items(ITEMS)
                    if not inventory_items:
                        last_message = "Inventory is empty."
                    else:
                        inventory_mode = True
                        last_message = "Choose an item to use."
                    continue
                last_message = apply_command(cmd, player, opponents, loot=loot_bank)
                if cmd == "ATTACK":
                    action_cmd = "ATTACK"

        if player.needs_level_up() and not any(opponent.hp > 0 for opponent in opponents):
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
        if action_cmd in ("ATTACK", "SPARK", "HEAL") and any(opponent.hp > 0 for opponent in opponents):
            if player.location == "Forest":
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
                    spell_mode,
                    suppress_actions=True
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
                if player.location == "Forest" and idx < len(acting) - 1:
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
                        spell_mode,
                        suppress_actions=True
                    )
                    render_frame(frame)
                    time.sleep(battle_action_delay(player))

        if player_defeated:
            SAVE_DATA.save_player(player)
            continue

        if action_cmd in ("ATTACK", "SPARK"):
            if not any(opponent.hp > 0 for opponent in opponents):
                animate_battle_end(player, opponents, last_message)
                opponents = []
                if loot_bank["xp"] or loot_bank["gold"]:
                    player.gain_xp(loot_bank["xp"])
                    player.gold += loot_bank["gold"]
                    last_message += (
                        f" You gain {loot_bank['xp']} XP and "
                        f"{loot_bank['gold']} gold."
                    )
                    if player.needs_level_up():
                        leveling_mode = True
                loot_bank = {"xp": 0, "gold": 0}

        if action_cmd in ("ATTACK", "SPARK", "HEAL"):
            SAVE_DATA.save_player(player)


if __name__ == "__main__":
    main()
