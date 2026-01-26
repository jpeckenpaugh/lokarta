# ASCII Quest — Local Terminal POC

## Overview

This project is a **local-first proof of concept** for a retro, BBS-style ASCII RPG inspired by classic NES-era games (e.g., Final Fantasy I).

The initial goal is **not** to build a full game, but to validate:
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

## Current Features (POC)

- Local terminal rendering using ANSI escape codes
- Colorized UI (borders, title, stats)
- Player stats anchored to the bottom of the screen
- Single-key controls:
  - `A` — Attack
  - `I` — Inventory
  - `R` — Run
  - `Q` — Quit
- Stateless frame rendering
- Minimal placeholder game logic

---

## Screen Layout Contract

The terminal UI adheres to a strict **100×30** layout:

```

+--------------------------------------------------+
|------------------ GAME TITLE --------------------|
|                                                  |
|                MAIN BODY TEXT                    |
|                                                  |
|                                                  |
+--------------------------------------------------+
| HP / MP                                          |
| Level / Gold                                     |
| Name                                             |
| Location                                         |
+--------------------------------------------------+

````

- Top: border + title
- Middle: main narrative / menu area
- Bottom: fixed stats panel (4 lines) + border
- Input hints may render *below* the frame and do not count toward the 100×30 contract

This contract is intentionally stable to support future web and SSH renderers.

---

## Architecture

The codebase follows a **three-layer structure**:

### 1. Engine (Pure Logic)
- No printing
- No terminal calls
- No direct input handling
- Produces a `Frame` object representing the current screen

### 2. UI / Renderer
- Responsible for:
  - ANSI coloring
  - screen clearing
  - fixed-width rendering
  - single-key input handling
- Translates key presses into engine commands

### 3. Assets (Future)
- Enemies, items, maps, text, etc.
- Intended to live in external data files (YAML/JSON)

This separation is deliberate to ensure:
- easy testing
- easy migration to web or SSH
- no logic duplication

---

## Input Model

- Input is handled as **single key presses** (no Enter)
- Keys are mapped in the UI layer to semantic commands:
  - `"A"` → `ATTACK`
  - `"I"` → `INVENTORY`
  - `"R"` → `RUN`
- The engine never sees raw key presses

This mirrors classic BBS and NES menu interaction patterns.

---

## Platform Support

### Currently Supported
- macOS terminal
- Linux terminal

(Single-key input uses POSIX `termios` / `tty`.)

### Not Yet Supported
- Windows native terminal (would require `msvcrt.getch()` adapter)
- Web UI
- SSH/BBS frontend

These are intentional future steps.

---

## Running the POC

1. Resize your terminal to **at least 100 columns × 30 rows**
2. Run:

```bash
python3 main.py
````

3. Use single keys (`A`, `I`, `R`, `Q`) to interact

---

## Future Directions (Out of Scope for POC)

* Persistent save files
* Real combat mechanics
* Enemy AI
* Inventory systems
* Multiplayer or shared world state
* Authentication

These will only be considered once the core interaction model is validated.

---

## Philosophy

This project prioritizes:

* **consistency over complexity**
* **nostalgia through constraints**
* **clean separation over clever hacks**

If it can be rendered with `print()`, it belongs in the renderer.
If it affects game rules, it belongs in the engine.

---

## Status

This repository represents an **exploratory prototype**.
Expect rapid iteration, breaking changes, and intentional simplicity.
