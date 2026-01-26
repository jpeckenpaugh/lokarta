# Overhaul Roadmap

[x] Phase 1: Command Metadata Schema
- Add action metadata to `data/commands.json` (type, target, anim, requires_target, suppress_actions).
- Document schema updates in `docs/commands.md`.

[x] Phase 2: Spell Command Unification
- Link spell commands to `data/spells.json` (command_id, mp_cost, boost settings).
- Route spell actions generically in command handling.

[ ] Phase 3: Combat Action Table
- Encode `ATTACK` as data-driven (type=combat, anim=flash/melt).
- Remove hard-coded action branches in `main.py` for attack flow where possible.

[ ] Phase 4: Menu/Scene Navigation Cleanup
- Encode menu navigation actions in JSON (open/close/inventory/spellbook).
- Reduce direct key branching in `main.py` for menu handling.

[ ] Phase 5: Animation + Timing Rules
- Move battle timing/animation triggers into command metadata.
- Centralize delays in a single action pipeline.

[ ] Phase 6: End-to-End Cleanup + Tests
- Remove dead branches in `main.py`.
- Add tests for command metadata and spell routing.

Notes:
- Keep JSON backward-compatible when possible.
- Preserve single-key input behavior and 100x30 layout constraints.
- Phase 1 added basic metadata fields to global commands and documented schema.
- Phase 2 linked spell commands and menu keys in `data/spells.json` and routed via `SpellsData`.
