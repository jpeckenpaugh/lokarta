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
from commands.registry import CommandContext, dispatch_command
from commands.router import CommandState, RouterContext, handle_boost_confirm, handle_command
from commands.scene_commands import scene_commands
from data_access.commands_data import CommandsData
from data_access.items_data import ItemsData
from data_access.menus_data import MenusData
from data_access.text_data import TextData
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
from ui.text import format_text

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
TEXTS = TextData(os.path.join(DATA_DIR, "text.json"))
SAVE_DATA = SaveData(SAVE_PATH)
SPELL_COMMANDS = {
    spell.get("command_id")
    for spell in SPELLS.all().values()
    if isinstance(spell, dict) and spell.get("command_id")
}
TARGETED_SPELL_COMMANDS = {
    spell.get("command_id")
    for spell in SPELLS.all().values()
    if isinstance(spell, dict) and spell.get("command_id") and spell.get("requires_target")
}
COMBAT_ACTIONS = {"ATTACK"} | SPELL_COMMANDS
OFFENSIVE_ACTIONS = {"ATTACK"} | TARGETED_SPELL_COMMANDS
COMMANDS = build_registry()
ROUTER_CTX = RouterContext(
    items=ITEMS,
    opponents_data=OPPONENTS,
    scenes=SCENES,
    commands=COMMANDS_DATA,
    venues=VENUES,
    save_data=SAVE_DATA,
    spells=SPELLS,
    menus=MENUS,
    registry=COMMANDS,
)
SCREEN_CTX = ScreenContext(
    items=ITEMS,
    opponents=OPPONENTS,
    scenes=SCENES,
    npcs=NPCS,
    venues=VENUES,
    menus=MENUS,
    commands=COMMANDS_DATA,
    spells=SPELLS,
    text=TEXTS,
)






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
    inn_mode = False
    spell_mode = False
    quit_confirm = False
    title_mode = True
    player.location = "Title"
    while True:
        if title_mode:
            player.has_save = SAVE_DATA.exists()
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
            inn_mode,
            spell_mode
        )
        render_frame(frame)

        if boost_prompt:
            choice = None
            spell_id = boost_prompt
            spell_data = SPELLS.get(spell_id, {})
            prompt_seconds = int(spell_data.get("boost_prompt_seconds", 3))
            prompt_text = spell_data.get("boost_prompt_text", "Boost {name}? (Y/N)")
            prompt_text = prompt_text.replace("{name}", spell_data.get("name", spell_id.title()))
            default_choice = str(spell_data.get("boost_default", "N")).lower()
            for remaining in range(prompt_seconds, 0, -1):
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
                    inn_mode,
                    spell_mode
                )
                render_frame(frame)
                choice = read_keypress_timeout(1.0)
                if choice and choice.lower() in ("y", "n"):
                    break
            ch = choice if choice else default_choice
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
        action_cmd = None
        handled_boost = False
        handled_by_router = False
        if boost_prompt:
            if ch.lower() not in ("y", "n"):
                last_message = "Choose Y or N to boost the spell."
                continue
            boosted = ch.lower() == "y"
            state = CommandState(
                player=player,
                opponents=opponents,
                loot_bank=loot_bank,
                last_message=last_message,
                shop_mode=shop_mode,
                inventory_mode=inventory_mode,
                inventory_items=inventory_items,
                hall_mode=hall_mode,
                hall_view=hall_view,
                inn_mode=inn_mode,
                spell_mode=spell_mode,
                action_cmd=action_cmd,
            )
            handle_boost_confirm(state, ROUTER_CTX, spell_id, boosted)
            last_message = state.last_message
            action_cmd = state.action_cmd
            boost_prompt = None
            handled_boost = True

        if not handled_boost:
            available_commands = None
            if title_mode:
                title_scene = SCENES.get("title", {})
                if getattr(player, "title_confirm", False):
                    available_commands = title_scene.get("confirm_commands", [])
                else:
                    available_commands = scene_commands(
                        SCENES,
                        COMMANDS_DATA,
                        "title",
                        player,
                        opponents
                    )
            elif inn_mode:
                venue = VENUES.get("town_inn", {})
                available_commands = venue.get("commands", [])
            elif not any(
                [
                    leveling_mode,
                    shop_mode,
                    inventory_mode,
                    hall_mode,
                    inn_mode,
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

        if cmd == "B_KEY" and not (shop_mode or hall_mode or inn_mode or spell_mode):
            continue
        if cmd == "X_KEY":
            continue

        state = CommandState(
            player=player,
            opponents=opponents,
            loot_bank=loot_bank,
            last_message=last_message,
            shop_mode=shop_mode,
            inventory_mode=inventory_mode,
            inventory_items=inventory_items,
            hall_mode=hall_mode,
            hall_view=hall_view,
            inn_mode=inn_mode,
            spell_mode=spell_mode,
            action_cmd=action_cmd,
        )
        if handle_command(cmd, state, ROUTER_CTX, key=ch):
            opponents = state.opponents
            loot_bank = state.loot_bank
            last_message = state.last_message
            shop_mode = state.shop_mode
            inventory_mode = state.inventory_mode
            inventory_items = state.inventory_items
            hall_mode = state.hall_mode
            hall_view = state.hall_view
            inn_mode = state.inn_mode
            spell_mode = state.spell_mode
            action_cmd = state.action_cmd
            if player.location == "Title" and state.player.location != "Title":
                title_mode = False
            player = state.player
            handled_by_router = True
            if action_cmd not in COMBAT_ACTIONS:
                continue
            if action_cmd in SPELL_COMMANDS:
                cmd = action_cmd
                handled_by_router = False

        if not handled_boost and not handled_by_router:
            spell_entry = SPELLS.by_command_id(cmd)
            if spell_entry:
                spell_id, spell = spell_entry
                name = spell.get("name", spell_id.title())
                if spell.get("requires_target") and not any(opponent.hp > 0 for opponent in opponents):
                    last_message = "There is nothing to target."
                    continue
                if spell_id == "healing" and player.hp == player.max_hp:
                    last_message = "Your HP is already full."
                    continue
                mp_cost = int(spell.get("mp_cost", 2))
                boosted_mp_cost = int(spell.get("boosted_mp_cost", mp_cost))
                if player.mp < mp_cost:
                    last_message = f"Not enough MP to cast {name}."
                    continue
                if player.mp >= boosted_mp_cost:
                    boost_prompt = spell_id
                    prompt = spell.get("boost_prompt_text", "Boost {name}? (Y/N)")
                    last_message = prompt.replace("{name}", name)
                    continue
                last_message = cast_spell(player, opponents, spell_id, boosted=False, loot=loot_bank, spells_data=SPELLS)
                action_cmd = cmd
            else:
                last_message = dispatch_command(
                    COMMANDS,
                    cmd,
                    CommandContext(
                        player=player,
                        opponents=opponents,
                        loot=loot_bank,
                        spells_data=SPELLS,
                        items_data=ITEMS,
                    ),
                )
                if cmd == "ATTACK":
                    action_cmd = "ATTACK"

        if player.needs_level_up() and not any(opponent.hp > 0 for opponent in opponents):
            leveling_mode = True

        if action_cmd in OFFENSIVE_ACTIONS:
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
        if action_cmd in COMBAT_ACTIONS and any(opponent.hp > 0 for opponent in opponents):
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
                    inn_mode,
                    spell_mode,
                    suppress_actions=True
                )
                render_frame(frame)
                time.sleep(battle_action_delay(player))
            acting = [(i, m) for i, m in enumerate(opponents) if m.hp > 0]
            for idx, (opp_index, m) in enumerate(acting):
                if m.stunned_turns > 0:
                    m.stunned_turns -= 1
                    template = TEXTS.get("battle", "opponent_stunned", "The {name} is stunned.")
                    last_message += " " + format_text(template, name=m.name)
                elif random.random() > m.action_chance:
                    template = TEXTS.get("battle", "opponent_hesitates", "The {name} hesitates.")
                    last_message += " " + format_text(template, name=m.name)
                else:
                    damage, crit, miss = roll_damage(m.atk, player.defense)
                    if miss:
                        template = TEXTS.get("battle", "opponent_miss", "The {name} misses you.")
                        last_message += " " + format_text(template, name=m.name)
                    else:
                        player.hp = max(0, player.hp - damage)
                        if crit:
                            template = TEXTS.get("battle", "opponent_crit", "Critical hit! The {name} hits you for {damage}.")
                            last_message += " " + format_text(template, name=m.name, damage=damage)
                        else:
                            template = TEXTS.get("battle", "opponent_hit", "The {name} hits you for {damage}.")
                            last_message += " " + format_text(template, name=m.name, damage=damage)
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
                        inn_mode,
                        spell_mode,
                        suppress_actions=True
                    )
                    render_frame(frame)
                    time.sleep(battle_action_delay(player))

        if player_defeated:
            SAVE_DATA.save_player(player)
            continue

        if action_cmd in OFFENSIVE_ACTIONS:
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
                    last_message = (
                        f"You gain {loot_bank['xp']} XP and "
                        f"{loot_bank['gold']} gold."
                    )
                    if player.needs_level_up():
                        leveling_mode = True
                else:
                    last_message = ""
                loot_bank = {"xp": 0, "gold": 0}

        if action_cmd in COMBAT_ACTIONS:
            SAVE_DATA.save_player(player)


if __name__ == "__main__":
    main()
