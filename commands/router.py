"""Command router for stateful, data-driven actions."""

from dataclasses import dataclass
from typing import List, Optional

from combat import primary_opponent
from data_access.commands_data import CommandsData
from data_access.items_data import ItemsData
from data_access.opponents_data import OpponentsData
from data_access.scenes_data import ScenesData
from data_access.venues_data import VenuesData
from data_access.save_data import SaveData
from models import Player, Opponent
from commands.registry import CommandContext, CommandRegistry, dispatch_command
from data_access.spells_data import SpellsData
from shop import purchase_item
from ui.ansi import ANSI
from ui.rendering import animate_battle_start


@dataclass
class CommandState:
    player: Player
    opponents: List[Opponent]
    loot_bank: dict
    last_message: str
    shop_mode: bool
    inventory_mode: bool
    inventory_items: List[tuple[str, str]]
    hall_mode: bool
    hall_view: str
    spell_mode: bool
    action_cmd: Optional[str]


@dataclass
class RouterContext:
    items: ItemsData
    opponents_data: OpponentsData
    scenes: ScenesData
    commands: CommandsData
    venues: VenuesData
    save_data: SaveData
    spells: SpellsData
    registry: CommandRegistry


def handle_command(command_id: str, state: CommandState, ctx: RouterContext, key: Optional[str] = None) -> bool:
    if command_id is None:
        return False

    if command_id == "ENTER_VENUE":
        venue_id = _command_target(ctx.scenes, ctx.commands, state, command_id, key)
        if not venue_id:
            return False
        venue = ctx.venues.get(venue_id, {})
        if venue_id == "town_shop":
            state.shop_mode = True
            state.hall_mode = False
            state.inventory_mode = False
            state.spell_mode = False
        elif venue_id == "town_hall":
            state.hall_mode = True
            state.hall_view = "menu"
            state.shop_mode = False
            state.inventory_mode = False
            state.spell_mode = False
        else:
            return False
        state.last_message = venue.get("welcome_message", state.last_message)
        return True

    if command_id == "ENTER_SCENE":
        scene_id = _command_target(ctx.scenes, ctx.commands, state, command_id, key)
        if not scene_id:
            return False
        return _enter_scene(scene_id, state, ctx)

    if command_id == "B_KEY" and state.inventory_mode:
        state.inventory_mode = False
        state.last_message = "Closed inventory."
        return True

    if command_id == "B_KEY" and state.spell_mode:
        state.spell_mode = False
        state.last_message = "Closed spellbook."
        return True
    if command_id == "SPELLBOOK":
        state.spell_mode = True
        state.shop_mode = False
        state.inventory_mode = False
        state.hall_mode = False
        state.last_message = "Open spellbook."
        return True

    if state.spell_mode and command_id in ("NUM1", "NUM2"):
        state.spell_mode = False
        if command_id == "NUM1":
            state.action_cmd = "HEAL"
        else:
            state.action_cmd = "SPARK"
        return True

    if command_id in ("NUM1", "NUM2") and state.hall_mode:
        venue = ctx.venues.get("town_hall", {})
        info_sections = venue.get("info_sections", [])
        selected = next(
            (entry for entry in info_sections if entry.get("command") == command_id),
            None
        )
        if selected:
            state.hall_view = selected.get("key", state.hall_view)
            state.last_message = selected.get("message", state.last_message)
            return True
        return False

    if command_id == "B_KEY" and state.hall_mode:
        venue = ctx.venues.get("town_hall", {})
        state.hall_mode = False
        state.last_message = venue.get("leave_message", "You leave the hall.")
        return True

    if command_id == "B_KEY" and state.shop_mode:
        venue = ctx.venues.get("town_shop", {})
        state.shop_mode = False
        state.last_message = venue.get("leave_message", "You leave the shop.")
        return True

    if state.shop_mode:
        venue = ctx.venues.get("town_shop", {})
        selection = next(
            (entry for entry in venue.get("inventory_items", []) if entry.get("command") == command_id),
            None
        )
        if selection:
            item_id = selection.get("item_id")
            if item_id:
                state.last_message = purchase_item(state.player, ctx.items, item_id)
                ctx.save_data.save_player(state.player)
            return True
        return False

    if command_id == "INVENTORY":
        state.inventory_items = state.player.list_inventory_items(ctx.items)
        if not state.inventory_items:
            state.last_message = "Inventory is empty."
            return True
        state.inventory_mode = True
        state.shop_mode = False
        state.hall_mode = False
        state.spell_mode = False
        state.last_message = "Choose an item to use."
        return True

    if command_id == "REST":
        if state.player.location != "Town":
            state.last_message = "The inn is only in town."
            return True
        if state.player.gold < 10:
            state.last_message = "Not enough GP to rest at the inn."
            return True
        state.player.gold -= 10
        state.player.hp = state.player.max_hp
        state.player.mp = state.player.max_mp
        state.last_message = "You rest at the inn and feel fully restored."
        ctx.save_data.save_player(state.player)
        return True

    ctx_data = CommandContext(
        player=state.player,
        opponents=state.opponents,
        loot=state.loot_bank,
        spells_data=ctx.spells,
        items_data=ctx.items,
    )
    message = dispatch_command(ctx.registry, command_id, ctx_data)
    if message != "Unknown action.":
        state.last_message = message
        if command_id in ("ATTACK", "SPARK", "HEAL"):
            state.action_cmd = command_id
        return True

    return False


