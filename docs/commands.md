# Command Schema

Commands are defined in JSON (global, scenes, venues, menus) and merged at runtime.

## Base Fields

- `key`: string displayed in the Actions panel (e.g., `"F"`, `"1"`)
- `label`: string shown next to the key (e.g., `"Shop"`)
- `command`: string command id dispatched by the router (the action to run)

## Optional Fields

- `target`: string target used by the command (e.g., `"forest"`, `"town_shop"`)
- `service_id`: string service id used by venue services (e.g., `"rest"`, `"meal"`)
- `when`: string condition for filtering (e.g., `"has_opponents"`, `"no_opponents"`, `"needs_rest"`, `"has_save"`)
- `type`: string categorizing the command (e.g., `"menu_open"`, `"combat"`, `"system"`)
- `anim`: string animation hint (e.g., `"flash"`, `"melt"`, `"battle_start"`, `"battle_end"`)
- `requires_target`: boolean to indicate a target is required
- `suppress_actions`: boolean to hide the action panel during a command

## Scene Object Entries (scenes.json)

When scenes use object composition (`objects`, `objects_left`, `objects_right`, `objects_bottom`), entries can be:

```json
{ "id": "house", "label": "Shop", "label_row": 2, "label_key": "o" }
```

Optional fields:
- `label`: text injected into the object art (centered within the row content).
- `label_row`: 0-based row index in the object art to place the label.
- `label_key`: color key used for the label mask.
- `label_variation`: jitter amount for label color.
- `label_jitter_stability`: whether label jitter is stable per tick.
- `scatter`: id of a dynamic object to scatter across a repeated base line (forest bottom).

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
