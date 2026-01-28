import shutil
import os
import sys
from typing import Optional

if os.name != 'nt':
    import termios

from app.bootstrap import create_app
from app.loop import (
    apply_boost_confirm,
    apply_router_command,
    handle_battle_end,
    handle_offensive_action,
    map_input_to_command,
    maybe_begin_target_select,
    read_input,
    render_frame_state,
    run_target_select,
    run_opponent_turns,
    resolve_player_action,
)
from app.input import read_keypress, read_keypress_timeout
from app.models import Player
from app.state import GameState
from app.ui.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from app.ui.rendering import clear_screen, render_frame
from app.ui.screens import generate_frame

APP = create_app()
ITEMS = APP.items
SAVE_DATA = APP.save_data

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

    if os.name != 'nt':
        termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)

    while True:
        if state.title_mode:
            state.player.has_save = SAVE_DATA.exists()
        if state.inventory_mode:
            state.inventory_items = state.player.list_inventory_items(ITEMS)
        render_frame_state(APP, render_frame, state, generate_frame)
        ch = read_input(APP, render_frame, state, generate_frame, read_keypress, read_keypress_timeout)
        action_cmd = None
        command_meta = None
        handled_by_router = False
        handled_boost, action_cmd, should_continue = apply_boost_confirm(APP, state, ch, action_cmd)
        if should_continue:
            continue
        cmd = None
        if not handled_boost:
            cmd, command_meta = map_input_to_command(APP, state, ch)

        if cmd == "QUIT":
            if state.title_mode or state.player.location == "Title":
                SAVE_DATA.save_player(state.player)
                clear_screen()
                print("Goodbye.")
                return
            state.title_mode = True
            state.player.location = "Title"
            state.player.title_confirm = False
            state.leveling_mode = False
            state.boost_prompt = None
            state.shop_mode = False
            state.inventory_mode = False
            state.inventory_items = []
            state.hall_mode = False
            state.hall_view = "menu"
            state.inn_mode = False
            state.spell_mode = False
            state.target_select = False
            state.target_index = None
            state.target_command = None
            state.opponents = []
            state.loot_bank = {"xp": 0, "gold": 0}
            state.battle_log = []
            state.last_message = ""
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

        if maybe_begin_target_select(APP, state, cmd):
            confirmed = run_target_select(APP, render_frame, state, generate_frame, read_keypress_timeout)
            if not confirmed:
                continue
            cmd = confirmed

        handled_by_router, action_cmd, cmd, should_continue = apply_router_command(
            APP,
            state,
            cmd,
            ch,
            command_meta,
            action_cmd,
        )
        if should_continue:
            continue

        action_cmd = resolve_player_action(
            APP,
            state,
            cmd,
            command_meta,
            action_cmd,
            handled_boost,
            handled_by_router,
        )
        if state.boost_prompt:
            continue
        if action_cmd:
            state.target_index = None
            state.target_command = None

        if state.player.needs_level_up() and not any(opponent.hp > 0 for opponent in state.opponents):
            state.leveling_mode = True

        handle_offensive_action(APP, state, action_cmd)

        player_defeated = run_opponent_turns(APP, render_frame, state, generate_frame, action_cmd)

        if player_defeated:
            SAVE_DATA.save_player(state.player)
            continue

        handle_battle_end(APP, state, action_cmd)

        if action_cmd in APP.combat_actions:
            SAVE_DATA.save_player(state.player)


if __name__ == "__main__":
    main()
