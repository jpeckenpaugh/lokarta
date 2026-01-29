import json
import os
import sys

def truecolor_fg(r, g, b):
    """Generates a 24-bit foreground ANSI escape code."""
    return f"\033[38;2;{r};{g};{b}m"

def hex_to_rgb(hex_code):
    """Converts a hex color string to an (r, g, b) tuple."""
    hex_code = hex_code.lstrip('#')
    if len(hex_code) != 6:
        return 0, 0, 0
    try:
        r = int(hex_code[0:2], 16)
        g = int(hex_code[2:4], 16)
        b = int(hex_code[4:6], 16)
        return r, g, b
    except ValueError:
        return 0, 0, 0

def load_json(path: str):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError as e:
        print(f"Error: Could not find a required data file: {e.filename}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse a JSON file. Please check syntax. ({e})")
        return None


def build_color_lookup(colors: dict) -> dict:
    color_by_key = {}
    for key, color_data in colors.items():
        if key == "random" or key.isdigit():
            continue
        rgb = hex_to_rgb(color_data['hex'])
        color_by_key[key] = truecolor_fg(*rgb)
    return color_by_key


def render_art(art_lines, color_mask_lines, color_by_key):
    reset_code = "\033[0m"
    for i, art_line in enumerate(art_lines):
        if i >= len(color_mask_lines):
            print(art_line)
            continue
        mask_line = color_mask_lines[i].ljust(len(art_line))
        output_line = ""
        for j, char in enumerate(art_line):
            mask_char = mask_line[j]
            if mask_char in color_by_key:
                output_line += f"{color_by_key[mask_char]}{char}"
            else:
                output_line += f"{reset_code}{char}"
        print(output_line + reset_code)


def render_object(object_name):
    """Renders a single object from objects.json with its colors."""
    base = os.path.dirname(__file__)
    objects = load_json(os.path.join(base, 'data', 'objects.json'))
    colors = load_json(os.path.join(base, 'data', 'colors.json'))
    if objects is None or colors is None:
        return
    if object_name == "all":
        for key in objects.keys():
            art_object = objects.get(key, {})
            art_lines = art_object.get("art", [])
            color_mask_lines = art_object.get("color_mask", [])
            print(f"\nRendering object '{key}':\n")
            render_art(art_lines, color_mask_lines, build_color_lookup(colors))
            print()
        return
    art_object = objects.get(object_name)
    if not art_object:
        print(f"Error: Object '{object_name}' not found in objects.json")
        print("\nAvailable objects:")
        for key in objects.keys():
            print(f"- {key}")
        return
    art_lines = art_object.get("art", [])
    color_mask_lines = art_object.get("color_mask", [])
    print(f"\nRendering object '{object_name}':\n")
    render_art(art_lines, color_mask_lines, build_color_lookup(colors))
    print()


def render_npc(npc_name):
    base = os.path.dirname(__file__)
    npcs = load_json(os.path.join(base, 'data', 'npcs.json'))
    colors = load_json(os.path.join(base, 'data', 'colors.json'))
    if npcs is None or colors is None:
        return
    if npc_name == "all":
        for key in npcs.keys():
            npc = npcs.get(key, {})
            print(f"\nRendering npc '{key}':\n")
            render_art(npc.get("art", []), npc.get("color_map", []), build_color_lookup(colors))
            print()
        return
    npc = npcs.get(npc_name)
    if not npc:
        print(f"Error: NPC '{npc_name}' not found in npcs.json")
        print("\nAvailable npcs:")
        for key in npcs.keys():
            print(f"- {key}")
        return
    print(f"\nRendering npc '{npc_name}':\n")
    render_art(npc.get("art", []), npc.get("color_map", []), build_color_lookup(colors))
    print()


def render_opponent(opponent_name):
    base = os.path.dirname(__file__)
    opponents = load_json(os.path.join(base, 'data', 'opponents.json'))
    colors = load_json(os.path.join(base, 'data', 'colors.json'))
    if opponents is None or colors is None:
        return
    if opponent_name == "all":
        for key in opponents.keys():
            opponent = opponents.get(key, {})
            print(f"\nRendering opponent '{key}':\n")
            render_art(opponent.get("art", []), opponent.get("color_map", []), build_color_lookup(colors))
            print()
        return
    opponent = opponents.get(opponent_name)
    if not opponent:
        print(f"Error: Opponent '{opponent_name}' not found in opponents.json")
        print("\nAvailable opponents:")
        for key in opponents.keys():
            print(f"- {key}")
        return
    print(f"\nRendering opponent '{opponent_name}':\n")
    render_art(opponent.get("art", []), opponent.get("color_map", []), build_color_lookup(colors))
    print()


