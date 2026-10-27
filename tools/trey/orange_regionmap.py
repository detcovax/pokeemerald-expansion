"""TREY (6c-4a, TREY_PLAN.md D40/D41): the Orange region map page from the Orange Islands ROM hack.

The hack draws the Orange Islands on FireRed's "Sevii 1-2-3" page (FireRed 1.0 code: the tilemap pointer at 0xC0370,
the shared map tiles at 0xC0330, the palette at 0xC02EC, the 22x15 two-layer location grid at 0xC419C).
FireRed puts grid cell (0,0) at screen tile (4,4); TREY pages put it at (1,2), so the art moves 3 tiles left and
2 up. Cells keep their x/y, so the hack's grid lands in columns 0-21 of TREY's 28x15 grid.

Written (run `python3 tools/trey/import_orange.py regionmap` from the project root):
  graphics/pokenav/region_map/map_orange.{png,bin,pal}   fly / Pokenav map (8bpp, colours 112-159)
  graphics/pokedex/region_map_orange.{png,bin,pal}       Pokedex area map (same picture)
  src/data/region_map/region_map_sections.json          Orange locations: positions, names, new MAPSECs (appended)
  src/data/region_map/trey_layouts.h                    the ORANGE page grid
  docs/trey/orange_region_map.json                      the ORANGE grid (tools/trey/region_maps.py --import reads it)
  docs/trey/orange_mapsecs.json                         hack location id -> TREY MAPSEC, or "parent" (6c-4b
                                                         gives those maps the location of the place they open from)
"""
import collections
import json
import re
import struct

from PIL import Image

PTR_PAL, PTR_GFX, PTR_TILEMAP, PTR_GRID = 0xC02EC, 0xC0330, 0xC0370, 0xC419C
GRID_W, GRID_H, TREY_W = 22, 15, 28
HACK_NONE = 0xC5
SHIFT_X, SHIFT_Y = 3, 2          # FireRed cell origin (4,4) -> TREY (1,2)
LAYOUTS_H = "src/data/region_map/trey_layouts.h"
SECTIONS_JSON = "src/data/region_map/region_map_sections.json"

