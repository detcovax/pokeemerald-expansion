#!/usr/bin/env python3
"""TREY: region map data and art (TREY_PLAN.md Phase 4, chunk 4a).

Run from the repo root:
    python3 tools/trey/region_maps.py --import        # one-time import from the sibling repos (safe to re-run)
    python3 tools/trey/region_maps.py --placeholders  # (re)draw the placeholder pages (Orange, Kitakami)
    python3 tools/trey/region_maps.py --preview DIR   # PNG of every page with its location grid

Pages ("region maps") and where their art comes from:
    HOENN               ours (graphics/pokenav/region_map/map.png, graphics/pokedex/region_map.png)
    KANTO, SEVII_123/45/67, JOHTO   ../pokehns-expansion (Heart & Soul)
    SINNOH              ../Sinnoh-pokeemerald-expansion
    ORANGE, KITAKAMI    placeholders drawn here from the location rectangles (Orange: replaced later from
                        the Orange Islands ROM; Kitakami: in its production phase)

Every location (MAPSEC) in src/data/region_map/region_map_sections.json gets:
    "trey_region": gameplay region (REGION_*)          Sevii counts as REGION_KANTO
    "trey_map":    region map page it is drawn on (TREY_REGION_MAP_*)
    x/y/width/height on that page (28x15 cells)
Per-page cell grids are written to src/data/region_map/trey_layouts.h.
"""
import json
import os
import re
import sys

from PIL import Image

SECTIONS_JSON = "src/data/region_map/region_map_sections.json"
LAYOUTS_H = "src/data/region_map/trey_layouts.h"
HOENN_LAYOUT_H = "src/data/region_map/region_map_layout.h"
HNS = "../pokehns-expansion"
SINNOH = "../Sinnoh-pokeemerald-expansion"
GRID_W, GRID_H = 28, 15

# Page order is also the L/R switching order on the map screens.
PAGES = ["KANTO", "SEVII_123", "SEVII_45", "SEVII_67", "ORANGE", "JOHTO", "HOENN", "SINNOH", "KITAKAMI"]
PAGE_FILE = {"HOENN": "", "KANTO": "_kanto", "SEVII_123": "_sevii_123", "SEVII_45": "_sevii_45",
             "SEVII_67": "_sevii_67", "ORANGE": "_orange", "JOHTO": "_johto", "SINNOH": "_sinnoh", "KITAKAMI": "_kitakami"}
PAGE_REGION = {"HOENN": "REGION_HOENN", "KANTO": "REGION_KANTO", "SEVII_123": "REGION_KANTO", "SEVII_45": "REGION_KANTO",
               "SEVII_67": "REGION_KANTO", "ORANGE": "REGION_ORANGE", "JOHTO": "REGION_JOHTO", "SINNOH": "REGION_SINNOH",
               "KITAKAMI": "REGION_KITAKAMI"}

SEVII_PAGES = {
    "SEVII_123": ["ONE_ISLAND", "TWO_ISLAND", "THREE_ISLAND", "KINDLE_ROAD", "TREASURE_BEACH", "CAPE_BRINK", "BOND_BRIDGE",
                  "THREE_ISLE_PORT", "MT_EMBER", "BERRY_FOREST", "THREE_ISLE_PATH", "EMBER_SPA", "SEVII_ISLE_6",
                  "SEVII_ISLE_7", "SEVII_ISLE_8", "SEVII_ISLE_9"],
    "SEVII_45": ["FOUR_ISLAND", "FIVE_ISLAND", "RESORT_GORGEOUS", "WATER_LABYRINTH", "FIVE_ISLE_MEADOW", "MEMORIAL_PILLAR",
                 "NAVEL_ROCK_FRLG", "ICEFALL_CAVE", "ROCKET_WAREHOUSE", "LOST_CAVE"],
    "SEVII_67": ["SEVEN_ISLAND", "SIX_ISLAND", "OUTCAST_ISLAND", "GREEN_PATH", "WATER_PATH", "RUIN_VALLEY", "TRAINER_TOWER",
                 "CANYON_ENTRANCE", "SEVAULT_CANYON", "TANOBY_RUINS", "SEVII_ISLE_22", "SEVII_ISLE_23", "SEVII_ISLE_24",
                 "TRAINER_TOWER_2", "DOTTED_HOLE", "PATTERN_BUSH", "ALTERING_CAVE_FRLG", "TANOBY_CHAMBERS", "TANOBY_KEY",
                 "BIRTH_ISLAND_FRLG", "MONEAN_CHAMBER", "LIPTOO_CHAMBER", "WEEPTH_CHAMBER", "DILFORD_CHAMBER",
                 "SCUFIB_CHAMBER", "RIXY_CHAMBER", "VIAPOIS_CHAMBER"],
}