def render_venue(venue_name):
    base = os.path.dirname(__file__)
    venues = load_json(os.path.join(base, 'data', 'venues.json'))
    colors = load_json(os.path.join(base, 'data', 'colors.json'))
    npcs = load_json(os.path.join(base, 'data', 'npcs.json'))
    if venues is None or colors is None or npcs is None:
        return
    try:
        sys.path.insert(0, base)
        from app.data_access.objects_data import ObjectsData
        from app.ui.rendering import render_venue_objects, render_venue_art
        objects = ObjectsData(os.path.join(base, 'data', 'objects.json'))
        color_map = colors
        if venue_name == "all":
            for key in venues.keys():
                venue = venues.get(key, {})
                npc = {}
                npc_ids = venue.get("npc_ids", [])
                if npc_ids:
                    npc = npcs.get(npc_ids[0], {})
                if venue.get("objects"):
                    art_lines, art_color, _ = render_venue_objects(venue, npc, objects, color_map)
                else:
                    art_lines, art_color = render_venue_art(venue, npc, color_map)
                print(f"\nRendering venue '{key}':\n")
                for line in art_lines:
                    print(f"{art_color}{line}\033[0m")
                print()
            return
        venue = venues.get(venue_name)
        if not venue:
            print(f"Error: Venue '{venue_name}' not found in venues.json")
            print("\nAvailable venues:")
            for key in venues.keys():
                print(f"- {key}")
            return
        npc = {}
        npc_ids = venue.get("npc_ids", [])
        if npc_ids:
            npc = npcs.get(npc_ids[0], {})
        if venue.get("objects"):
            art_lines, art_color, _ = render_venue_objects(venue, npc, objects, color_map)
        else:
            art_lines, art_color = render_venue_art(venue, npc, color_map)
        print(f"\nRendering venue '{venue_name}':\n")
        for line in art_lines:
            print(f"{art_color}{line}\033[0m")
        print()
    except Exception as exc:
        print(f"Error rendering venue: {exc}")


def render_scene(scene_name):
    base = os.path.dirname(__file__)
    scenes = load_json(os.path.join(base, 'data', 'scenes.json'))
    colors = load_json(os.path.join(base, 'data', 'colors.json'))
    if scenes is None or colors is None:
        return
    try:
        sys.path.insert(0, base)
        from app.data_access.objects_data import ObjectsData
        from app.ui.rendering import render_scene_art
        objects = ObjectsData(os.path.join(base, 'data', 'objects.json'))
        if scene_name == "all":
            for key in scenes.keys():
                scene = scenes.get(key, {})
                art_lines, art_color = render_scene_art(
                    scene,
                    opponents=[],
                    objects_data=objects,
                    color_map_override=colors
                )
                print(f"\nRendering scene '{key}':\n")
                for line in art_lines:
                    print(f"{art_color}{line}\033[0m")
                print()
            return
        scene = scenes.get(scene_name)
        if not scene:
            print(f"Error: Scene '{scene_name}' not found in scenes.json")
            print("\nAvailable scenes:")
            for key in scenes.keys():
                print(f"- {key}")
            return
        art_lines, art_color = render_scene_art(
            scene,
            opponents=[],
            objects_data=objects,
            color_map_override=colors
        )
        print(f"\nRendering scene '{scene_name}':\n")
        for line in art_lines:
            print(f"{art_color}{line}\033[0m")
        print()
    except Exception as exc:
        print(f"Error rendering scene: {exc}")

def main():
    """Main function to handle command-line arguments."""
    if len(sys.argv) not in (2, 3):
        print("Usage: python3 render.py <type> [name]")
        print("\nExample:")
        print("  python3 render.py object flower_box")
        print("  python3 render.py npc mayor_1")
        print("  python3 render.py opponent slime")
        print("  python3 render.py venue town_hall")
        print("  python3 render.py scene forest")
        return
        
    render_type = sys.argv[1].lower()
    name = sys.argv[2] if len(sys.argv) == 3 else None
    if name is None:
        base = os.path.dirname(__file__)
        file_map = {
            "object": "objects.json",
            "npc": "npcs.json",
            "opponent": "opponents.json",
            "venue": "venues.json",
            "scene": "scenes.json",
        }
        filename = file_map.get(render_type)
        if not filename:
            print(f"Unknown type '{render_type}'. Expected object|npc|opponent|venue|scene.")
            return
        data = load_json(os.path.join(base, 'data', filename))
        if data is None:
            return
        print(f"Available {render_type}s:")
        for key in data.keys():
            print(f"- {key}")
        return
    if render_type == "object":
        render_object(name)
    elif render_type == "npc":
        render_npc(name)
    elif render_type == "opponent":
        render_opponent(name)
    elif render_type == "venue":
        render_venue(name)
    elif render_type == "scene":
        render_scene(name)
    else:
        print(f"Unknown type '{render_type}'. Expected object|npc|opponent|venue|scene.")

if __name__ == "__main__":
    main()
