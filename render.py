import json
import os
import sys
import re

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

def render_object(object_name):
    """Renders a single object from objects.json with its colors."""
    objects_path = os.path.join(os.path.dirname(__file__), 'data', 'objects.json')
    colors_path = os.path.join(os.path.dirname(__file__), 'data', 'colors.json')

    try:
        with open(objects_path, 'r') as f:
            objects = json.load(f)
        with open(colors_path, 'r') as f:
            colors = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: Could not find a required data file: {e.filename}")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse a JSON file. Please check syntax. ({e})")
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
    reset_code = "\033[0m"

    # Build a color lookup from the main colors file
    color_by_key = {}
    for key, color_data in colors.items():
        rgb = hex_to_rgb(color_data['hex'])
        color_by_key[key] = truecolor_fg(*rgb)

    print(f"\nRendering '{object_name}':\n")

    for i, art_line in enumerate(art_lines):
        if i >= len(color_mask_lines):
            print(art_line)
            continue

        mask_line = color_mask_lines[i]
        output_line = ""
        # Pad mask_line to match art_line length in case it's shorter
        mask_line = mask_line.ljust(len(art_line))

        for j, char in enumerate(art_line):
            mask_char = mask_line[j]
            if mask_char in color_by_key:
                color_code = color_by_key[mask_char]
                output_line += f"{color_code}{char}"
            else:
                # Use reset if character in mask is not a valid color key, or just the character
                output_line += f"{reset_code}{char}"
        
        print(output_line + reset_code)
    print()

def main():
    """Main function to handle command-line arguments."""
    if len(sys.argv) != 2:
        print("Usage: python3 render.py <object_name>")
        print("\nExample:")
        print("  python3 render.py flower_box")

        # Also list available objects if no argument is given
        objects_path = os.path.join(os.path.dirname(__file__), 'data', 'objects.json')
        try:
            with open(objects_path, 'r') as f:
                objects = json.load(f)
            print("\nAvailable objects:")
            for key in objects.keys():
                print(f"- {key}")
        except (FileNotFoundError, json.JSONDecodeError):
            # Fail silently if we can't list objects, the main error is usage.
            pass
        return
        
    object_name = sys.argv[1]
    render_object(object_name)

if __name__ == "__main__":
    main()
