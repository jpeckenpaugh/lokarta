import json
import math
import os
import colorsys

HUE_BINS = 12
MIN_SAT_FOR_HUE = 0.2
NEAR_DUPLICATE_DELTAE = 6.0
MAX_CLOSE_PAIRS = 12


def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip("#")
    if len(hex_code) != 6:
        return None
    try:
        r = int(hex_code[0:2], 16)
        g = int(hex_code[2:4], 16)
        b = int(hex_code[4:6], 16)
        return r, g, b
    except ValueError:
        return None


def srgb_to_linear(v):
    v = v / 255.0
    if v <= 0.04045:
        return v / 12.92
    return ((v + 0.055) / 1.055) ** 2.4


def rgb_to_xyz(r, g, b):
    r_lin = srgb_to_linear(r)
    g_lin = srgb_to_linear(g)
    b_lin = srgb_to_linear(b)
    x = r_lin * 0.4124 + g_lin * 0.3576 + b_lin * 0.1805
    y = r_lin * 0.2126 + g_lin * 0.7152 + b_lin * 0.0722
    z = r_lin * 0.0193 + g_lin * 0.1192 + b_lin * 0.9505
    return x, y, z


def xyz_to_lab(x, y, z):
    # D65 reference white
    ref_x, ref_y, ref_z = 0.95047, 1.00000, 1.08883
    x /= ref_x
    y /= ref_y
    z /= ref_z

    def f(t):
        if t > 0.008856:
            return t ** (1.0 / 3.0)
        return (7.787 * t) + (16.0 / 116.0)

    fx = f(x)
    fy = f(y)
    fz = f(z)
    l = (116.0 * fy) - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return l, a, b


def rgb_to_lab(r, g, b):
    x, y, z = rgb_to_xyz(r, g, b)
    return xyz_to_lab(x, y, z)


def delta_e(lab1, lab2):
    return math.sqrt(
        (lab1[0] - lab2[0]) ** 2
        + (lab1[1] - lab2[1]) ** 2
        + (lab1[2] - lab2[2]) ** 2
    )


def hue_bin_index(hue_deg):
    return int(hue_deg // (360 / HUE_BINS)) % HUE_BINS


def load_colors():
    base = os.path.dirname(__file__)
    path = os.path.join(base, "data", "colors.json")
    with open(path, "r") as f:
        return json.load(f)


def main():
    colors = load_colors()
    entries = []
    for key, value in colors.items():
        if key == "random" or key.isdigit():
            continue
        if not isinstance(value, dict):
            continue
        hex_code = value.get("hex", "")
        rgb = hex_to_rgb(hex_code)
        if not rgb:
            continue
        r, g, b = rgb
        h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        hsv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        lab = rgb_to_lab(r, g, b)
        entries.append(
            {
                "key": key,
                "name": value.get("name", ""),
                "hex": hex_code,
                "rgb": rgb,
                "h": h * 360.0,
                "l": l,
                "s": s,
                "hsv": hsv,
                "lab": lab,
            }
        )

    print("Palette Audit")
    print("=============")
    print(f"Entries: {len(entries)}")
    print()

    # Hue bins
    bins = [0 for _ in range(HUE_BINS)]
    bins_all = [0 for _ in range(HUE_BINS)]
    for e in entries:
        idx = hue_bin_index(e["h"])
        bins_all[idx] += 1
        if e["s"] >= MIN_SAT_FOR_HUE:
            bins[idx] += 1

    print("Hue Coverage (HSL hue bins)")
    for i in range(HUE_BINS):
        start = int(i * (360 / HUE_BINS))
        end = int((i + 1) * (360 / HUE_BINS))
        print(f" {start:3d}-{end:3d} deg: {bins[i]} (sat>={MIN_SAT_FOR_HUE}) / {bins_all[i]} total")
    print()

    # Near-duplicates
    pairs = []
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            d = delta_e(entries[i]["lab"], entries[j]["lab"])
            pairs.append((d, entries[i], entries[j]))
    pairs.sort(key=lambda x: x[0])

    print(f"Closest Pairs (DeltaE < {NEAR_DUPLICATE_DELTAE})")
    shown = 0
    for d, a, b in pairs:
        if d >= NEAR_DUPLICATE_DELTAE:
            break
        print(f" {a['key']} {a['name']} {a['hex']}  <->  {b['key']} {b['name']} {b['hex']}  (dE {d:.2f})")
        shown += 1
        if shown >= MAX_CLOSE_PAIRS:
            break
    if shown == 0:
        print(" none")
    print()

    # Brown-ish check (rough heuristic)
    brownish = []
    for e in entries:
        hue = e["h"]
        if 15 <= hue <= 45 and 0.18 <= e["l"] <= 0.55 and 0.25 <= e["s"] <= 0.7:
            brownish.append(e)
    print("Brown-ish Candidates")
    if brownish:
        for e in brownish:
            print(f" {e['key']} {e['name']} {e['hex']}  (h {e['h']:.0f}, l {e['l']:.2f}, s {e['s']:.2f})")
    else:
        print(" none")
    print()

    # Nearest to a target brown
    target_hex = "#8B5A2B"
    target_rgb = hex_to_rgb(target_hex)
    target_lab = rgb_to_lab(*target_rgb)
    nearest = sorted(
        [(delta_e(e["lab"], target_lab), e) for e in entries],
        key=lambda x: x[0],
    )[:5]
    print("Nearest to target brown (#8B5A2B)")
    for d, e in nearest:
        print(f" {e['key']} {e['name']} {e['hex']}  (dE {d:.2f})")
    print()


if __name__ == "__main__":
    main()