# Johto: Heart & Soul's list, minus its fan-made places; renamed where our IDs would collide.
JOHTO_SKIP = {"MAPSEC_SINJOH", "MAPSEC_NEW_SINJOH", "MAPSEC_SNOWSWEPT_CAVERN", "MAPSEC_ROUTE_49", "MAPSEC_ROUTE_50",
              "MAPSEC_VICTORY_ROAD_HNS"}
JOHTO_RENAME = {"MAPSEC_ROCKET_HIDEOUT_HNS": "MAPSEC_MAHOGANY_HIDEOUT", "MAPSEC_OLIVINE_LIGHTHOUSE": "MAPSEC_OLIVINE_LIGHTHOUSE"}
JOHTO_NAMES = {"MAPSEC_OLIVINE_LIGHTHOUSE": "LIGHTHOUSE"}  # 16-character limit
# Canon HGSS places Heart & Soul doesn't list (no grid position yet).
JOHTO_EXTRA = [("MAPSEC_JOHTO_SAFARI_ZONE", "SAFARI ZONE"), ("MAPSEC_GOLDENROD_TUNNEL", "GOLDENROD TUNNEL"),
               ("MAPSEC_RADIO_TOWER", "RADIO TOWER"), ("MAPSEC_POKEATHLON_DOME", "POKéATHLON DOME"),
               ("MAPSEC_BELLCHIME_TRAIL", "BELLCHIME TRAIL"), ("MAPSEC_CLIFF_EDGE_GATE", "CLIFF EDGE GATE")]

SINNOH_RENAME = {"MAPSEC_POKEMON_LEAGUE": "MAPSEC_SINNOH_POKEMON_LEAGUE"}
SINNOH_NAMES = {"MAPSEC_ROUTE_219": "ROUTE 219", "MAPSEC_FIGHT_AREA": "FIGHT AREA", "MAPSEC_MT_CORONET": "MT. CORONET",
                "MAPSEC_MT_STARK": "STARK MOUNTAIN", "MAPSEC_SINNOH_POKEMON_LEAGUE": "POKéMON LEAGUE",
                "MAPSEC_SUNYSHORE_CITY": "SUNYSHORE CITY"}
SINNOH_EXTRA = [("MAPSEC_SINNOH_VICTORY_ROAD", "VICTORY ROAD"), ("MAPSEC_GREAT_MARSH", "GREAT MARSH"),
                ("MAPSEC_TROPHY_GARDEN", "TROPHY GARDEN"), ("MAPSEC_AMITY_SQUARE", "AMITY SQUARE"),
                ("MAPSEC_SOLACEON_RUINS", "SOLACEON RUINS"), ("MAPSEC_LOST_TOWER", "LOST TOWER"),
                ("MAPSEC_SNOWPOINT_TEMPLE", "SNOWPOINT TEMPLE"), ("MAPSEC_SPEAR_PILLAR", "SPEAR PILLAR"),
                ("MAPSEC_HALL_OF_ORIGIN", "HALL OF ORIGIN"), ("MAPSEC_DISTORTION_WORLD", "DISTORTION WORLD"),
                ("MAPSEC_TURNBACK_CAVE", "TURNBACK CAVE"), ("MAPSEC_SENDOFF_SPRING", "SENDOFF SPRING"),
                ("MAPSEC_FULLMOON_ISLAND", "FULLMOON ISLAND"), ("MAPSEC_NEWMOON_ISLAND", "NEWMOON ISLAND"),
                ("MAPSEC_FLOWER_PARADISE", "FLOWER PARADISE"), ("MAPSEC_SEABREAK_PATH", "SEABREAK PATH"),
                ("MAPSEC_SPRING_PATH", "SPRING PATH"), ("MAPSEC_GALACTIC_HQ", "GALACTIC HQ"),
                ("MAPSEC_MANIAC_TUNNEL", "MANIAC TUNNEL"), ("MAPSEC_PAL_PARK", "PAL PARK"),
                ("MAPSEC_BATTLE_PARK", "BATTLE PARK")]

