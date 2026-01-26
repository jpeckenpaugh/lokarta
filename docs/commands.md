# Command Schema

Commands are defined in JSON (global, scenes, venues, menus) and merged at runtime.

## Base Fields

- `key`: string displayed in the Actions panel (e.g., `"F"`, `"1"`)
- `label`: string shown next to the key (e.g., `"Shop"`)
- `command`: string command id dispatched by the router (the action to run)

## Optional Fields

- `target`: string target used by the command (e.g., `"forest"`, `"town_shop"`)
- `when`: string condition for filtering (e.g., `"has_opponents"`, `"no_opponents"`, `"needs_rest"`, `"has_save"`)
- `type`: string categorizing the command (e.g., `"menu_open"`, `"combat"`, `"system"`)
- `anim`: string animation hint (e.g., `"flash"`, `"melt"`, `"battle_start"`, `"battle_end"`)
- `requires_target`: boolean to indicate a target is required
- `suppress_actions`: boolean to hide the action panel during a command

## Examples

```json
{
  "key": "F",
  "label": "Set out for the Forest",
  "command": "ENTER_SCENE",
  "target": "forest"
}
```

```json
{
  "key": "1",
  "label": "Buy Rations",
  "command": "NUM1"
}
```

```json
{
  "key": "S",
  "label": "Shop",
  "command": "ENTER_VENUE",
  "target": "town_shop"
}
```