# Hack location -> TREY MAPSEC id, name. Existing TREY ids are reused; names follow the hack (16-character limit).
# Ids not listed (the hack's leftover Sevii names and its generic "KANTO") are "parent" places (D41).
LOCATIONS = {
    0x58: ("MAPSEC_ORANGE_PALLET_TOWN", "ORANGE PALLET"),
    0x59: ("MAPSEC_ORANGE_ROUTE_1", "ORANGE ROUTE 1"),
    0x5A: ("MAPSEC_TANGELO_ISLAND", "TANGELO ISLAND"),
    0x5B: ("MAPSEC_MIKAN_ISLAND", "MIKAN ISLAND"),
    0x5C: ("MAPSEC_MANDARIN_NORTH", "MANDARIN NORTH"),
    0x5D: ("MAPSEC_SUNBURST_ISLAND", "SUNBURST ISLAND"),
    0x5E: ("MAPSEC_TROVITOPOLIS", "TROVITOPOLIS"),
    0x5F: ("MAPSEC_NAVEL_ISLAND", "NAVEL ISLAND"),
    0x60: ("MAPSEC_MORO_ISLAND", "MORO ISLAND"),
    0x61: ("MAPSEC_MURCOTT_ISLAND", "MURCOTT ISLAND"),
    0x62: ("MAPSEC_MANDARIN_SOUTH", "MANDARIN SOUTH"),
    0x63: ("MAPSEC_YAMBERA", "YAMBERA"),
    0x64: ("MAPSEC_KINNOW_ISLAND", "KINNOW ISLAND"),
    0x65: ("MAPSEC_VALENCIA_ISLAND", "VALENCIA ISLAND"),
    0x6C: ("MAPSEC_PINKAN_ISLAND", "PINKAN ISLAND"),
    0x6F: ("MAPSEC_FUKUHARA_ISLAND", "FUKUHARA ISLAND"),
    0x73: ("MAPSEC_GRAPEFRUIT_ISLES", "GRAPEFRUIT ISLES"),   # hack: GRAPEFRUIT ISLANDS (18 characters)
    0x76: ("MAPSEC_GOLDEN_ISLAND", "GOLDEN ISLAND"),
    0x7E: ("MAPSEC_VALENCIA_PARK", "VALENCIA PARK"),
    0x7F: ("MAPSEC_POKEMON_PARK", "POKéMON PARK"),
    0x80: ("MAPSEC_POKEMON_SHOWBOAT", "POKéMON SHOWBOAT"),
    0x81: ("MAPSEC_ORANGE_SEWERS", "SEWERS"),
    0x82: ("MAPSEC_NAVEL_MOUNTAIN", "NAVEL MOUNTAIN"),
    0x83: ("MAPSEC_CRYSTAL_CAVE", "CRYSTAL CAVE"),
    0x84: ("MAPSEC_BAY_CAVE", "BAY CAVE"),
    0x85: ("MAPSEC_ORANGE_ROCKET_HIDEOUT", "ROCKET HIDEOUT"),
    0x86: ("MAPSEC_OLD_SILPH_CO", "OLD SILPH. CO"),
    0x87: ("MAPSEC_FAIRCHILD_ISLAND", "FAIRCHILD ISLAND"),
    0x88: ("MAPSEC_LIGHTNING_ISLAND", "LIGHTNING ISLAND"),
    0x89: ("MAPSEC_ORANGE_LEAGUE", "ORANGE LEAGUE"),
    0x8A: ("MAPSEC_CLEOPATRA_ISLAND", "CLEOPATRA ISLAND"),
    0x8B: ("MAPSEC_ASCORBIA_FOREST", "ASCORBIA FOREST"),
    0x8C: ("MAPSEC_BUTWAL_ISLAND", "BUTWAL ISLAND"),
    0x8D: ("MAPSEC_ICE_ISLAND", "ICE ISLAND"),
    0x8E: ("MAPSEC_RIND_ISLAND", "RIND ISLAND"),
    0x8F: ("MAPSEC_TROVITA_ISLAND", "TROVITA ISLAND"),
    0x90: ("MAPSEC_SHAMOUTI_ISLAND", "SHAMOUTI ISLAND"),
    0x91: ("MAPSEC_ASCORBIA_ISLAND", "ASCORBIA ISLAND"),
    0x92: ("MAPSEC_KUMQUAT_ISLAND", "KUMQUAT ISLAND"),
    0x93: ("MAPSEC_PUMMELO_ISLAND", "PUMMELO ISLAND"),
    0x94: ("MAPSEC_TARROCO_ISLAND", "TARROCO ISLAND"),
    0x95: ("MAPSEC_HAMLIN_ISLAND", "HAMLIN ISLAND"),
    0x9F: ("MAPSEC_ORANGE_UNDERWATER", "UNDERWATER"),
    0xA0: ("MAPSEC_ORANGE_UNDERWATER", "UNDERWATER"),
    0xA1: ("MAPSEC_HAMLIN_FIELDS", "HAMLIN FIELDS"),
    0xA4: ("MAPSEC_NEW_ISLAND", "NEW ISLAND"),
    0xAF: ("MAPSEC_SALVEYO_ISLAND", "SALVEYO ISLAND"),
    0xB0: ("MAPSEC_FIRE_ISLAND", "FIRE ISLAND"),
    0xB1: ("MAPSEC_MURCOTT_MEADOWS", "MURCOTT MEADOWS"),
    0xC4: ("MAPSEC_TROVITO_DEPT", "TROVITO DEPT."),
}
# Sea routes. The hack has two ids for some (E, F, I, Q, R): they become one TREY location each.
_ROUTE_IDS = {0x66: "A", 0x67: "B", 0x68: "C", 0x69: "D", 0x6A: "E", 0x6B: "E", 0x6D: "F", 0x6E: "F", 0x70: "G",
              0x71: "H", 0x72: "I", 0x74: "I", 0x75: "J", 0x77: "K", 0x78: "L", 0x79: "M", 0x7A: "N", 0x7B: "O",
              0x7C: "P", 0x7D: "Q", 0x96: "Q", 0x97: "R", 0x98: "R", 0x99: "S", 0x9A: "T", 0x9B: "U", 0x9C: "V",
              0x9D: "W", 0x9E: "X"}