# Orange Islands: the anime's islands for now (renamed later from the Orange Islands ROM hack).
# (id, name, x, y, w, h, kind) kind: T town/island with a centre, L landmark, R sea route
ORANGE = [
    ("VALENCIA_ISLAND", "VALENCIA ISLAND", 2, 12, 1, 1, "T"),
    ("TANGELO_ISLAND", "TANGELO ISLAND", 4, 10, 1, 1, "T"),
    ("PINKAN_ISLAND", "PINKAN ISLAND", 6, 12, 1, 1, "L"),
    ("MIKAN_ISLAND", "MIKAN ISLAND", 7, 9, 1, 1, "T"),
    ("SUNBURST_ISLAND", "SUNBURST ISLAND", 9, 11, 1, 1, "T"),
    ("GOLDEN_ISLAND", "GOLDEN ISLAND", 10, 13, 1, 1, "L"),
    ("CLEOPATRA_ISLAND", "CLEOPATRA ISLAND", 11, 8, 1, 1, "L"),
    ("NAVEL_ISLAND", "NAVEL ISLAND", 12, 5, 1, 1, "T"),
    ("TROVITA_ISLAND", "TROVITA ISLAND", 14, 8, 1, 1, "T"),
    ("MORO_ISLAND", "MORO ISLAND", 15, 12, 1, 1, "T"),
    ("FAIRCHILD_ISLAND", "FAIRCHILD ISLAND", 16, 10, 1, 1, "L"),
    ("MANDARIN_NORTH", "MANDARIN NORTH", 17, 4, 1, 1, "T"),
    ("KUMQUAT_ISLAND", "KUMQUAT ISLAND", 18, 7, 1, 1, "T"),
    ("MANDARIN_SOUTH", "MANDARIN SOUTH", 18, 12, 1, 1, "T"),
    ("ASCORBIA_ISLAND", "ASCORBIA ISLAND", 20, 10, 1, 1, "L"),
    ("HAMLIN_ISLAND", "HAMLIN ISLAND", 21, 5, 1, 1, "T"),
    ("MURCOTT_ISLAND", "MURCOTT ISLAND", 20, 13, 1, 1, "T"),
    ("GRAPEFRUIT_ISLES", "GRAPEFRUIT ISLES", 22, 8, 2, 1, "L"),
    ("BUTWAL_ISLAND", "BUTWAL ISLAND", 19, 2, 1, 1, "T"),
    ("KINNOW_ISLAND", "KINNOW ISLAND", 22, 2, 1, 1, "T"),
    ("PUMMELO_ISLAND", "PUMMELO ISLAND", 25, 3, 1, 1, "T"),
    ("SHAMOUTI_ISLAND", "SHAMOUTI ISLAND", 24, 11, 1, 1, "T"),
    ("FIRE_ISLAND", "FIRE ISLAND", 23, 13, 1, 1, "L"),
    ("ICE_ISLAND", "ICE ISLAND", 26, 9, 1, 1, "L"),
    ("LIGHTNING_ISLAND", "LIGHTNING ISLAND", 26, 13, 1, 1, "L"),
]

