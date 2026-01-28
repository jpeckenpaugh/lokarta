import json
import os
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

def display_color_map():
    """Reads colors.json and displays a visual map of the colors."""
    file_path = os.path.join(os.path.dirname(__file__), 'data', 'colors.json')
    
    try:
        with open(file_path, 'r') as f:
            colors = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find colors.json at {file_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not parse colors.json. Please check for syntax errors.")
        return

    # ANSI reset code
    reset = "\033[0m"

    print("\nLokarta Color Map Reference")
    print("===========================\n")
    
    # Sort keys alphabetically, ignoring case, lowercase first
    sorted_keys = sorted(colors.keys(), key=lambda k: (k.lower(), k.islower()))
    
    # Process lowercase letters first to establish pairs
    lower_keys = [k for k in sorted_keys if 'a' <= k <= 'z']
    
    # Group into columns for display
    num_columns = 3
    col_width = 32
    
    row_chunks = [lower_keys[i:i + num_columns] for i in range(0, len(lower_keys), num_columns)]

    for row in row_chunks:
        line_parts = []
        for key in row:
            upper_key = key.upper()
            
            soft_data = colors.get(key)
            intense_data = colors.get(upper_key)
            
            if not soft_data or not intense_data:
                continue

            soft_rgb = hex_to_rgb(soft_data['hex'])
            intense_rgb = hex_to_rgb(intense_data['hex'])

            soft_color_code = truecolor_fg(*soft_rgb)
            intense_color_code = truecolor_fg(*intense_rgb)
            
            # Format: [ swatch ] key: name (hex)
            soft_swatch = f"{soft_color_code}██{reset}"
            intense_swatch = f"{intense_color_code}██{reset}"
            
            part = (
                f" {soft_swatch} {key}: {soft_data['name']} ({soft_data['hex']})\n"
                f" {intense_swatch} {upper_key}: {intense_data['name']} ({intense_data['hex']})"
            )
            line_parts.append(part)
        
        # Print parts side-by-side
        if line_parts:
            # Split the parts into lines and pad them
            split_parts = [part.split('\n') for part in line_parts]
            
            # Assuming each part has 2 lines
            for i in range(2):
                line_to_print = ""
                for j, part_lines in enumerate(split_parts):
                    if i < len(part_lines):
                        # Strip ansi for length calculation to pad correctly
                        visible_line = re.sub(r'\x1b\[[0-9;]*m', '', part_lines[i])
                        padding = ' ' * (col_width - len(visible_line))
                        line_to_print += part_lines[i] + padding
                print(line_to_print)
            print() # Add a blank line between full rows of colors

if __name__ == "__main__":
    display_color_map()
