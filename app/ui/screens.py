"""Screen composition helpers for game UI states."""

import textwrap
from dataclasses import dataclass
from typing import List, Optional

from app.commands.scene_commands import scene_commands
from app.data_access.commands_data import CommandsData
from app.data_access.items_data import ItemsData
from app.data_access.menus_data import MenusData
from app.data_access.npcs_data import NpcsData
from app.data_access.opponents_data import OpponentsData
from app.data_access.scenes_data import ScenesData
from app.data_access.spells_data import SpellsData
from app.data_access.venues_data import VenuesData
from app.data_access.text_data import TextData
from app.models import Frame, Player, Opponent
from app.ui.ansi import ANSI
from app.ui.layout import format_action_lines, format_command_lines, format_menu_actions
from app.ui.constants import SCREEN_WIDTH
from app.ui.rendering import (
    COLOR_BY_NAME,
    format_player_stats,
    render_scene_art,
    render_venue_art,
)
from app.ui.text import format_text


@dataclass
class ScreenContext:
    items: ItemsData
    opponents: OpponentsData
    scenes: ScenesData
    npcs: NpcsData
    venues: VenuesData
    menus: MenusData
    commands: CommandsData
    spells: SpellsData
    text: TextData


def generate_frame(
    ctx: ScreenContext,
    player: Player,
    opponents: List[Opponent],
    message: str = "",
    leveling_mode: bool = False,
    shop_mode: bool = False,
    inventory_mode: bool = False,
    inventory_items: Optional[List[tuple[str, str]]] = None,
    hall_mode: bool = False,
    hall_view: str = "menu",
    inn_mode: bool = False,
    spell_mode: bool = False,
    suppress_actions: bool = False
) -> Frame:
    """Build a screen frame from game state and UI data."""
    healing = ctx.spells.get("healing", {})
    spark = ctx.spells.get("spark", {})
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
        venue = ctx.venues.get("town_shop", {})
        npc_lines = []
        npc_ids = venue.get("npc_ids", [])
        npc = {}
        if npc_ids:
            npc_lines = ctx.npcs.format_greeting(npc_ids[0])
            npc = ctx.npcs.get(npc_ids[0], {})
        body = []
        if npc_lines:
            body += npc_lines + [""]
        for entry in venue.get("inventory_items", []):
            item_id = entry.get("item_id")
            if not item_id:
                continue
            item = ctx.items.get(item_id, {})
            label = entry.get("label", item.get("name", item_id))
            price = item.get("price", 0)
            body.append(f"{label}  {price} GP")
        body.append("")
        body += venue.get("narrative", [])
        art_lines, art_color = render_venue_art(venue, npc)
        actions = format_command_lines(venue.get("commands", []))
    elif player.location == "Town" and hall_mode:
        venue = ctx.venues.get("town_hall", {})
        info_sections = venue.get("info_sections", [])
        npc_lines = []
        npc_ids = venue.get("npc_ids", [])
        npc = {}
        if npc_ids:
            npc_lines = ctx.npcs.format_greeting(npc_ids[0])
            npc = ctx.npcs.get(npc_ids[0], {})
        section = next((entry for entry in info_sections if entry.get("key") == hall_view), None)
        source = section.get("source") if section else None
        if source == "items":
            info_lines = ctx.items.list_descriptions()
        elif source == "opponents":
            info_lines = ctx.opponents.list_descriptions()
        else:
            info_lines = []
        body = []
        if npc_lines:
            body += npc_lines + [""]
        body += info_lines
        body += venue.get("narrative", [])
        actions = format_command_lines(venue.get("commands", []))
        art_lines, art_color = render_venue_art(venue, npc)
    elif player.location == "Town" and inn_mode:
        venue = ctx.venues.get("town_inn", {})
        npc_lines = []
        npc_ids = venue.get("npc_ids", [])
        npc = {}
        if npc_ids:
            npc_lines = ctx.npcs.format_greeting(npc_ids[0])
            npc = ctx.npcs.get(npc_ids[0], {})
        body = []
        if npc_lines:
            body += npc_lines + [""]
        body += venue.get("narrative", [])
        actions = format_command_lines(venue.get("commands", []))
        art_lines, art_color = render_venue_art(venue, npc)
    elif inventory_mode:
        inventory_menu = ctx.menus.get("inventory", {})
        items = inventory_items or []
        title = inventory_menu.get("title", "Inventory")
        body = [title, ""]
        if items:
            for i, (_, label) in enumerate(items[:9], start=1):
                body.append(f"{i}. {label}")
        else:
            body.append(inventory_menu.get("empty", "Inventory is empty."))
        actions = format_menu_actions(inventory_menu)
        art_lines = []
        art_color = ANSI.FG_WHITE
    elif spell_mode:
        spell_menu = ctx.menus.get("spellbook", {})
        heal_cost = int(healing.get("mp_cost", 2))
        spark_cost = int(spark.get("mp_cost", 2))
        body = [
            spell_menu.get("title", "Spellbook"),
            "",
            f"{heal_name} ({heal_cost} MP)",
            f"{spark_name} ({spark_cost} MP)",
        ]
        actions = format_menu_actions(
            spell_menu,
            replacements={
                "{heal_name}": heal_name,
                "{spark_name}": spark_name,
            },
        )
        art_lines = []
        art_color = ANSI.FG_WHITE
    elif player.location == "Town":
        scene_data = ctx.scenes.get("town", {})
        art_lines = scene_data.get("art", [])
        art_color = COLOR_BY_NAME.get(scene_data.get("color", "yellow").lower(), ANSI.FG_WHITE)
        body = scene_data.get("narrative", [])
        actions = format_command_lines(
            scene_commands(ctx.scenes, ctx.commands, "town", player, opponents)
        )
    elif player.location == "Title":
        scene_data = ctx.scenes.get("title", {})
        art_lines = scene_data.get("art", [])
        art_color = COLOR_BY_NAME.get(scene_data.get("color", "cyan").lower(), ANSI.FG_WHITE)
        if getattr(player, "title_confirm", False):
            body = scene_data.get("confirm_narrative", [])
            actions = format_command_lines(scene_data.get("confirm_commands", []))
        else:
            body = scene_data.get("narrative", [])
            actions = format_command_lines(
                scene_commands(ctx.scenes, ctx.commands, "title", player, opponents)
            )
    else:
        scene_data = ctx.scenes.get("forest", {})
        forest_art, art_color = render_scene_art(scene_data, opponents)
        alive = [o for o in opponents if o.hp > 0]
        default_text = ctx.text.get("battle", "quiet", "All is quiet. No enemies in sight.")
        default_narrative = scene_data.get("narrative", [default_text])
        if alive:
            if len(alive) > 1:
                arrival = ctx.text.get("battle", "opponent_arrival_plural", "Opponents emerge from the forest.")
                body = [arrival]
            else:
                primary = alive[0]
                arrival = ctx.text.get("battle", "opponent_arrival", "A {name} {arrival}.")
                body = [format_text(arrival, name=primary.name, arrival=primary.arrival)]
        else:
            body = [*default_narrative]
        if message:
            lines = [line for line in message.splitlines() if line.strip() != ""]
            if lines:
                if body and lines and lines[0].startswith("A ") and lines[0].endswith("."):
                    lines = []
                body += lines
        actions = format_command_lines(
            scene_commands(ctx.scenes, ctx.commands, "forest", player, opponents)
        )
        art_lines = forest_art

    if player.location == "Forest":
        status_lines = []
    elif message and "\n" in message:
        status_lines = [line for line in message.splitlines() if line.strip() != ""]
    else:
        status_lines = (
            textwrap.wrap(message, width=SCREEN_WIDTH - 4)
            if message
            else []
        )

    return Frame(
        title="World Builder — PROTOTYPE",
        body_lines=body,
        action_lines=(format_action_lines([]) if suppress_actions else actions),
        stat_lines=format_player_stats(player),
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
