# Pyodide Web Demo Plan

## Phase 1 - Discovery and Minimal Adapter Design
- [x] Review current input/output flow to identify the smallest browser adapter surface
- [x] Inventory filesystem reads/writes for JSON assets and saves
- [x] Define browser input queue API to replace terminal getch
- [x] Decide output strategy (stdout intercept vs direct render hook)

## Phase 2 - Web Runtime Scaffold
- [x] Create `web/index.html` with container for xterm.js
- [x] Create `web/main.js` to load Pyodide and bootstrap the app
- [x] Create `web/style.css` for terminal sizing and layout
- [x] Add `web/README.md` with local run instructions

## Phase 3 - Virtual Filesystem Loading
- [x] Add JS file loader to mirror repo files into Pyodide FS (`/app`, `/data`, `/main.py`)
- [ ] Ensure JSON assets load correctly via Python `open()`
- [x] Add versioned asset manifest for efficient loading

## Phase 4 - Input/Output Bridge
- [x] Wire xterm.js key events into a Python input queue
- [x] Replace platform-specific input in `app/input.py` with browser mode
- [x] Route Python stdout/stderr to xterm.js output
- [ ] Validate ANSI color rendering and 100x30 layout

## Phase 5 - Save Data Persistence
- [x] Mount `/saves` to IDBFS on load
- [x] Sync IDBFS after `SaveData.save_player()`
- [ ] Confirm save/load works across page refresh

## Phase 6 - Local Browser Testing
- [x] Run `python3 -m http.server 8000` from repo root
- [x] Open `http://localhost:8000/web/` and confirm boot
- [x] Verify title screen, new game, and basic actions
- [x] Verify save file created and persists after refresh
- [x] Confirm no console errors

## Phase 7 - Static Hosting Readiness
- [x] Confirm all assets are relative-path safe for static hosting
- [x] Document GCS static hosting steps and CORS notes
- [ ] Optional: add a simple build step to copy `web/` + assets to `dist/`

## Footer - Paper Trail
2026-01-29
- Input review: `app/input.py` reads single-key input via `msvcrt` (Windows) or `termios/tty` (POSIX), including arrow keys and Enter mapping.
- Output review: `app/ui/rendering.py` writes ANSI frames directly to `sys.stdout`, clears screen with `\033[H\033[J`, and uses cursor hide/show codes.
- Runtime notes: `main.py` uses alternate screen buffer on POSIX and checks terminal size via `shutil.get_terminal_size`.
- Filesystem I/O: JSON loads via `open()` from `data/` and saves via `app/data_access/save_data.py` to `saves/slot1.json` (path from `app/config.py`).
- Input queue plan: replace `read_keypress`/`read_keypress_timeout` with a browser queue (push from JS key events; timeout polls queue).
- Output strategy: keep stdout-based rendering and intercept stdout in Pyodide to pipe to xterm.js.
2026-01-29
- Added `web/index.html` with Pyodide + xterm.js script tags and a terminal container.
- Added `web/main.js` bootstrap that initializes xterm and loads Pyodide.
- Added `web/style.css` to frame a 100x30 terminal-style viewport.
- Added `web/README.md` with local `python3 -m http.server` test steps.
2026-01-29
- Added `web/asset-manifest.json` to list Python and data assets for loading into Pyodide FS.
- Implemented asset loader + IDBFS mount + input bridge in `web/main.js`.
- Added browser input queue in `app/input.py` and gated terminal-only behavior in `main.py`.
- Added IDBFS sync hook after saves in `app/data_access/save_data.py`.
2026-01-29
- User reported local browser boot success after input path fix; game runs in Pyodide via `web/`.
- Added GCS static hosting notes to `web/README.md` for bucket hosting and CORS.