for _k, _c in _ROUTE_IDS.items():
    LOCATIONS[_k] = (f"MAPSEC_ORANGE_ROUTE_{_c}", f"ROUTE {_c}")

# Places the hack doesn't draw (D41): they sit at the position of the place they open from (no cell of their own).
PARENT_SPOT = {
    "MAPSEC_POKEMON_SHOWBOAT": "MAPSEC_KINNOW_ISLAND", "MAPSEC_ORANGE_SEWERS": "MAPSEC_TROVITOPOLIS",
    "MAPSEC_NAVEL_MOUNTAIN": "MAPSEC_NAVEL_ISLAND", "MAPSEC_ORANGE_ROCKET_HIDEOUT": "MAPSEC_MANDARIN_NORTH",
    "MAPSEC_OLD_SILPH_CO": "MAPSEC_SHAMOUTI_ISLAND", "MAPSEC_LIGHTNING_ISLAND": "MAPSEC_NAVEL_ISLAND",
    "MAPSEC_ORANGE_LEAGUE": "MAPSEC_PUMMELO_ISLAND", "MAPSEC_ICE_ISLAND": "MAPSEC_MIKAN_ISLAND",
    "MAPSEC_ORANGE_UNDERWATER": "MAPSEC_ORANGE_ROUTE_H", "MAPSEC_HAMLIN_FIELDS": "MAPSEC_HAMLIN_ISLAND",
    "MAPSEC_NEW_ISLAND": "MAPSEC_SHAMOUTI_ISLAND", "MAPSEC_FIRE_ISLAND": "MAPSEC_SHAMOUTI_ISLAND",
    "MAPSEC_TROVITO_DEPT": "MAPSEC_TROVITOPOLIS",
}
# Orange Pallet and Orange Route 1 are on the hack's Kanto page: TREY gives them cells in the open sea (D41),
# with a small island and a route band drawn from the hack's own tiles (Mikan Island's corner of the page).
EXTRA_CELLS = {"MAPSEC_ORANGE_PALLET_TOWN": [(24, 8)], "MAPSEC_ORANGE_ROUTE_1": [(24, 9), (24, 10)]}
SWITCH_ICON_TILES = [(x, y) for x in range(21, 24) for y in range(14, 17)]   # FireRed's page-switch button: painted out


def _rgb(c):
    return ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)


