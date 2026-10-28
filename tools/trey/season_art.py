#!/usr/bin/env python3
"""TREY: seasonal tileset palettes (TREY_PLAN.md 5.5, Phase 4 chunk 4b).

Run from the repo root:
    python3 tools/trey/season_art.py --preview DIR [Map1,Map2]  # render maps (any region) in all four seasons
    python3 tools/trey/season_art.py --list          # the tilesets that get seasons, with their palette folders
    python3 tools/trey/season_art.py --write         # write the seasonal palettes of every tileset in SEASONAL_TILESETS

6-S (D33): every region has seasons (Hoenn, Kanto/Sevii FRLG, Johto, Sinnoh); see HEADER_FILES and NO_SEASONS.

Seasons are palette recolours of the same tiles (David, 2026-10-14: "palettes + key tile swaps"). Summer is
the base art. Each other season is generated from the base palettes by colour rules (foliage, earth, water),
then written to <tileset>/seasons/<season>/NN.pal so they can be hand-tuned afterwards: the script never
overwrites a palette whose file starts with the line "HANDMADE". Tile swaps (snow-covered tiles, blossoms)
go in <tileset>/seasons/<season>/tiles.png when a tileset needs them; none exist yet.
"""
import colorsys
import os
import struct
import sys

from PIL import Image

SEASONS = ["spring", "summer", "autumn", "winter"]
OUTDOOR_MAP_TYPES = {"MAP_TYPE_TOWN", "MAP_TYPE_CITY", "MAP_TYPE_ROUTE", "MAP_TYPE_OCEAN_ROUTE"}


# TREY (6-S, D33): every region gets seasons. Tileset headers and graphics live in several files (Hoenn and FRLG
# in headers.h/graphics.h, Johto in trey_hns.h, Sinnoh in trey_sinnoh.h). Seasons recolour a tileset's PALETTE
# folder, so tilesets that share a palette array (Sinnoh's "meta" tilesets) share one seasonal table.
HEADER_FILES = ["src/data/tilesets/headers.h", "src/data/tilesets/trey_hns.h", "src/data/tilesets/trey_sinnoh.h",
                "src/data/tilesets/trey_orange.h", "src/data/tilesets/trey_kitakami.h"]   # TREY (6d-1): Kitakami
GRAPHICS_FILES = ["src/data/tilesets/graphics.h", "src/graphics.c", "src/data/tilesets/trey_hns.h", "src/data/tilesets/trey_sinnoh.h",
                  "src/data/tilesets/trey_orange.h", "src/data/tilesets/trey_kitakami.h"]
# Tilesets snowy all year (DPPt): no seasonal art. A map whose SECONDARY tileset has no seasonal art shows the base
# art for its primary too (src/trey_seasons.c), so Snowpoint keeps its summer = winter look.
NO_SEASONS = {"gTileset_SinnohSnowpoint", "gTileset_MtSilverSnow_Hns"}
# Sinnoh's outdoor tilesets, until its maps are in data/maps (6b-4); harmless afterwards.
EXTRA_OUTDOOR = {"gTileset_SinnohGeneral", "gTileset_SinnohTwinleaf", "gTileset_SinnohJubilife", "gTileset_SinnohOreburgh",
                 "gTileset_SinnohFloaroma", "gTileset_SinnohPastoria", "gTileset_SinnohLeague", "gTileset_SinnohStark",
                 "gTileset_SinnohCanalave", "gTileset_SinnohCelestic", "gTileset_SinnohHearthome",
                 "gTileset_SinnohSunyshore", "gTileset_SinnohValor", "gTileset_SinnohVeilstone"}


def _read(path):
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""


def tileset_headers():
    """tileset name -> (header file, palettes symbol)."""
    import re
    out = {}
    for hf in HEADER_FILES:
        for m in re.finditer(r"const struct Tileset (\w+)\s*=\s*\{(.*?)\};", _read(hf), re.S):
            p = re.search(r"\.palettes\s*=\s*(\w+)", m.group(2))
            if p:
                out.setdefault(m.group(1), (hf, p.group(1)))
    return out


def palette_dirs():
    """palettes symbol -> (folder, number of palettes)."""
    import re
    out = {}
    for gf in GRAPHICS_FILES:
        for m in re.finditer(r"(gTilesetPalettes_\w+)\[\]\[16\]\s*=\s*\{(.*?)\};", _read(gf), re.S):
            paths = re.findall(r'INC\w+\("([^"]+)/palettes/\d\d\.(?:pal|gbapal)"', m.group(2))
            if paths:
                out.setdefault(m.group(1), (paths[0], len(paths)))
    return out


