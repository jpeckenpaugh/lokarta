import os
import sys
import shutil
import random
import time
from typing import List, Optional

from combat import (
    battle_action_delay,
    cast_spell,
    primary_opponent,
    primary_opponent_index,
    roll_damage,
)
from commands import build_registry
from commands.keymap import map_key_to_command
from commands.registry import CommandContext
from commands.scene_commands import scene_commands
from data_access.commands_data import CommandsData
from data_access.items_data import ItemsData
from data_access.menus_data import MenusData
from data_access.opponents_data import OpponentsData
from data_access.scenes_data import ScenesData
from data_access.npcs_data import NpcsData
from data_access.venues_data import VenuesData
from data_access.spells_data import SpellsData
from data_access.save_data import SaveData
from input import read_keypress, read_keypress_timeout
from models import Frame, Player, Opponent
from shop import purchase_item
from ui.ansi import ANSI, color
from ui.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from ui.layout import format_action_lines
from ui.rendering import (
    COLOR_BY_NAME,
    clear_screen,
    animate_battle_end,
    animate_battle_start,
    flash_opponent,
    melt_opponent,
    render_frame,
)
from ui.screens import ScreenContext, generate_frame

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SAVE_PATH = os.path.join(os.path.dirname(__file__), "saves", "slot1.json")

ITEMS = ItemsData(os.path.join(DATA_DIR, "items.json"))
OPPONENTS = OpponentsData(os.path.join(DATA_DIR, "opponents.json"))
SCENES = ScenesData(os.path.join(DATA_DIR, "scenes.json"))
NPCS = NpcsData(os.path.join(DATA_DIR, "npcs.json"))
VENUES = VenuesData(os.path.join(DATA_DIR, "venues.json"))
SPELLS = SpellsData(os.path.join(DATA_DIR, "spells.json"))
COMMANDS_DATA = CommandsData(os.path.join(DATA_DIR, "commands.json"))
MENUS = MenusData(os.path.join(DATA_DIR, "menus.json"))
SAVE_DATA = SaveData(SAVE_PATH)
COMMANDS = build_registry()
SCREEN_CTX = ScreenContext(
    items=ITEMS,
    opponents=OPPONENTS,
    scenes=SCENES,
    npcs=NPCS,
    venues=VENUES,
    menus=MENUS,
    commands=COMMANDS_DATA,
    spells=SPELLS,
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
            frame = generate_frame(
                SCREEN_CTX,
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
                frame = generate_frame(
                    SCREEN_CTX,
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
                    SAVE_DATA.delete()
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
            venue = VENUES.get("town_hall", {})
            info_sections = venue.get("info_sections", [])
            if cmd == "B_KEY":
                hall_mode = False
                last_message = venue.get("leave_message", "You leave the hall.")
            else:
                selected = next(
                    (entry for entry in info_sections if entry.get("command") == cmd),
                    None
                )
                if selected:
                    hall_view = selected.get("key", hall_view)
                    last_message = selected.get("message", last_message)
            continue

        if shop_mode and not handled_boost:
            venue = VENUES.get("town_shop", {})
            if cmd == "B_KEY":
                shop_mode = False
                last_message = venue.get("leave_message", "You leave the shop.")
            else:
                selection = next(
                    (entry for entry in venue.get("inventory_items", []) if entry.get("command") == cmd),
                    None
                )
                if selection:
                    item_id = selection.get("item_id")
                    if item_id:
                        last_message = purchase_item(player, ITEMS, item_id)
                        SAVE_DATA.save_player(player)
            continue

        if cmd == "B_KEY":
            continue
        if cmd == "X_KEY":
            continue

        if cmd == "S_KEY":
            if player.location == "Town":
                shop_mode = True
                venue = VENUES.get("town_shop", {})
                last_message = venue.get("welcome_message", "Welcome to the shop.")
                continue
            continue

        if cmd == "HALL":
            if player.location == "Town":
                hall_mode = True
                hall_view = "menu"
                venue = VENUES.get("town_hall", {})
                last_message = venue.get("welcome_message", "Welcome to the hall.")
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
                    animate_battle_start(
                        SCENES,
                        COMMANDS_DATA,
                        "forest",
                        player,
                        opponents,
                        last_message
                    )
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
                        animate_battle_start(
                            SCENES,
                            COMMANDS_DATA,
                            "forest",
                            player,
                            opponents,
                            last_message
                        )
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
                    animate_battle_start(
                        SCENES,
                        COMMANDS_DATA,
                        "forest",
                        player,
                        opponents,
                        last_message
                    )
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
                        animate_battle_start(
                            SCENES,
                            COMMANDS_DATA,
                            "forest",
                            player,
                            opponents,
                            last_message
                        )
                    else:
                        last_message = "All is quiet. No enemies in sight."
            else:
                player.location = "Forest"
                opponents = OPPONENTS.spawn(player.level, ANSI.FG_CYAN)
                loot_bank = {"xp": 0, "gold": 0}
                if opponents:
                    last_message = f"A {opponents[0].name} appears."
                    animate_battle_start(
                        SCENES,
                        COMMANDS_DATA,
                        "forest",
                        player,
                        opponents,
                        last_message
                    )
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
                SCENES,
                COMMANDS_DATA,
                "forest",
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
                melt_opponent(
                    SCENES,
                    COMMANDS_DATA,
                    "forest",
                    player,
                    opponents,
                    last_message,
                    index
                )
                opponents[index].melted = True

        player_defeated = False
        if action_cmd in ("ATTACK", "SPARK", "HEAL") and any(opponent.hp > 0 for opponent in opponents):
            if player.location == "Forest":
                frame = generate_frame(
                    SCREEN_CTX,
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
                        SCENES,
                        COMMANDS_DATA,
                        "forest",
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
                    frame = generate_frame(
                        SCREEN_CTX,
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
                animate_battle_end(
                    SCENES,
                    COMMANDS_DATA,
                    "forest",
                    player,
                    opponents,
                    last_message
                )
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
