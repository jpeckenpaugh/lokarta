# Architecture Overview

## Runtime Flow

- `main.py` owns the game loop and user input.
- `app/bootstrap.py` creates an `AppContext` that wires data loaders, command registry, and UI contexts.
- `app/config.py` holds file path configuration (`data/`, `saves/`).

## Key Modules

- `app/data_access/` loads JSON content packs (scenes, opponents, items, commands, menus).
- `app/commands/` hosts the command registry, router, and command helpers.
- `app/ui/` builds frames, renders ASCII art, and handles animations.
- `app/combat.py` handles combat math and spell resolution.

## Data-Driven Commands

- Commands are defined in JSON and filtered at runtime (`app/commands/scene_commands.py`).
- The router (`app/commands/router.py`) executes stateful transitions and menu actions.
- Animation hints are stored in JSON and interpreted by the main loop.