def find_seasonal_tilesets():
    """Every tileset used by an outdoor map (town, city, route, ocean route), with its palette folder."""
    import json
    groups = json.load(open("data/maps/map_groups.json", encoding="utf-8"))
    layouts = {l["id"]: l for l in json.load(open("data/layouts/layouts.json", encoding="utf-8"))["layouts"] if "id" in l}
    names = set(EXTRA_OUTDOOR)
    for g in groups["group_order"]:
        for m in groups[g]:
            path = f"data/maps/{m}/map.json"
            if not os.path.exists(path):
                continue
            d = json.load(open(path, encoding="utf-8"))
            lay = layouts.get(d.get("layout"))
            if d.get("map_type") in OUTDOOR_MAP_TYPES and lay:
                names.add(lay["primary_tileset"])
                names.add(lay["secondary_tileset"])
    heads, pdirs = tileset_headers(), palette_dirs()
    out = {}
    for name in sorted(n for n in names - NO_SEASONS if not n.startswith("gTileset_Orange")):  # TREY (6c-4b, D42): Orange is always summer
        if name in heads and heads[name][1] in pdirs:
            folder, count = pdirs[heads[name][1]]
            if os.path.exists(f"{folder}/palettes/00.pal"):
                out[name] = folder
                PAL_COUNT[folder] = count
                HEADER_OF[name] = heads[name][0]
    return out


PAL_COUNT = {}   # palette folder -> number of palettes in its C array (13 or 16)
HEADER_OF = {}   # tileset -> the file that defines its struct Tileset
# Tilesets that get seasonal palettes: every tileset an outdoor map uses (the recolours apply wherever
# that tileset is drawn on an outdoor map; indoor and cave maps always show the base art).
SEASONAL_TILESETS = find_seasonal_tilesets()
PREVIEW_MAPS = ["Route101"]
NUM_PALS_IN_PRIMARY = 6
NUM_PALS_TOTAL = 13
NUM_PALS_IN_PRIMARY_FRLG = 7
NUM_TILES_IN_PRIMARY_FRLG = 640
NUM_METATILES_IN_PRIMARY_FRLG = 640


def read_pal(path):
    with open(path, encoding="utf-8") as f:
        lines = [l.strip() for l in f.read().splitlines() if l.strip()]
    start = 3 if lines[0] == "JASC-PAL" else 4
    return [tuple(int(v) for v in l.split()[:3]) for l in lines[start:start + 16]]


def write_pal(path, colors):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    colors = list(colors)[:16] + [(0, 0, 0)] * (16 - len(colors))  # 6-S: some Heart & Soul palettes list only 15 colours
    with open(path, "w", newline="\r\n") as f:
        f.write("JASC-PAL\n0100\n16\n")
        for r, g, b in colors:
            f.write(f"{r} {g} {b}\n")


def gba(c):
    """Round to the GBA's 5-bit colour steps, as the game will show it."""
    return tuple(min(255, (v >> 3) << 3) for v in c)


# ---------------------------------------------------------------------------
# Colour rules
# ---------------------------------------------------------------------------
def classify(rgb):
    r, g, b = [v / 255 for v in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    hd = h * 360
    if s < 0.12 or v < 0.12:
        return "neutral", hd, s, v
    if 65 <= hd <= 170:
        return "foliage", hd, s, v
    if 180 <= hd <= 250:
        return "water", hd, s, v
    if 15 <= hd < 65 and s < 0.75:
        return "earth", hd, s, v
    return "other", hd, s, v


def hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360, max(0, min(1, s)), max(0, min(1, v)))
    return (int(r * 255), int(g * 255), int(b * 255))