def hack_picture(rom):
    """The hack's Orange page as a 240x160 RGB picture on TREY's cell origin."""
    pal_at = rom.off(rom.u32(PTR_PAL))
    pal = [_rgb(struct.unpack_from("<H", rom.d, pal_at + 2 * i)[0]) for i in range(80)]
    gfx = rom.lz77(rom.u32(PTR_GFX))
    tm = rom.lz77(rom.u32(PTR_TILEMAP))
    ents = struct.unpack_from("<600H", tm)
    src = Image.new("RGB", (240, 160))
    px = src.load()
    for i, e in enumerate(ents):
        t, hf, vf, p = e & 0x3FF, e >> 10 & 1, e >> 11 & 1, e >> 12
        x0, y0 = (i % 30) * 8, (i // 30) * 8
        for y in range(8):
            for x in range(8):
                o = t * 32 + y * 4 + x // 2
                v = gfx[o] >> (4 * (x & 1)) & 15 if o < len(gfx) else 0
                px[x0 + (7 - x if hf else x), y0 + (7 - y if vf else y)] = pal[(p * 16 + v) % 80]
    tile = lambda im, x, y: im.crop((x * 8, y * 8, x * 8 + 8, y * 8 + 8))
    common = collections.Counter(tile(src, x, y).tobytes() for y in range(20) for x in range(30))
    sea = Image.frombytes("RGB", (8, 8), common.most_common(1)[0][0])
    out = Image.new("RGB", (240, 160))
    for ty in range(20):
        for tx in range(30):
            sx, sy = tx + SHIFT_X, ty + SHIFT_Y
            t = sea
            if sx < 30 and sy < 20:
                c = tile(src, sx, sy)
                if not set(c.getdata()) <= {(248, 248, 248), (0, 0, 0)}:   # FireRed's frame and edge
                    t = c
            out.paste(t, (tx * 8, ty * 8))
    for tx, ty in SWITCH_ICON_TILES:
        out.paste(sea, (tx * 8, ty * 8))
    # Orange Pallet: Mikan Island's 3x3 tiles (town square, island, route band south) without the band from the west,
    # then one more route tile from Route Q's open-sea stretch.
    block = out.crop((1 * 8, 8 * 8, 4 * 8, 11 * 8))
    out.paste(block, (24 * 8, 9 * 8))
    for tx in (24, 25, 26):
        out.paste(sea, (tx * 8, 9 * 8))
    out.paste(tile(out, 13, 7), (25 * 8, 12 * 8))
    return out


def hack_grid(rom):
    base = rom.off(rom.u32(PTR_GRID))
    layers = []
    for layer in range(2):
        o = base + layer * GRID_W * GRID_H
        layers.append([list(rom.d[o + y * GRID_W:o + (y + 1) * GRID_W]) for y in range(GRID_H)])
    return layers


def _write_pal(path, colours):
    with open(path, "w", newline="\r\n") as f:
        f.write("JASC-PAL\n0100\n%d\n" % len(colours) + "".join(f"{r} {g} {b}\n" for r, g, b in colours))


def write_art(picture, nav_base, dex_base, write_pal=_write_pal):
    """8bpp pictures for both map screens, own colours at indices 112-159."""
    colours = sorted(set(picture.getdata()))
    assert len(colours) <= 48, len(colours)
    index = {c: 112 + i for i, c in enumerate(colours)}
    pal48 = colours + [(0, 0, 0)] * (48 - len(colours))
    flat = [0, 0, 0] * 112 + [v for c in pal48 for v in c] + [0, 0, 0] * 96
    tiles, order, tm = [], {}, []
    for ty in range(20):
        for tx in range(30):
            t = tuple(index[picture.getpixel((tx * 8 + x, ty * 8 + y))] for y in range(8) for x in range(8))
            if t not in order:
                order[t] = len(tiles)
                tiles.append(t)
            tm.append(order[t])
    assert len(tiles) <= 256, len(tiles)
    sheet = Image.new("P", (128, max(8, (len(tiles) + 15) // 16 * 8)))
    sheet.putpalette(flat)
    sp = sheet.load()
    for i, t in enumerate(tiles):
        for k, v in enumerate(t):
            sp[(i % 16) * 8 + k % 8, (i // 16) * 8 + k // 8] = v
    sea = collections.Counter(tm).most_common(1)[0][0]
    for base in (nav_base, dex_base):
        sheet.save(base + ".png")
        write_pal(base + ".pal", pal48)
    nav = bytearray([sea] * 64 * 64)            # Pokenav/fly: affine BG, 64x64 one-byte tilemap
    dex = [sea] * 32 * 32                      # Pokedex: text BG, 32x32 two-byte tilemap
    for i, t in enumerate(tm):
        nav[(i // 30) * 64 + i % 30] = t
        dex[(i // 30) * 32 + i % 30] = t
    open(nav_base + ".bin", "wb").write(nav)
    open(dex_base + ".bin", "wb").write(b"".join(bytes([t & 0xFF, t >> 8]) for t in dex))
    return len(tiles), len(colours)


def build(rom, dry=False):
    layers = hack_grid(rom)
    used = {b for layer in layers for row in layer for b in row if b != HACK_NONE}
    missing = sorted(b for b in used if b not in LOCATIONS)
    assert not missing, [hex(b) for b in missing]

    grid = [["MAPSEC_NONE"] * TREY_W for _ in range(GRID_H)]
    cells = collections.defaultdict(list)       # every cell of a location, map layer first
    for y in range(GRID_H):
        for x in range(GRID_W):
            b = layers[0][y][x]
            if b != HACK_NONE:
                grid[y][x] = LOCATIONS[b][0]
                cells[LOCATIONS[b][0]].append((x, y))
    for sid, xy in EXTRA_CELLS.items():
        for x, y in xy:
            assert grid[y][x] == "MAPSEC_NONE"
            grid[y][x] = sid
            cells[sid].append((x, y))
    # dungeon layer: position only (TREY grids have one layer, like the Kanto dungeons)
    spot = {}
    for y in range(GRID_H):
        for x in range(GRID_W):
            b = layers[1][y][x]
            if b != HACK_NONE:
                spot.setdefault(LOCATIONS[b][0], (x, y, 1, 1))
    for sid, xy in cells.items():
        xs, ys = [c[0] for c in xy], [c[1] for c in xy]
        spot[sid] = (min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
    for sid, parent in PARENT_SPOT.items():
        if sid not in spot:
            px, py = cells[parent][0]
            spot[sid] = (px, py, 1, 1)

    # sections json: update Orange entries, append new ones at the end (existing MAPSEC numbers don't move)
    data = json.load(open(SECTIONS_JSON, encoding="utf-8"))
    secs = data["map_sections"]
    by_id = {s["id"]: s for s in secs}
    names = {}
    for sid, name in LOCATIONS.values():
        names.setdefault(sid, name)
    added = []
    for sid, name in names.items():
        assert len(name) <= 16, name
        s = by_id.get(sid)
        if s is None:
            s = {"id": sid, "name": name}
            secs.append(s)
            by_id[sid] = s
            added.append(sid)
        elif s.get("trey_region") != "REGION_ORANGE":
            raise SystemExit(f"{sid} already exists outside Orange")
        s["name"] = name
        for k in ("x", "y", "width", "height"):
            s.pop(k, None)
        s.pop("trey_region", None)
        s.pop("trey_map", None)
        x, y, w, h = spot[sid]
        s.update({"x": x, "y": y, "width": w, "height": h,
                  "trey_region": "REGION_ORANGE", "trey_map": "TREY_REGION_MAP_ORANGE"})
    stale = [s["id"] for s in secs if s.get("trey_region") == "REGION_ORANGE" and s["id"] not in names]

    mapping = {}
    for b in range(0x58, 0xC5):
        mapping[f"{b:#04x}"] = LOCATIONS[b][0] if b in LOCATIONS else "parent"
    report = {"added": added, "stale_orange_ids": stale, "grid_cells": sum(c != "MAPSEC_NONE" for r in grid for c in r)}
    if dry:
        return report, None
    picture = hack_picture(rom)
    ntiles, ncols = write_art(picture, "graphics/pokenav/region_map/map_orange", "graphics/pokedex/region_map_orange")
    report.update({"tiles": ntiles, "colours": ncols})
    json.dump(data, open(SECTIONS_JSON, "w", encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False)
    open(SECTIONS_JSON, "a", encoding="utf-8", newline="\n").write("\n")
    json.dump({"grid": grid}, open("docs/trey/orange_region_map.json", "w", encoding="utf-8", newline="\n"), indent=0)
    json.dump(mapping, open("docs/trey/orange_mapsecs.json", "w", encoding="utf-8", newline="\n"), indent=1)
    text = open(LAYOUTS_H, encoding="utf-8").read()
    block = "".join("    {" + ", ".join(row) + "},\n" for row in grid)
    pat = re.compile(r"(static const u16 sTreyRegionMapLayout_ORANGE\[MAP_HEIGHT\]\[MAP_WIDTH\] =\n\{\n)(.*?)(\};)", re.S)
    assert pat.search(text)
    text = pat.sub(lambda m: m.group(1) + block + m.group(3), text, count=1)
    open(LAYOUTS_H, "w", encoding="utf-8", newline="\n").write(text)
    return report, picture
