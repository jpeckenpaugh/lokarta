import shutil
import random
import time
from typing import List, Optional

from app.combat import (
    battle_action_delay,
    cast_spell,
    primary_opponent,
    primary_opponent_index,
    roll_damage,
)
from app.bootstrap import create_app
from app.commands.keymap import map_key_to_command
from app.commands.registry import CommandContext, dispatch_command
from app.commands.router import CommandState, handle_boost_confirm, handle_command
from app.commands.scene_commands import scene_commands
from app.input import read_keypress, read_keypress_timeout
from app.models import Player
from app.state import GameState
from app.ui.ansi import ANSI
from app.ui.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from app.ui.rendering import (
    clear_screen,
    animate_battle_end,
    animate_battle_start,
    flash_opponent,
    melt_opponent,
    render_frame,
)
from app.ui.screens import generate_frame
from app.ui.text import format_text

APP = create_app()
ITEMS = APP.items
OPPONENTS = APP.opponents
SCENES = APP.scenes
NPCS = APP.npcs
VENUES = APP.venues
SPELLS = APP.spells
COMMANDS_DATA = APP.commands_data
MENUS = APP.menus
TEXTS = APP.texts
SAVE_DATA = APP.save_data
COMMANDS = APP.registry
ROUTER_CTX = APP.router_ctx
SCREEN_CTX = APP.screen_ctx
SPELL_COMMANDS = APP.spell_commands
TARGETED_SPELL_COMMANDS = APP.targeted_spell_commands
FLASH_SPELL_COMMANDS = APP.flash_spell_commands
COMBAT_ACTIONS = APP.combat_actions
OFFENSIVE_ACTIONS = APP.offensive_actions
BATTLE_END_COMMANDS = APP.battle_end_commands






# -----------------------------
# Main loop
# -----------------------------