def season_color(rgb, season):
    kind, h, s, v = classify(rgb)
    if season == "summer":
        return rgb
    if season == "spring":
        if kind == "foliage":                       # fresh, slightly yellower and brighter greens
            return hsv(h - 8, min(1, s * 1.05), min(1, v * 1.06 + 0.02))
        if kind == "earth":
            return hsv(h, s, min(1, v * 1.03))
        return rgb
    # Emerald's ground grass is a minty, teal-ish green (hue above 140); tree leaves are yellower greens.
    ground = kind == "foliage" and h > 140 and s < 0.5
    tallgrass = kind == "foliage" and h > 140 and s >= 0.5
    if season == "autumn":
        if ground:                                  # dry, yellowed grass
            return hsv(64, s * 0.8, v * 0.97)
        if tallgrass:                               # olive, going brown
            return hsv(48, min(1, s * 0.9), v * 0.92)
        if kind == "foliage":                       # leaves: gold, orange, red-brown shade
            if v > 0.6:
                return hsv(42, min(1, s + 0.2), v * 0.97)
            if v > 0.42:
                return hsv(24, min(1, s + 0.25), v * 0.93)
            return hsv(6, min(1, s + 0.2), v * 0.85)
        if kind == "earth":
            return hsv(h - 4, min(1, s * 1.1), v * 0.93)
        if kind == "water":
            return hsv(h, s * 0.9, v * 0.95)
        return rgb
    if season == "winter":
        if ground and s < 0.3:                      # lighter grass patches and paths: trodden, blue-grey snow
            return hsv(214, 0.16, 0.84)
        if ground:                                  # open ground: fresh snow
            return hsv(220, 0.04, 0.97)
        if kind == "foliage":                       # snow on leaves and tall grass: white highlights, blue-grey shading
            if v > 0.65:
                return hsv(220, 0.05, 0.95)
            if v > 0.45:
                return hsv(220, 0.11, 0.84)
            if v > 0.3:
                return hsv(222, 0.17, 0.68)
            return hsv(225, 0.22, 0.50)
        if kind == "earth":                         # frozen paths stay visible: greyer and a little darker
            return hsv(h, s * 0.4, v * 0.82)
        if kind == "water":                         # cold, paler water
            return hsv(h + 6, s * 0.6, min(1, v * 1.06 + 0.05))
    return rgb


def season_palettes(base, season):
    return [[c if i == 0 else gba(season_color(c, season)) for i, c in enumerate(pal)] for pal in base]


