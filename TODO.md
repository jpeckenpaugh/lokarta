# Main Loop Streamlining Plan

[x] Phase 1: Extract GameState
- Create a `GameState` dataclass to hold loop state (modes, message, opponents, loot).
- Replace local variables in `main()` with `GameState` fields.

[ ] Phase 2: Frame + Input Pipeline
- Extract `render_frame(state, ctx)` and `read_input(state, ctx)` helpers.
- Encapsulate boost prompt countdown as its own state handler.

[ ] Phase 3: Command Resolution
- Add `resolve_command(state, ctx, key)` to map inputs to command ids.
- Centralize router dispatch and state sync into a single function.

[ ] Phase 4: Combat Turn Handler
- Move battle/offense animations and opponent turns into `run_combat_round(state, ctx)`.
- Make combat flow callable from `main()` with minimal branching.

[ ] Phase 5: Cleanup + Tests
- Remove dead branches and unused imports from `main.py`.
- Add or update tests covering state transitions and command routing.

Notes:
- Preserve current behavior and timings.
- Keep JSON-driven command flow intact.
- Phase 1 introduced `GameState` and replaced loop locals with state fields.