# Kitakami (Teal Mask). Rough positions on a placeholder map.
KITAKAMI = [
    ("MOSSUI_TOWN", "MOSSUI TOWN", 9, 8, 1, 1, "T"),
    ("APPLE_HILLS", "APPLE HILLS", 6, 6, 2, 1, "L"),
    ("KITAKAMI_ROAD", "KITAKAMI ROAD", 10, 8, 3, 1, "R"),
    ("REVELERS_ROAD", "REVELER'S ROAD", 13, 9, 3, 1, "R"),
    ("KITAKAMI_HALL", "KITAKAMI HALL", 16, 9, 1, 1, "T"),
    ("LOYALTY_PLAZA", "LOYALTY PLAZA", 15, 7, 1, 1, "L"),
    ("ONI_MOUNTAIN", "ONI MOUNTAIN", 11, 4, 2, 2, "L"),
    ("ONIS_MAW", "ONI'S MAW", 13, 5, 1, 1, "L"),
    ("CRYSTAL_POOL", "CRYSTAL POOL", 12, 3, 1, 1, "L"),
    ("TIMELESS_WOODS", "TIMELESS WOODS", 5, 10, 2, 2, "L"),
    ("WISTFUL_FIELDS", "WISTFUL FIELDS", 14, 11, 2, 1, "L"),
    ("PARADISE_BARRENS", "PARADISE BARRENS", 18, 12, 2, 1, "L"),
    ("FELLHORN_GORGE", "FELLHORN GORGE", 17, 5, 2, 1, "L"),
    ("INFERNAL_PASS", "INFERNAL PASS", 14, 2, 1, 1, "L"),
    ("CHILLING_WATERHEAD", "WATERHEAD", 9, 2, 1, 1, "L"),
    ("DREAMING_POND", "DREAMING POND", 4, 4, 1, 1, "L"),
    ("MOSSFELL_CONFLUENCE", "MOSSFELL", 8, 11, 1, 1, "L"),
]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def read_grid(path):
    """A 28x15 MAPSEC grid from a C header (any variable name/type)."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    rows = re.findall(r"\{([^{}]*)\}", text.split("=", 1)[1])
    grid = [[c.strip() for c in row.split(",") if c.strip()] for row in rows]
    grid = [r for r in grid if len(r) == GRID_W]
    assert len(grid) == GRID_H, (path, len(grid))
    return grid


def grid_rects(grid):
    """Bounding box of each MAPSEC in a grid."""
    boxes = {}
    for y, row in enumerate(grid):
        for x, sec in enumerate(row):
            if sec == "MAPSEC_NONE":
                continue
            x0, y0, x1, y1 = boxes.get(sec, (x, y, x, y))
            boxes[sec] = (min(x0, x), min(y0, y), max(x1, x), max(y1, y))
    return {k: (a, b, c - a + 1, d - b + 1) for k, (a, b, c, d) in boxes.items()}


def rect_grid(sections, page):
    grid = [["MAPSEC_NONE"] * GRID_W for _ in range(GRID_H)]
    for s in sections:
        if s.get("trey_map") != f"TREY_REGION_MAP_{page}" or "x" not in s:
            continue
        for yy in range(s["y"], s["y"] + s.get("height", 1)):
            for xx in range(s["x"], s["x"] + s.get("width", 1)):
                if 0 <= xx < GRID_W and 0 <= yy < GRID_H and grid[yy][xx] == "MAPSEC_NONE":
                    grid[yy][xx] = s["id"]
    return grid


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------
def import_all():
    data = load_json(SECTIONS_JSON)
    secs = data["map_sections"]
    ids = [s["id"] for s in secs]
    by_id = {s["id"]: s for s in secs}
    kanto0, kanto1 = ids.index("MAPSEC_PALLET_TOWN"), ids.index("MAPSEC_SPECIAL_AREA")
    sevii = {f"MAPSEC_{n}": page for page, names in SEVII_PAGES.items() for n in names}
    hns = load_json(f"{HNS}/src/data/region_map/region_map_sections.json")
    hns_main = {s["id"]: s for s in hns["map_sections"]}

    # Existing sections: region and page. Kanto/Sevii coordinates come from Heart & Soul (FRLG layout).
    for i, s in enumerate(secs):
        if s["id"] == "MAPSEC_NONE":
            continue
        if kanto0 <= i <= kanto1:
            page = sevii.get(s["id"], "KANTO")
            src = hns_main.get(s["id"])
            if src is not None and "x" in src:
                for k in ("x", "y", "width", "height"):
                    s[k] = src[k]
        else:
            page = s.get("trey_map", "TREY_REGION_MAP_HOENN").replace("TREY_REGION_MAP_", "")
        s.setdefault("trey_map", f"TREY_REGION_MAP_{page}")
        s.setdefault("trey_region", PAGE_REGION[page])

    def add(sid, name, page, rect=None):
        if sid in by_id:
            return by_id[sid]
        assert len(name) <= 16, name
        entry = {"id": sid, "name": name}
        if rect is not None:
            entry.update({"x": rect[0], "y": rect[1], "width": rect[2], "height": rect[3]})
        entry["trey_region"] = PAGE_REGION[page]
        entry["trey_map"] = f"TREY_REGION_MAP_{page}"
        secs.append(entry)
        by_id[sid] = entry
        return entry

    # Johto
    hs = hns["hns_map_sections"]
    hids = [s["id"] for s in hs]
    for s in hs[hids.index("MAPSEC_NEW_BARK_TOWN"):hids.index("MAPSEC_WHIRL_ISLANDS") + 1]:
        if s["id"] in JOHTO_SKIP:
            continue
        sid = JOHTO_RENAME.get(s["id"], s["id"])
        name = JOHTO_NAMES.get(sid, s["name"])
        rect = (s["x"], s["y"], s["width"], s["height"]) if "x" in s else None
        add(sid, name, "JOHTO", rect)
    for sid, name in JOHTO_EXTRA:
        add(sid, name, "JOHTO")

    # Sinnoh
    sin = load_json(f"{SINNOH}/src/data/region_map/region_map_sections.json")["map_sections"]
    sids = [s["id"] for s in sin]
    sin_grid = rename_grid(read_grid(f"{SINNOH}/src/data/region_map/region_map_layout.h"), SINNOH_RENAME)
    sin_rects = grid_rects(sin_grid)
    for s in sin[sids.index("MAPSEC_TWINLEAF_TOWN"):sids.index("MAPSEC_POKEMON_LEAGUE", sids.index("MAPSEC_TWINLEAF_TOWN")) + 1]:
        sid = SINNOH_RENAME.get(s["id"], s["id"])
        name = SINNOH_NAMES.get(sid, s["name"])
        rect = sin_rects.get(sid)
        if rect is None and "x" in s and s["x"] is not None:
            rect = (s["x"], s["y"], s.get("width", 1), s.get("height", 1))
        add(sid, name, "SINNOH", rect)
    for sid, name in SINNOH_EXTRA:
        add(sid, name, "SINNOH")

    # Orange and Kitakami
    for (sid, name, x, y, w, h, _) in ORANGE:
        add(f"MAPSEC_{sid}", name, "ORANGE", (x, y, w, h))
    for (sid, name, x, y, w, h, _) in KITAKAMI:
        add(f"MAPSEC_{sid}", name, "KITAKAMI", (x, y, w, h))

    write_json(SECTIONS_JSON, data)
    print(f"region_maps.py: {len(secs)} locations")

    # Grids
    known = set(by_id)
    grids = {
        "HOENN": read_grid(HOENN_LAYOUT_H),
        "KANTO": read_grid("src/data/region_map/region_map_layout_kanto.h"),  # upstream FRLG (expansion 1.16)
        "SEVII_123": read_grid("src/data/region_map/region_map_layout_sevii123.h"),  # upstream FRLG (expansion 1.16)
        "SEVII_45": read_grid("src/data/region_map/region_map_layout_sevii45.h"),  # upstream FRLG (expansion 1.16)
        "SEVII_67": read_grid("src/data/region_map/region_map_layout_sevii67.h"),  # upstream FRLG (expansion 1.16)
        "JOHTO": rename_grid(read_grid(f"{HNS}/src/data/region_map/region_map_layout_johto.h"), JOHTO_RENAME),
        "SINNOH": sin_grid,
    }
    for page in ("ORANGE", "KITAKAMI"):
        grids[page] = rect_grid(secs, page)
    for page, grid in grids.items():
        for row in grid:
            for i, sec in enumerate(row):
                if sec not in known and sec != "MAPSEC_NONE":
                    print(f"  {page}: {sec} is not a TREY location; left empty")
                    row[i] = "MAPSEC_NONE"
    write_layouts(grids)

    # Art
    # Kanto and Sevii art is upstream's FRLG art since expansion 1.16 (D25), so it is not copied.
    copy_art(f"{HNS}/graphics/pokenav/region_map/map_johto", "graphics/pokenav/region_map/map_johto")
    copy_art(f"{SINNOH}/graphics/pokenav/region_map/map", "graphics/pokenav/region_map/map_sinnoh")
    copy_art(f"{HNS}/graphics/pokedex/region_map_johto", "graphics/pokedex/region_map_johto")
    copy_art(f"{SINNOH}/graphics/pokedex/region_map", "graphics/pokedex/region_map_sinnoh")
    draw_placeholders(secs, grids)


def rename_grid(grid, renames):
    return [[renames.get(c, c) for c in row] for row in grid]


def write_pal(path, colors):
    with open(path, "w", newline="\r\n") as f:
        f.write("JASC-PAL\n0100\n%d\n" % len(colors))
        for r, g, b in colors:
            f.write(f"{r} {g} {b}\n")


def map_pal_slice(pal):
    """The map screens load 48 colours into BG palettes 7-9 (8bpp indices 112-159): the .pal holds just those."""
    pal = list(pal) + [0] * (768 - len(pal))
    return [tuple(pal[i * 3:i * 3 + 3]) for i in range(112, 160)]


def copy_art(src, dst):
    im = Image.open(src + ".png")
    im.save(dst + ".png")
    with open(src + ".bin", "rb") as f, open(dst + ".bin", "wb") as g:
        g.write(f.read())
    write_pal(dst + ".pal", map_pal_slice(im.getpalette()))


def write_layouts(grids):
    with open(LAYOUTS_H, "w", encoding="utf-8", newline="\n") as f:
        f.write("// TREY: MAPSEC grid of every region map page (28x15 cells). Generated by tools/trey/region_maps.py; do not edit.\n")
        f.write("// Hoenn is copied from region_map_layout.h, Kanto/Sevii/Johto from Heart & Soul, Sinnoh from the Sinnoh repo,\n")
        f.write("// Orange and Kitakami from the location rectangles in region_map_sections.json.\n\n")
        for page in PAGES:
            f.write(f"static const u16 sTreyRegionMapLayout_{page}[MAP_HEIGHT][MAP_WIDTH] =\n{{\n")
            for row in grids[page]:
                f.write("    {" + ", ".join(row) + "},\n")
            f.write("};\n\n")
        f.write("static const u16 (*const sTreyRegionMapLayouts[TREY_REGION_MAP_COUNT])[MAP_WIDTH] =\n{\n")
        for page in PAGES:
            f.write(f"    [TREY_REGION_MAP_{page}] = sTreyRegionMapLayout_{page},\n")
        f.write("};\n")


# ---------------------------------------------------------------------------
# Placeholder art (Orange, Kitakami)
# ---------------------------------------------------------------------------
def nearest(pal, rgb, lo=112, hi=159):
    best, bd = lo, 1 << 30
    for i in range(lo, hi + 1):
        r, g, b = pal[i * 3:i * 3 + 3]
        d = (r - rgb[0]) ** 2 + (g - rgb[1]) ** 2 + (b - rgb[2]) ** 2
        if d < bd:
            best, bd = i, d
    return best


def placeholder_pixels(sections, page, kinds):
    """240x160 picture (index-free RGB) of a page: sea, land round every location, routes, town dots."""
    W, H = 30 * 8, 20 * 8
    SEA, LAND, LAND2, ROUTE, TOWN, LANDMARK = (148, 196, 236), (104, 176, 72), (72, 148, 56), (232, 184, 72), (224, 64, 56), (64, 112, 216)
    img = Image.new("RGB", (W, H), SEA)
    px = img.load()
    cells = [s for s in sections if s.get("trey_map") == f"TREY_REGION_MAP_{page}" and "x" in s]
    def cell_box(s):
        x0 = (s["x"] + 1) * 8
        y0 = (s["y"] + 2) * 8
        return x0, y0, x0 + s.get("width", 1) * 8, y0 + s.get("height", 1) * 8
    # land: a rounded blob around every location (Kitakami: big overlapping blobs make one island,
    # with darker high ground round the mountain locations)
    import math
    big = page == "KITAKAMI"
    for s in cells:
        x0, y0, x1, y1 = cell_box(s)
        r = 15 if big else 5
        for y in range(max(0, y0 - r), min(H, y1 + r)):
            for x in range(max(0, x0 - r), min(W, x1 + r)):
                dx = max(x0 - x, 0, x - (x1 - 1))
                dy = max(y0 - y, 0, y - (y1 - 1))
                wobble = 2 * math.sin(x * 0.7 + y * 0.3) + 1.5 * math.cos(y * 0.9 - x * 0.2) if big else 0
                if dx * dx + dy * dy <= (r + wobble) ** 2:
                    high = big and ("ONI" in s["id"] or "CRYSTAL" in s["id"] or "INFERNAL" in s["id"]) and dx * dx + dy * dy <= 64
                    if px[x, y] == SEA or high:
                        px[x, y] = LAND2 if high else (LAND if (x // 4 + y // 4) % 5 else LAND2)
    for s in cells:
        x0, y0, x1, y1 = cell_box(s)
        kind = kinds.get(s["id"], "L")
        for y in range(y0, y1):
            for x in range(x0, x1):
                if kind == "R":
                    if y0 + 2 <= y < y1 - 2 or (y1 - y0 > 8 and x0 + 2 <= x < x1 - 2):
                        px[x, y] = ROUTE
                elif kind == "T":
                    if x0 + 1 <= x < x1 - 1 and y0 + 1 <= y < y1 - 1:
                        px[x, y] = TOWN if (x0 + 2 <= x < x1 - 2 and y0 + 2 <= y < y1 - 2) else (248, 248, 248)
                else:
                    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                    if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= 6:
                        px[x, y] = LANDMARK
    return img


def to_indexed(img, pal_src):
    im = Image.open(pal_src)
    pal = im.getpalette()
    out = Image.new("P", img.size)
    out.putpalette(pal)
    cache = {}
    src = img.load()
    dst = out.load()
    for y in range(img.size[1]):
        for x in range(img.size[0]):
            c = src[x, y]
            if c not in cache:
                cache[c] = nearest(pal, c)
            dst[x, y] = cache[c]
    return out, pal


def tiles_of(indexed):
    w, h = indexed.size
    px = indexed.load()
    tiles, order, tilemap = [], {}, []
    for ty in range(h // 8):
        for tx in range(w // 8):
            t = tuple(px[tx * 8 + x, ty * 8 + y] for y in range(8) for x in range(8))
            if t not in order:
                order[t] = len(tiles)
                tiles.append(t)
            tilemap.append(order[t])
    return tiles, tilemap


def sheet(tiles, pal):
    rows = (len(tiles) + 15) // 16
    im = Image.new("P", (128, max(8, rows * 8)))
    im.putpalette(pal)
    px = im.load()
    for i, t in enumerate(tiles):
        ox, oy = (i % 16) * 8, (i // 16) * 8
        for k, v in enumerate(t):
            px[ox + k % 8, oy + k // 8] = v
    return im


def write_page_art(picture, dst_nav, dst_dex):
    # Pokénav/fly map: 8bpp affine BG, 64x64 one-byte tilemap; the picture is the top-left 30x20 tiles.
    indexed, pal = to_indexed(picture, "graphics/pokenav/region_map/map.png")
    tiles, tm = tiles_of(indexed)
    sea_tile = tm[0]
    assert len(tiles) <= 256, len(tiles)
    full = bytearray([sea_tile] * 64 * 64)
    for i, t in enumerate(tm):
        full[(i // 30) * 64 + i % 30] = t
    sheet(tiles, pal).save(dst_nav + ".png")
    with open(dst_nav + ".bin", "wb") as f:
        f.write(full)
    write_pal(dst_nav + ".pal", map_pal_slice(pal))
    # Pokédex area map: 8bpp text BG, 32x32 two-byte tilemap (same picture).
    indexed, pal = to_indexed(picture, "graphics/pokedex/region_map.png")
    tiles, tm = tiles_of(indexed)
    sea_tile = tm[0]
    full = [sea_tile] * 32 * 32
    for i, t in enumerate(tm):
        full[(i // 30) * 32 + i % 30] = t
    sheet(tiles, pal).save(dst_dex + ".png")
    with open(dst_dex + ".bin", "wb") as f:
        for t in full:
            f.write(bytes([t & 0xFF, t >> 8]))
    write_pal(dst_dex + ".pal", map_pal_slice(pal))


def draw_placeholders(secs=None, grids=None):
    if secs is None:
        secs = load_json(SECTIONS_JSON)["map_sections"]
    kinds = {f"MAPSEC_{e[0]}": e[6] for e in ORANGE + KITAKAMI}
    for page in ("ORANGE", "KITAKAMI"):
        pic = placeholder_pixels(secs, page, kinds)
        write_page_art(pic, f"graphics/pokenav/region_map/map{PAGE_FILE[page]}", f"graphics/pokedex/region_map{PAGE_FILE[page]}")
    print("region_maps.py: placeholder pages drawn (ORANGE, KITAKAMI)")


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------
def render_nav(page):
    base = f"graphics/pokenav/region_map/map{PAGE_FILE[page]}"
    im = Image.open(base + ".png")
    tw = im.size[0] // 8
    ent = open(base + ".bin", "rb").read()
    side = 64
    canvas = Image.new("P", (30 * 8, 20 * 8))
    canvas.putpalette(im.getpalette())
    for i, t in enumerate(ent):
        x, y = i % side, i // side
        if x >= 30 or y >= 20:
            continue
        tx, ty = (t % tw) * 8, (t // tw) * 8
        if ty < im.size[1]:
            canvas.paste(im.crop((tx, ty, tx + 8, ty + 8)), (x * 8, y * 8))
    return canvas.convert("RGB")


def preview(out):
    from PIL import ImageDraw
    os.makedirs(out, exist_ok=True)
    secs = load_json(SECTIONS_JSON)["map_sections"]
    with open(LAYOUTS_H, encoding="utf-8") as f:
        text = f.read()
    for page in PAGES:
        m = re.search(r"sTreyRegionMapLayout_%s\[MAP_HEIGHT\]\[MAP_WIDTH\] =\n\{\n(.*?)\n\};" % page, text, re.S)
        grid = [[c.strip() for c in row.strip().strip("{},").split(",")] for row in m.group(1).split("\n")]
        pic = render_nav(page).resize((480, 320), Image.NEAREST)
        d = ImageDraw.Draw(pic, "RGBA")
        for y, row in enumerate(grid):
            for x, sec in enumerate(row):
                if sec != "MAPSEC_NONE":
                    X, Y = (x + 1) * 16, (y + 2) * 16
                    d.rectangle((X, Y, X + 15, Y + 15), outline=(255, 0, 255, 160))
        names = sorted({c for row in grid for c in row if c != "MAPSEC_NONE"})
        pic.save(f"{out}/page_{page.lower()}.png")
        print(page, len(names), "locations on the grid")


if __name__ == "__main__":
    if not os.path.exists("Makefile"):
        print("Run from the project's root folder.")
        sys.exit(1)
    if len(sys.argv) >= 2 and sys.argv[1] == "--import":
        import_all()
    elif len(sys.argv) >= 2 and sys.argv[1] == "--placeholders":
        draw_placeholders()
    elif len(sys.argv) >= 3 and sys.argv[1] == "--preview":
        preview(sys.argv[2])
    else:
        print(__doc__)