# ---------------------------------------------------------------------------
# Tilesets
# ---------------------------------------------------------------------------
def load_tileset(path, secondary):
    tiles_img = Image.open(f"{path}/tiles.png")
    tiles = []
    w, h = tiles_img.size
    px = tiles_img.load()
    for ty in range(h // 8):
        for tx in range(w // 8):
            tiles.append([px[tx * 8 + x, ty * 8 + y] & 0xF for y in range(8) for x in range(8)])
    pals = [read_pal(f"{path}/palettes/{i:02d}.pal") if os.path.exists(f"{path}/palettes/{i:02d}.pal") else [(0, 0, 0)] * 16
            for i in range(16)]
    with open(f"{path}/metatiles.bin", "rb") as f:
        data = f.read()
    metatiles = [struct.unpack_from("<8H", data, i * 16) for i in range(len(data) // 16)]
    return {"tiles": tiles, "pals": pals, "metatiles": metatiles, "secondary": secondary}


def pal_count(path):
    return PAL_COUNT.get(path) or sum(1 for i in range(16) if os.path.exists(f"{path}/palettes/{i:02d}.pal"))


# Hoenn's seasonal palettes from 4b (approved 2026-10-14): never re-tuned by the 6-S rules below.
HOENN_4B = {"primary/general", "secondary/battle_frontier_outside_east", "secondary/battle_frontier_outside_west",
            "secondary/cave", "secondary/dewford", "secondary/ever_grande", "secondary/facility", "secondary/fallarbor",
            "secondary/fortree", "secondary/lavaridge", "secondary/lilycove", "secondary/mauville", "secondary/mossdeep",
            "secondary/pacifidlog", "secondary/petalburg", "secondary/rustboro", "secondary/slateport", "secondary/sootopolis"}
_BUILDING_PALS = {}
# Building palettes the door rule misses (doors without a door behaviour, walls in a palette of their own).
KEEP_PALETTES = {"secondary/sinnoh_hearthome": {8, 10, 11}, "secondary/celadon_city_frlg": {12}}


def building_palettes(path):
    """6-S: palettes of a SECONDARY tileset that its door metatiles use. Those hold the roofs and walls (green roofs
    would otherwise turn orange in autumn), so they keep their base colours in every season."""
    import re
    if path in _BUILDING_PALS:
        return _BUILDING_PALS[path]
    keep = set()
    if "/secondary/" in path and path.split("data/tilesets/", 1)[-1] not in HOENN_4B \
            and os.path.exists(f"{path}/metatiles.bin") and os.path.exists(f"{path}/metatile_attributes.bin"):
        text = open("include/constants/metatile_behaviors.h", encoding="utf-8").read()
        names = re.findall(r"^\s*(MB_\w+)", text[text.index("enum"):], re.M)
        mts = open(f"{path}/metatiles.bin", "rb").read()
        attrs = open(f"{path}/metatile_attributes.bin", "rb").read()
        count = len(mts) // 16
        wide = count and len(attrs) >= count * 4          # FRLG 32-bit attributes (Kanto, Johto)
        for i in range(count):
            a = struct.unpack_from("<I" if wide else "<H", attrs, i * (4 if wide else 2))[0] & (0x1FF if wide else 0xFF)
            if a < len(names) and "DOOR" in names[a]:
                first = NUM_PALS_IN_PRIMARY_FRLG if wide else NUM_PALS_IN_PRIMARY   # only the tileset's own palettes
                keep.update(e >> 12 for e in struct.unpack_from("<8H", mts, i * 16) if e >> 12 >= first)
    keep |= KEEP_PALETTES.get(path.split("data/tilesets/", 1)[-1], set())
    _BUILDING_PALS[path] = keep
    return keep


def season_pals_for(path, season):
    n = pal_count(path)
    base = [read_pal(f"{path}/palettes/{i:02d}.pal") for i in range(n)]
    out = season_palettes(base, season)
    for i in building_palettes(path):
        if i < n:
            out[i] = [gba(c) if k else c for k, c in enumerate(base[i])]
    for i in range(n):
        hand = f"{path}/seasons/{season}/{i:02d}.pal"
        if os.path.exists(hand) and open(hand).readline().startswith("HANDMADE"):
            out[i] = read_pal(hand)
    return out


def render_map(mapbin, w, h, prim, sec, season, frlg=False):
    with open(mapbin, "rb") as f:
        blocks = struct.unpack(f"<{w * h}H", f.read(w * h * 2))
    npp = NUM_PALS_IN_PRIMARY_FRLG if frlg else NUM_PALS_IN_PRIMARY
    ntp = NUM_TILES_IN_PRIMARY_FRLG if frlg else 512
    nmp = NUM_METATILES_IN_PRIMARY_FRLG if frlg else 512
    def pals_of(ts):
        if season == "summer" or ts[0] not in SEASONAL_TILESETS:
            return ts[1]["pals"]
        p = season_pals_for(SEASONAL_TILESETS[ts[0]], season)
        return p + ts[1]["pals"][len(p):]
    if sec[0] not in SEASONAL_TILESETS:   # same rule as src/trey_seasons.c: base art all over
        pals = prim[1]["pals"][:npp] + sec[1]["pals"][npp:NUM_PALS_TOTAL]
    else:
        pals = pals_of(prim)[:npp] + pals_of(sec)[npp:NUM_PALS_TOTAL]
    img = Image.new("RGB", (w * 16, h * 16))
    out = img.load()
    for i, block in enumerate(blocks):
        mid = block & 0x3FF
        mtl, j = (prim[1]["metatiles"], mid) if mid < nmp else (sec[1]["metatiles"], mid - nmp)
        if j >= len(mtl):
            continue
        mt = mtl[j]
        bx, by = (i % w) * 16, (i // w) * 16
        for layer in range(2):
            for k in range(4):
                e = mt[layer * 4 + k]
                t, hf, vf, p = e & 0x3FF, (e >> 10) & 1, (e >> 11) & 1, e >> 12
                tl, j = (prim[1]["tiles"], t) if t < ntp else (sec[1]["tiles"], t - ntp)
                tile = tl[j] if j < len(tl) else [0] * 64
                ox, oy = bx + (k % 2) * 8, by + (k // 2) * 8
                for y in range(8):
                    for x in range(8):
                        c = tile[(7 - y if vf else y) * 8 + (7 - x if hf else x)]
                        if c == 0 and layer == 1:
                            continue
                        if p < len(pals):
                            out[ox + x, oy + y] = pals[p][c] if c else pals[p][0] if layer == 0 and False else (pals[p][c] if c else (0, 0, 0))
    return img


def tileset_files(name):
    """(tiles folder, palette folder, metatiles folder) of any tileset, from the C files."""
    import re
    heads = tileset_headers()
    body = re.search(r"const struct Tileset " + name + r"\s*=\s*\{(.*?)\};", _read(heads[name][0]), re.S).group(1)
    field = lambda k: re.search(r"\." + k + r"\s*=\s*(\w+)", body).group(1)
    c = "".join(_read(f) for f in GRAPHICS_FILES + ["src/data/tilesets/metatiles.h"])
    find = lambda sym, what: re.search(re.escape(sym) + r"\[\](?:\[16\])?\s*=\s*\{?\s*INC\w+\(\"([^\"]+)/" + what, c).group(1)
    return find(field("tiles"), "tiles.png"), find(field("palettes"), "palettes/"), find(field("metatiles"), "metatiles.bin")


def load_any_tileset(name):
    tdir, pdir, mdir = tileset_files(name)
    ts = load_tileset(tdir, False) if tdir == mdir else None
    if ts is None:   # Sinnoh "meta"/"pal" tilesets: tiles, palettes and metatiles in different folders
        img = Image.open(f"{tdir}/tiles.png")
        px, (w, h) = img.load(), img.size
        data = open(f"{mdir}/metatiles.bin", "rb").read()
        ts = {"tiles": [[px[tx * 8 + x, ty * 8 + y] & 0xF for y in range(8) for x in range(8)]
                        for ty in range(h // 8) for tx in range(w // 8)],
              "metatiles": [struct.unpack_from("<8H", data, i * 16) for i in range(len(data) // 16)]}
    ts["pals"] = [read_pal(f"{pdir}/palettes/{i:02d}.pal") if os.path.exists(f"{pdir}/palettes/{i:02d}.pal") else [(0, 0, 0)] * 16
                  for i in range(16)]
    return ts


def preview(outdir, maps=None):
    """Four-season sheets of maps (any region; FRLG-format layouts are read as such)."""
    import json
    os.makedirs(outdir, exist_ok=True)
    layouts = {l["id"]: l for l in json.load(open("data/layouts/layouts.json", encoding="utf-8"))["layouts"] if "id" in l}
    for name in maps or PREVIEW_MAPS:
        lay = layouts[json.load(open(f"data/maps/{name}/map.json", encoding="utf-8"))["layout"]]
        mapbin, w, h = lay["blockdata_filepath"], lay["width"], lay["height"]
        pn, sn = lay["primary_tileset"], lay["secondary_tileset"]
        prim = (pn, load_any_tileset(pn))
        sec = (sn, load_any_tileset(sn))
        frlg = lay.get("layout_version") == "frlg"
        frames = [render_map(mapbin, w, h, prim, sec, s, frlg) for s in SEASONS]
        sheet = Image.new("RGB", (w * 16 * 2 + 12, h * 16 * 2 + 12), (40, 44, 60))
        for k, fr in enumerate(frames):
            sheet.paste(fr, ((k % 2) * (w * 16 + 12), (k // 2) * (h * 16 + 12)))
            fr.save(f"{outdir}/{name}_{SEASONS[k]}.png")
        sheet.save(f"{outdir}/{name}_seasons.png")
        print("preview:", f"{outdir}/{name}_seasons.png")


def write_all():
    for name, path in SEASONAL_TILESETS.items():
        for season in SEASONS:
            if season == "summer":
                continue
            pals = season_pals_for(path, season)
            for i, pal in enumerate(pals):
                dst = f"{path}/seasons/{season}/{i:02d}.pal"
                if os.path.exists(dst) and open(dst).readline().startswith("HANDMADE"):
                    continue
                write_pal(dst, pal)
        print("season_art.py: wrote", path)


# ---------------------------------------------------------------------------
# Key tile swaps: winter snow drifts (Route 101 proof). A drift is a new metatile in the Petalburg tileset,
# drawn with General palette 2's grass colours, which the winter palettes turn into snow. It is only
# placed in winter layouts, so in other seasons it never shows.
#   index 13 ground  -> fresh snow    12 light patch -> blue-grey snow
#   index 15 dark    -> grey shade    4 darkest      -> deep shadow / outline
# ---------------------------------------------------------------------------
import json
import math

DRIFT_PAL = 2
SIDECAR = "data/tilesets/secondary/petalburg/trey_season_tiles.json"
WINTER_LAYOUT = ("LAYOUT_ROUTE101_WINTER", "Route101_Winter_Layout", "data/layouts/Route101_Winter")
DRIFTS = [(7, 7), (8, 7), (13, 9), (14, 9), (13, 10)]     # snow drifts (impassable)
OPENINGS = [(3, 7)]                                        # a ledge buried in snow: walkable both ways
GROUND_METATILE = 0x001


def drift_image():
    img = [[13] * 16 for _ in range(16)]                   # snowy ground around the mound
    for y in range(16):
        for x in range(16):
            # a big rounded mound filling most of the tile, lit from the top left
            dx, dy = (x + 0.5 - 8) / 7.8, (y + 0.5 - 8.8) / 7.0
            d = dx * dx + dy * dy
            if d <= 1.0:
                shade = -dx * 0.55 - dy * 0.85 + (1 - d) * 0.35
                c = 13 if shade > 0.15 else (12 if shade > -0.35 else 4)
                if d > 0.8 and (dy > -0.2 or dx > 0.3):
                    c = 4                                  # outline on the shaded side
                img[y][x] = c
            elif d <= 1.3 and dy > 0.3:
                img[y][x] = 12                             # shadow cast on the ground
    return img


def split4(img):
    return [tuple(img[ty + y][tx + x] for y in range(8) for x in range(8)) for ty in (0, 8) for tx in (0, 8)]


def redraw_drift_tiles(first):
    base = "data/tilesets/secondary/petalburg"
    im = Image.open(f"{base}/tiles.png")
    px = im.load()
    for k, t in enumerate(split4(drift_image())):
        n = first + k
        ox, oy = (n % 16) * 8, (n // 16) * 8
        for i, v in enumerate(t):
            px[ox + i % 8, oy + i // 8] = v
    im.save(f"{base}/tiles.png")


def ensure_drift_metatile():
    """Appends the drift tiles and metatile to Petalburg (once). Returns the metatile ID."""
    if os.path.exists(SIDECAR):
        info = json.load(open(SIDECAR))
        redraw_drift_tiles(info["drift_tile"])            # keep the art in step with drift_image()
        return info["drift_metatile"]
    base = "data/tilesets/secondary/petalburg"
    im = Image.open(f"{base}/tiles.png")
    w, h = im.size
    ntiles = (w // 8) * (h // 8)
    tiles = split4(drift_image())
    new = Image.new("P", (w, h + 8))
    new.putpalette(im.getpalette())
    new.paste(im, (0, 0))
    px = new.load()
    for k, t in enumerate(tiles):
        ox, oy = (k % 16) * 8, h + (k // 16) * 8
        for i, v in enumerate(t):
            px[ox + i % 8, oy + i // 8] = v
    new.save(f"{base}/tiles.png")
    with open(f"{base}/metatiles.bin", "rb") as f:
        mts = f.read()
    mid = 512 + len(mts) // 16
    entries = [(512 + ntiles + k) | (DRIFT_PAL << 12) for k in range(4)] + [0, 0, 0, 0]
    with open(f"{base}/metatiles.bin", "ab") as f:
        f.write(struct.pack("<8H", *entries))
    with open(f"{base}/metatile_attributes.bin", "ab") as f:
        f.write(struct.pack("<H", 0x0000))                 # MB_NORMAL, normal layer
    json.dump({"drift_metatile": mid, "drift_tile": ntiles, "note": "TREY 4b: winter snow drift, added by tools/trey/season_art.py"},
              open(SIDECAR, "w"), indent=2)
    print(f"season_art.py: drift metatile 0x{mid:03X} added to Petalburg (tiles {ntiles}-{ntiles + 3})")
    return mid


def write_winter_layout():
    mid = ensure_drift_metatile()
    lid, lname, ldir = WINTER_LAYOUT
    os.makedirs(ldir, exist_ok=True)
    with open("data/layouts/Route101/map.bin", "rb") as f:
        blocks = list(struct.unpack("<400H", f.read()))
    for (x, y) in DRIFTS:
        blocks[y * 20 + x] = mid | (1 << 10) | (blocks[y * 20 + x] & 0xF000)
    for (x, y) in OPENINGS:
        blocks[y * 20 + x] = GROUND_METATILE | (blocks[y * 20 + x] & 0xF000)
    with open(f"{ldir}/map.bin", "wb") as f:
        f.write(struct.pack("<400H", *blocks))
    with open("data/layouts/Route101/border.bin", "rb") as f, open(f"{ldir}/border.bin", "wb") as g:
        g.write(f.read())
    lj = json.load(open("data/layouts/layouts.json", encoding="utf-8"))
    if not any(l.get("id") == lid for l in lj["layouts"]):
        lj["layouts"].append({"id": lid, "name": lname, "width": 20, "height": 20,
                              "primary_tileset": "gTileset_General", "secondary_tileset": "gTileset_Petalburg",
                              "border_filepath": f"{ldir}/border.bin", "blockdata_filepath": f"{ldir}/map.bin"})
        with open("data/layouts/layouts.json", "w", encoding="utf-8", newline="\n") as f:
            json.dump(lj, f, indent=2, ensure_ascii=False)
            f.write("\n")
    mp = "data/maps/Route101/map.json"
    mj = json.load(open(mp, encoding="utf-8"))
    mj["trey_season_layouts"] = {"winter": lid}
    mj["trey_season_weather"] = {"winter": "WEATHER_SNOW"}
    with open(mp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(mj, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("season_art.py: Route 101 winter layout written")


SEASONAL_H = "src/data/tilesets/trey_seasonal.h"
HEADERS_H = "src/data/tilesets/headers.h"


def write_c_tables():
    """Palette arrays and TilesetSeasonGfx tables for every seasonal tileset, and the .seasonal pointers."""
    table_of = {}   # palette folder -> seasonal table (tilesets sharing a palette folder share the table)
    with open(SEASONAL_H, "w", encoding="utf-8", newline="\n") as f:
        f.write("// TREY (4b, 6-S): seasonal tileset palettes for every region. Generated by tools/trey/season_art.py; do not edit.\n")
        f.write("// Summer uses the base art (NULL). Tiles are shared in every season for now (NULL).\n\n")
        for name, path in SEASONAL_TILESETS.items():
            if path in table_of:
                continue
            short = name.replace("gTileset_", "")
            table_of[path] = f"gTilesetSeasonal_{short}"
            for season in SEASONS:
                if season == "summer":
                    continue
                f.write(f"const u16 ALIGNED(4) gTilesetPalettes_{short}_{season.capitalize()}[][16] =\n{{\n")
                for i in range(pal_count(path)):
                    f.write(f'    INCBIN_U16("{path}/seasons/{season}/{i:02d}.gbapal"),\n')
                f.write("};\n\n")
            f.write(f"const struct TilesetSeasonGfx gTilesetSeasonal_{short}[TREY_SEASONS_COUNT] =\n{{\n")
            for season in SEASONS:
                pal = "NULL" if season == "summer" else f"gTilesetPalettes_{short}_{season.capitalize()}"
                f.write(f"    [SEASON_{season.upper()}] = {{ .tiles = NULL, .palettes = {pal} }},\n")
            f.write("};\n\n")
    for hf in sorted(set(HEADER_OF.values())):
        text = open(hf, encoding="utf-8").read()
        for name in SEASONAL_TILESETS:
            if HEADER_OF[name] != hf:
                continue
            start = text.index(f"const struct Tileset {name} =")
            end = text.index("};", start)
            block = text[start:end]
            if ".seasonal" not in block:
                block = block.rstrip() + f"\n    .seasonal = {table_of[SEASONAL_TILESETS[name]]}, // TREY (6-S)\n"
                text = text[:start] + block + text[end:]
        open(hf, "w", encoding="utf-8", newline="\n").write(text)
    print("season_art.py: wrote", SEASONAL_H, f"({len(table_of)} palette folders, {len(SEASONAL_TILESETS)} tilesets)")


if __name__ == "__main__":
    if not os.path.exists("Makefile"):
        print("Run from the project's root folder.")
        sys.exit(1)
    if len(sys.argv) >= 3 and sys.argv[1] == "--preview":
        preview(sys.argv[2], sys.argv[3].split(",") if len(sys.argv) >= 4 else None)
    elif len(sys.argv) >= 2 and sys.argv[1] == "--list":
        for name, path in SEASONAL_TILESETS.items():
            print(f"{name:40} {path} ({pal_count(path)} palettes, {HEADER_OF[name]})")
    elif len(sys.argv) >= 2 and sys.argv[1] == "--write":
        write_all()
        write_winter_layout()
        write_c_tables()
    else:
        print(__doc__)
