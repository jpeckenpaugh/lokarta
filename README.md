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

---

## Screen Layout Contract (100x30)

Top to bottom:
- Top border (1)
- Title panel line (centered) (1)
- Separator border (1)
- Body area (21)
  - Art block (10)
  - Divider (1)
  - Narrative block (remaining) with a centered Status line at the bottom
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

Town:
- `I` Inn (Rest, 10 GP) — only shown when HP/MP not full
- `H` Hall (info on opponents/items)
- `S` Shop
- `O` Open Inventory
- `F` Set out for the Forest
- `Q` Quit

Forest:
- `A` Attack
- `M` Magic (Spellbook)
- `O` Open Inventory
- `F` Find an opponent to fight
- `T` Return to Town
- `Q` Quit

Menus:
- Shop: `1` Rations, `2` Elixir, `B` Back, `Q` Quit
- Hall: `1` Opponents, `2` Items, `B` Back, `Q` Quit
- Spellbook: `1` Healing, `2` Spark, `B` Back, `Q` Quit
- Inventory: `1-9` Use item, `B` Back, `Q` Quit
- Level Up: `1-4` allocate stats, `B` Balanced, `X` Random

---

## Assets

Game data is externalized into JSON:
- `data/opponents.json` — opponent stats, art, descriptions
- `data/items.json` — item effects, prices, descriptions
- `data/scenes.json` — scene art and colors
- `data/npcs.json` — NPC names and dialog snippets
- `data/venues.json` — venue metadata and NPC links

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
