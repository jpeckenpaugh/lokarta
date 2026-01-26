# World Builder — Local Terminal POC

## Overview

This project is a **local-first proof of concept** for a retro, BBS-style ASCII RPG. The goal is to validate:
- screen layout
- rendering approach
- input model
- engine/UI separation

Once validated locally, the same engine and assets can be migrated to:
- a web-based terminal UI
- an SSH-based BBS-style interface

---

## Design Goals

- Fixed-size ASCII screen (**100 columns × 30 rows**)
- Deterministic rendering (no scrolling UI)
- Single-key input (no Enter required)
- Nostalgic presentation with modern code structure
- Clean separation between game logic and presentation

---

## Code Structure

- `main.py` — game loop and state orchestration
- `app/bootstrap.py` — app initialization and wiring
- `app/config.py` — filesystem paths and config
- `app/models.py` — core dataclasses (`Player`, `Opponent`, `Frame`)
- `app/combat.py` — combat helpers and timing
- `app/input.py` — single-key input handling
- `app/shop.py` — shop interaction helpers
- `app/commands/` — command registry and command modules
- `app/loop.py` — main loop helper functions
- `app/ui/` — layout, rendering, and screen composition helpers
- `app/data_access/` — JSON data loaders
- `data/` — JSON content packs
- `saves/` — local save slots
- `docs/` — schema and design notes
- `tests/` — unit tests

---

## Current Features

- Title screen with Continue/New/Quit and save overwrite confirmation
- Persistent save file (`saves/slot1.json`)
- ANSI color rendering and ASCII scene art
- Town hub with Inn, Shop, Hall, and Inventory
- Spellbook (Healing / Spark) and boosted casting prompts
- Items (Rations, Elixir) and purchasing via the shop
- Inventory item usage with numbered selection
- Multi-opponent encounters (up to 3) with level-budget spawns
- Combat with variance, crits, misses, and Spark stun
- Leveling: +10 stat points per level, allocation screen, auto-heal
- Boosted spell prompts auto-time out after 3 seconds

---

## Screen Layout Contract (100x30)

Top to bottom:
- Top border (1)
- Location line (centered) (1)
- Separator border (1)
- Body area (variable)
  - Art block (if present)
  - Divider (if art present)
  - Narrative block with status lines
- Actions panel header (1)
- Actions panel content (3, auto-columns)
- Player stats header (1)
- Player stats (2)
- Bottom border (1)

---

## Controls

Title Screen:
- `C` Continue (if save exists)
- `N` New Game (confirm overwrite if save exists)
- `Q` Quit
- `Y/N` confirm/cancel overwrite

Town/Forest/Menus:
- Controls are data-driven from `data/commands.json`, `data/scenes.json`,
  `data/venues.json`, and `data/menus.json`.
- The action panel reflects the active commands and their conditions.
- Command schema notes: `docs/commands.md`.
- Boost prompts and timing are driven by `data/spells.json`.

---

## Assets

Game data is externalized into JSON:
- `data/opponents.json` — opponent stats, art, descriptions
- `data/items.json` — item effects, prices, descriptions
- `data/scenes.json` — scene art and colors
- `data/npcs.json` — NPC names and dialog snippets
- `data/venues.json` — venue metadata and NPC links
- `data/spells.json` — spell definitions and costs
- `data/commands.json` — global action commands
- `data/menus.json` — inventory/spellbook UI text and actions
- `data/text.json` — message templates for battle text

---

## Running the POC

1. Resize your terminal to **at least 100 columns × 30 rows**
2. Run:

```bash
python3 main.py
```

---

## Platform Support

### Currently Supported
- macOS terminal
- Linux terminal
- Windows terminal (uses `msvcrt.getch()` for single-key input)

### Not Yet Supported
- Web UI
- SSH/BBS frontend

---

## Status

This repository represents an **exploratory prototype**.
Expect rapid iteration, breaking changes, and intentional simplicity.
