# TODO: Data-Driven Command Overhaul

[x] Phase 1: Command Schema
- [x] Define a shared command schema with `command`, `target`, and `when` fields in JSON.
- [x] Document the schema in `README.md` or a small `docs/commands.md`.

[x] Phase 2: Global Command Routing
- [x] Introduce a `CommandRouter` that dispatches JSON actions to handlers.
- [x] Replace remaining hard-coded `main()` command branches with router calls.

[x] Phase 3: Scene Transitions
- [x] Move `Town/Forest` transitions into `data/scenes.json` using `ENTER_SCENE`.
- [x] Add `scene_id`-driven actions for scene changes, including default messages.

[x] Phase 4: Venue Interactions
- [x] Move shop/hall open/close actions into `data/venues.json` via `ENTER_VENUE` and `EXIT_VENUE`.
- [x] Express hall views as venue sub-views with commands and dynamic sources.

[x] Phase 5: Menu Actions
- [x] Add `open_message` and `close_message` to `data/menus.json`.
- [x] Route menu open/close actions through JSON commands.

[x] Phase 6: Spell Boost Flow
- [x] Add boost prompt metadata to `data/spells.json` (timeout, default, prompt text).
- [x] Route boost confirmation through the command router.

[ ] Phase 7: Battle Text + Events
- [ ] Move battle message templates into a `data/text.json`.
- [ ] Add a small formatter to render messages from templates.

[ ] Phase 8: Title Screen as Data
- [ ] Move title screen copy and actions into `data/scenes.json` or `data/menus.json`.
- [ ] Handle overwrite confirmation as a data-driven subview.

[ ] Phase 9: Inn/Rest Service
- [ ] Add a service definition (cost, effects, text) in JSON.
- [ ] Replace hard-coded rest logic with service actions.

[ ] Phase 10: Cleanup + Tests
- [ ] Remove unused branches in `main()` after router is complete.
- [ ] Add unit tests for the command router and schema validation.

---

Notes:
- Phase 1 docs captured in `docs/commands.md` with base fields and examples.
- README now points to the command schema notes.
- Phase 2 routing added in `commands/router.py` and wired in `main.py`.
- Menu-specific handlers (shop/hall/inventory/spellbook) now live in `commands/router.py`.
- Phase 3 ENTER_SCENE/ENTER_VENUE commands added to scene JSON and handled in router.
- Phase 4 venue open/close now driven by `venues.json` with `welcome_message`/`leave_message`.
- Hall info panels now use `info_sections` in `venues.json`.
- Phase 5 menu open/close messages now loaded from `menus.json`.
- Phase 6 boost prompt settings and confirmation now routed via `commands/router.py`.