def _command_target(
    scenes_data: ScenesData,
    commands_data: CommandsData,
    state: CommandState,
    command_id: str,
    key: Optional[str]
) -> Optional[str]:
    from commands.scene_commands import scene_commands
    scene_id = "town" if state.player.location == "Town" else "forest"
    commands_list = scene_commands(
        scenes_data,
        commands_data,
        scene_id,
        state.player,
        state.opponents,
    )
    for command in commands_list:
        if command.get("command") != command_id:
            continue
        if key:
            cmd_key = str(command.get("key", "")).lower()
            if cmd_key and cmd_key != key.lower():
                continue
        return command.get("target")
    return None


def _enter_scene(scene_id: str, state: CommandState, ctx: RouterContext) -> bool:
    if scene_id == "town":
        if state.player.location == "Town":
            state.last_message = "You are already in town."
            return True
        state.player.location = "Town"
        state.opponents = []
        state.loot_bank = {"xp": 0, "gold": 0}
        state.shop_mode = False
        state.inventory_mode = False
        state.hall_mode = False
        state.spell_mode = False
        state.last_message = "You return to town."
        ctx.save_data.save_player(state.player)
        return True
    if scene_id == "forest":
        if state.player.location != "Forest":
            state.player.location = "Forest"
            state.opponents = ctx.opponents_data.spawn(state.player.level, ANSI.FG_CYAN)
            state.loot_bank = {"xp": 0, "gold": 0}
            if state.opponents:
                state.last_message = f"A {state.opponents[0].name} appears."
                animate_battle_start(ctx.scenes, ctx.commands, "forest", state.player, state.opponents, state.last_message)
            else:
                state.last_message = "All is quiet. No enemies in sight."
            state.shop_mode = False
            state.inventory_mode = False
            state.hall_mode = False
            state.spell_mode = False
            ctx.save_data.save_player(state.player)
            return True

        primary = primary_opponent(state.opponents)
        if primary:
            state.last_message = f"You are already facing a {primary.name}."
            ctx.save_data.save_player(state.player)
            return True

        state.opponents = ctx.opponents_data.spawn(state.player.level, ANSI.FG_CYAN)
        state.loot_bank = {"xp": 0, "gold": 0}
        if state.opponents:
            state.last_message = f"A {state.opponents[0].name} appears."
            animate_battle_start(ctx.scenes, ctx.commands, "forest", state.player, state.opponents, state.last_message)
        else:
            state.last_message = "All is quiet. No enemies in sight."
        ctx.save_data.save_player(state.player)
        return True
    return False
