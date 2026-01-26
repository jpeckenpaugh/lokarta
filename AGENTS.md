# AGENTS.md

## Project Overview
- Terminal-based ASCII RPG prototype.
- Main entry: `main.py`.
- Data assets: `data/opponents.json`, `data/items.json`, `data/scenes.json`, `data/npcs.json`, `data/venues.json`.
- Save file: `saves/slot1.json` (generated at runtime).

## Conventions
- Keep UI within 100x30 layout constraints.
- Single-key input only; no Enter prompts during gameplay.
- Town/Forest actions are listed in the Actions panel.
- Spells are accessed via the Spellbook (Magic).
- Persist changes to player state via `save_game()`.

## Editing Guidelines
- Update JSON assets instead of hardcoding data.
- Avoid introducing non-ASCII characters unless already used.
- Keep UI text concise to avoid truncation.

## Quick Start
- Run: `python3 main.py`.
- If testing UI changes, ensure terminal size >= 100x30.