def main():
    cols, rows = shutil.get_terminal_size(fallback=(0, 0))
    if cols < SCREEN_WIDTH or rows < SCREEN_HEIGHT:
        print(f"WARNING: Terminal size is {cols}x{rows}. Recommended is 100x30.")
        print("Resize your terminal for best results.")
        input("Press Enter to continue anyway...")

    state = GameState(
        player=Player.from_dict({}),
        opponents=[],
        loot_bank={"xp": 0, "gold": 0},
        last_message="",
        leveling_mode=False,
        boost_prompt=None,
        shop_mode=False,
        inventory_mode=False,
        inventory_items=[],
        hall_mode=False,
        hall_view="menu",
        inn_mode=False,
        spell_mode=False,
        quit_confirm=False,
        title_mode=True,
    )
    state.player.location = "Title"
    def render_battle_pause(message: str):
        frame = generate_frame(
            SCREEN_CTX,
            state.player,
            state.opponents,
            message,
            state.leveling_mode,
            state.shop_mode,
            state.inventory_mode,
            state.inventory_items,
            state.hall_mode,
            state.hall_view,
            state.inn_mode,
            state.spell_mode,
            suppress_actions=True
        )
        render_frame(frame)
        time.sleep(battle_action_delay(state.player))

    while True:
        if state.title_mode:
            state.player.has_save = SAVE_DATA.exists()
        if state.inventory_mode:
            state.inventory_items = state.player.list_inventory_items(ITEMS)
        frame = generate_frame(
            SCREEN_CTX,
            state.player,
            state.opponents,
            state.last_message,
            state.leveling_mode,
            state.shop_mode,
            state.inventory_mode,
            state.inventory_items,
            state.hall_mode,
            state.hall_view,
            state.inn_mode,
            state.spell_mode
        )
        render_frame(frame)

        if state.boost_prompt:
            choice = None
            spell_id = state.boost_prompt
            spell_data = SPELLS.get(spell_id, {})
            prompt_seconds = int(spell_data.get("boost_prompt_seconds", 3))
            prompt_text = spell_data.get("boost_prompt_text", "Boost {name}? (Y/N)")
            prompt_text = prompt_text.replace("{name}", spell_data.get("name", spell_id.title()))
            default_choice = str(spell_data.get("boost_default", "N")).lower()
            for remaining in range(prompt_seconds, 0, -1):
                countdown_message = f"{state.last_message} ({remaining})"
                frame = generate_frame(
                    SCREEN_CTX,
                    state.player,
                    state.opponents,
                    countdown_message,
                    state.leveling_mode,
                    state.shop_mode,
                    state.inventory_mode,
                    state.inventory_items,
                    state.hall_mode,
                    state.hall_view,
                    state.inn_mode,
                    state.spell_mode
                )
                render_frame(frame)
                choice = read_keypress_timeout(1.0)
                if choice and choice.lower() in ("y", "n"):
                    break
            ch = choice if choice else default_choice
        else:
            ch = read_keypress()
        if state.quit_confirm:
            if ch.lower() == "y":
                SAVE_DATA.save_player(state.player)
                clear_screen()
                print("Goodbye.")
                return
            if ch.lower() == "n":
                state.quit_confirm = False
                state.last_message = "Quit cancelled."
                continue
            state.last_message = "Quit? (Y/N)"
            continue
        action_cmd = None
        command_meta = None
        handled_boost = False
        handled_by_router = False
        if state.boost_prompt:
            if ch.lower() not in ("y", "n"):
                state.last_message = "Choose Y or N to boost the spell."
                continue
            boosted = ch.lower() == "y"
            cmd_state = CommandState(
                player=state.player,
                opponents=state.opponents,
                loot_bank=state.loot_bank,
                last_message=state.last_message,
                shop_mode=state.shop_mode,
                inventory_mode=state.inventory_mode,
                inventory_items=state.inventory_items,
                hall_mode=state.hall_mode,
                hall_view=state.hall_view,
                inn_mode=state.inn_mode,
                spell_mode=state.spell_mode,
                action_cmd=action_cmd,
            )
            handle_boost_confirm(cmd_state, ROUTER_CTX, spell_id, boosted)
            state.last_message = cmd_state.last_message
            action_cmd = cmd_state.action_cmd
            state.boost_prompt = None
            handled_boost = True

        if not handled_boost:
            available_commands = None
            if state.title_mode:
                title_scene = SCENES.get("title", {})
                if getattr(state.player, "title_confirm", False):
                    available_commands = title_scene.get("confirm_commands", [])
                else:
                    available_commands = scene_commands(
                        SCENES,
                        COMMANDS_DATA,
                        "title",
                        state.player,
                        state.opponents
                    )
            elif state.inn_mode:
                venue = VENUES.get("town_inn", {})
                available_commands = venue.get("commands", [])
            elif not any(
                [
                    state.leveling_mode,
                    state.shop_mode,
                    state.inventory_mode,
                    state.hall_mode,
                    state.inn_mode,
                    state.spell_mode,
                    state.boost_prompt,
                ]
            ):
                scene_id = "town" if state.player.location == "Town" else "forest"
                available_commands = scene_commands(
                    SCENES,
                    COMMANDS_DATA,
                    scene_id,
                    state.player,
                    state.opponents
                )
            cmd = map_key_to_command(ch, available_commands)
            if available_commands and cmd:
                command_meta = next(
                    (entry for entry in available_commands if entry.get("command") == cmd),
                    None
                )
        else:
            cmd = None

        if cmd == "QUIT":
            state.quit_confirm = True
            state.last_message = "Quit? (Y/N)"
            continue

        if cmd is None and not handled_boost:
            continue

        if state.leveling_mode and not handled_boost:
            state.last_message, leveling_done = state.player.handle_level_up_input(cmd)
            if leveling_done:
                state.leveling_mode = False
            continue

        if cmd == "B_KEY" and not (state.shop_mode or state.hall_mode or state.inn_mode or state.spell_mode or state.inventory_mode):
            continue
        if cmd == "X_KEY":
            continue

        cmd_state = CommandState(
            player=state.player,
            opponents=state.opponents,
            loot_bank=state.loot_bank,
            last_message=state.last_message,
            shop_mode=state.shop_mode,
            inventory_mode=state.inventory_mode,
            inventory_items=state.inventory_items,
            hall_mode=state.hall_mode,
            hall_view=state.hall_view,
            inn_mode=state.inn_mode,
            spell_mode=state.spell_mode,
            action_cmd=action_cmd,
        )
        if handle_command(cmd, cmd_state, ROUTER_CTX, key=ch):
            state.opponents = cmd_state.opponents
            state.loot_bank = cmd_state.loot_bank
            state.last_message = cmd_state.last_message
            state.shop_mode = cmd_state.shop_mode
            state.inventory_mode = cmd_state.inventory_mode
            state.inventory_items = cmd_state.inventory_items
            state.hall_mode = cmd_state.hall_mode
            state.hall_view = cmd_state.hall_view
            state.inn_mode = cmd_state.inn_mode
            state.spell_mode = cmd_state.spell_mode
            action_cmd = cmd_state.action_cmd
            if state.player.location == "Title" and cmd_state.player.location != "Title":
                state.title_mode = False
            state.player = cmd_state.player
            handled_by_router = True
            if command_meta and command_meta.get("anim") == "battle_start" and state.opponents:
                animate_battle_start(
                    SCENES,
                    COMMANDS_DATA,
                    "forest",
                    state.player,
                    state.opponents,
                    state.last_message
                )
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
                if spell.get("requires_target") and not any(opponent.hp > 0 for opponent in state.opponents):
                    state.last_message = "There is nothing to target."
                    continue
                if spell_id == "healing" and state.player.hp == state.player.max_hp:
                    state.last_message = "Your HP is already full."
                    continue
                mp_cost = int(spell.get("mp_cost", 2))
                boosted_mp_cost = int(spell.get("boosted_mp_cost", mp_cost))
                if state.player.mp < mp_cost:
                    state.last_message = f"Not enough MP to cast {name}."
                    continue
                if state.player.mp >= boosted_mp_cost:
                    state.boost_prompt = spell_id
                    prompt = spell.get("boost_prompt_text", "Boost {name}? (Y/N)")
                    state.last_message = prompt.replace("{name}", name)
                    continue
                state.last_message = cast_spell(state.player, state.opponents, spell_id, boosted=False, loot=state.loot_bank, spells_data=SPELLS)
                action_cmd = cmd
            else:
                state.last_message = dispatch_command(
                    COMMANDS,
                    cmd,
                    CommandContext(
                        player=state.player,
                        opponents=state.opponents,
                        loot=state.loot_bank,
                        spells_data=SPELLS,
                        items_data=ITEMS,
                    ),
                )
                if command_meta and command_meta.get("type") == "combat":
                    action_cmd = cmd
                if command_meta and command_meta.get("anim") == "battle_start":
                    action_cmd = cmd

        if state.player.needs_level_up() and not any(opponent.hp > 0 for opponent in state.opponents):
            state.leveling_mode = True

        if action_cmd in OFFENSIVE_ACTIONS:
            target_index = primary_opponent_index(state.opponents)
            flash_opponent(
                SCENES,
                COMMANDS_DATA,
                "forest",
                state.player,
                state.opponents,
                state.last_message,
                target_index,
                ANSI.FG_YELLOW
            )
            defeated_indices = [
                i for i, m in enumerate(state.opponents)
                if m.hp <= 0 and not m.melted
            ]
            for index in defeated_indices:
                melt_opponent(
                    SCENES,
                    COMMANDS_DATA,
                    "forest",
                    state.player,
                    state.opponents,
                    state.last_message,
                    index
                )
                state.opponents[index].melted = True

        player_defeated = False
        if action_cmd in COMBAT_ACTIONS and any(opponent.hp > 0 for opponent in state.opponents):
            if state.player.location == "Forest":
                render_battle_pause(state.last_message)
            acting = [(i, m) for i, m in enumerate(state.opponents) if m.hp > 0]
            for idx, (opp_index, m) in enumerate(acting):
                if m.stunned_turns > 0:
                    m.stunned_turns -= 1
                    template = TEXTS.get("battle", "opponent_stunned", "The {name} is stunned.")
                    state.last_message += " " + format_text(template, name=m.name)
                elif random.random() > m.action_chance:
                    template = TEXTS.get("battle", "opponent_hesitates", "The {name} hesitates.")
                    state.last_message += " " + format_text(template, name=m.name)
                else:
                    damage, crit, miss = roll_damage(m.atk, state.player.defense)
                    if miss:
                        template = TEXTS.get("battle", "opponent_miss", "The {name} misses you.")
                        state.last_message += " " + format_text(template, name=m.name)
                    else:
                        state.player.hp = max(0, state.player.hp - damage)
                        if crit:
                            template = TEXTS.get("battle", "opponent_crit", "Critical hit! The {name} hits you for {damage}.")
                            state.last_message += " " + format_text(template, name=m.name, damage=damage)
                        else:
                            template = TEXTS.get("battle", "opponent_hit", "The {name} hits you for {damage}.")
                            state.last_message += " " + format_text(template, name=m.name, damage=damage)
                    flash_opponent(
                        SCENES,
                        COMMANDS_DATA,
                        "forest",
                        state.player,
                        state.opponents,
                        state.last_message,
                        opp_index,
                        ANSI.FG_RED
                    )
                    if state.player.hp == 0:
                        lost_gp = state.player.gold // 2
                        state.player.gold -= lost_gp
                        state.player.location = "Town"
                        state.player.hp = state.player.max_hp
                        state.player.mp = state.player.max_mp
                        state.opponents = []
                        state.loot_bank = {"xp": 0, "gold": 0}
                        state.last_message = (
                            "You were defeated and wake up at the inn. "
                            f"You lost {lost_gp} GP."
                        )
                        player_defeated = True
                        break
                if state.player.location == "Forest" and idx < len(acting) - 1:
                    render_battle_pause(state.last_message)

        if player_defeated:
            SAVE_DATA.save_player(state.player)
            continue

        if action_cmd in OFFENSIVE_ACTIONS:
            if not any(opponent.hp > 0 for opponent in state.opponents):
                if BATTLE_END_COMMANDS:
                    animate_battle_end(
                        SCENES,
                        COMMANDS_DATA,
                        "forest",
                        state.player,
                        state.opponents,
                        state.last_message
                    )
                state.opponents = []
                if state.loot_bank["xp"] or state.loot_bank["gold"]:
                    state.player.gain_xp(state.loot_bank["xp"])
                    state.player.gold += state.loot_bank["gold"]
                    state.last_message = (
                        f"You gain {state.loot_bank['xp']} XP and "
                        f"{state.loot_bank['gold']} gold."
                    )
                    if state.player.needs_level_up():
                        state.leveling_mode = True
                else:
                    state.last_message = ""
                state.loot_bank = {"xp": 0, "gold": 0}

        if action_cmd in COMBAT_ACTIONS:
            SAVE_DATA.save_player(state.player)


if __name__ == "__main__":
    main()
