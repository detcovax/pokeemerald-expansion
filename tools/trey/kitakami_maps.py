#!/usr/bin/env python3
"""TREY (6d-3, TREY_PLAN.md D47/D51): write Kitakami's hand-built map layouts and render PNG previews.

Kitakami has no source maps (D47). Each map here is a short list of drawing operations on the stamps of
docs/trey/kitakami_tiles.json (built by kitakami_tiles.py, 6d-1). Stamps are rectangles of map blocks
(metatile id | collision << 10 | elevation << 12) cut from existing Johto maps, so any crop of a stamp keeps its
source map's collision and elevation; the primary tileset's metatiles can be used directly by id.

Operations (x1/y1 exclusive everywhere; stamp coordinates are inside the stamp):
  ("fill", blk)                                   whole map
  ("rect", blk, x, y, w, h)                       one block over a rectangle
  ("put", blk, x, y)                              one block
  ("stamp", name, x, y)                           whole stamp, or ("stamp", name, x, y, (sx, sy, sw, sh)) for a crop
  ("tile", name, (sx, sy, pw, ph), x, y, w, h)    repeat a pattern; the phase follows map coordinates (x - x0)
  ("nine", name, (sx, sy, sw, sh), (l, t, r, b), x, y, w, h)
                                                  9-slice: corners/edges of the source rect kept, the middle
                                                  repeated, so a pond/plateau/field of any size keeps its edges
  ("box", grid, x, y, w, h)                       grid = 3x3 blocks (corners/edges/centre) stretched over a rect
  ("col", x, y, w, h, c)                        force collision c (0 walkable, 1 blocked) over a rectangle
A block `blk` is an int (raw block value) or ("stamp_name", sx, sy) (that stamp block) or
("id", metatile, collision[, elevation=3]).

Run from the repo root:
    python3 tools/trey/kitakami_maps.py preview OUTDIR [Map...]   # PNG per map (+ _col.png collision overlay)
    python3 tools/trey/kitakami_maps.py stamps OUTDIR             # every catalog stamp with a coordinate grid
    python3 tools/trey/kitakami_maps.py write [Map...]            # layouts: data/layouts/<Map>/*.bin + layouts.json
                                                                  # (only after David approved the previews)
"""
import json
import os
import struct
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kitakami_tiles as K  # noqa: E402
import season_art as S  # noqa: E402

CATALOG = "docs/trey/kitakami_tiles.json"
_cat = None
_ts = {}


def catalog():
    global _cat
    if _cat is None:
        _cat = json.load(open(CATALOG, encoding="utf-8"))
    return _cat


def tilesets(tname):
    """(primary, secondary) dicts for a Kitakami tileset, read back from the written files."""
    if tname not in _ts:
        entry = catalog()[tname]
        prim = K.tileset(entry["primary"])
        folder = K.Builder(tname[len("gTileset_"):]).folder()
        sec = S.load_tileset(folder, True)
        sec["attrs"] = [a for (a,) in struct.iter_unpack("<I", open(f"{folder}/metatile_attributes.bin", "rb").read())]
        _ts[tname] = (prim, sec, {})
    return _ts[tname]


def metatile_image(tname, mid):
    prim, sec, cache = tilesets(tname)
    if mid not in cache:
        cache[mid] = K.layers_image(K.metatile_layers(prim, sec, mid)[0])
    return cache[mid]


def attr(tname, mid):
    prim, sec, _ = tilesets(tname)
    if mid < K.NUM_PRI_MT:
        return prim["attrs"][mid]
    j = mid - K.NUM_PRI_MT
    return sec["attrs"][j] if j < len(sec["attrs"]) else 0


# ---------------------------------------------------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------------------------------------------------
class Canvas:
    def __init__(self, tname, w, h):
        self.tname, self.w, self.h = tname, w, h
        self.stamps = catalog()[tname]["stamps"]
        self.b = [[0] * w for _ in range(h)]

    def block(self, blk):
        if isinstance(blk, int):
            return blk
        if blk[0] == "id":
            return blk[1] | (blk[2] << 10) | ((blk[3] if len(blk) > 3 else 3) << 12)
        st = self.stamps[blk[0]]["blocks"]
        return st[blk[2]][blk[1]]

    def put(self, x, y, v):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.b[y][x] = v

    def src(self, name, sx, sy):
        return self.stamps[name]["blocks"][sy][sx]

    def run(self, ops):
        for op in ops:
            getattr(self, "op_" + op[0])(*op[1:])

    def op_fill(self, blk):
        self.op_rect(blk, 0, 0, self.w, self.h)

    def op_rect(self, blk, x, y, w, h):
        v = self.block(blk)
        for j in range(h):
            for i in range(w):
                self.put(x + i, y + j, v)

    def op_put(self, blk, x, y):
        self.put(x, y, self.block(blk))

    def op_stamp(self, name, x, y, crop=None):
        st = self.stamps[name]
        sx, sy, sw, sh = crop or (0, 0, st["w"], st["h"])
        for j in range(sh):
            for i in range(sw):
                self.put(x + i, y + j, self.src(name, sx + i, sy + j))

    def op_tile(self, name, pat, x, y, w, h):
        sx, sy, pw, ph = pat
        for j in range(h):
            for i in range(w):
                self.put(x + i, y + j, self.src(name, sx + i % pw, sy + j % ph))

    def op_nine(self, name, srect, margins, x, y, w, h):
        sx, sy, sw, sh = srect
        l, t, r, b = margins
        cw, ch = sw - l - r, sh - t - b

        def pick(i, n, lo, hi, mid):
            if i < lo:
                return i
            if i >= n - hi:
                return (lo + mid) + (i - (n - hi))
            return lo + (i - lo) % mid
        for j in range(h):
            for i in range(w):
                self.put(x + i, y + j, self.src(name, sx + pick(i, w, l, r, cw), sy + pick(j, h, t, b, ch)))

    def op_box(self, grid, x, y, w, h):
        """grid = 3x3 blocks (corners, edges, centre): a rect of any size >= 2x2 with those edges."""
        for j in range(h):
            r = 0 if j == 0 else (2 if j == h - 1 else 1)
            for i in range(w):
                c = 0 if i == 0 else (2 if i == w - 1 else 1)
                self.put(x + i, y + j, self.block(grid[r][c]))

    def op_col(self, x, y, w, h, c):
        for j in range(h):
            for i in range(w):
                if 0 <= x + i < self.w and 0 <= y + j < self.h:
                    self.b[y + j][x + i] = (self.b[y + j][x + i] & ~0xC00) | (c << 10)


def render(tname, blocks, grid=True, col=False, marks=()):
    h, w = len(blocks), len(blocks[0])
    img = Image.new("RGB", (w * 16, h * 16))
    for y, row in enumerate(blocks):
        for x, v in enumerate(row):
            img.paste(metatile_image(tname, v & 0x3FF), (x * 16, y * 16))
    if col:
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for y, row in enumerate(blocks):
            for x, v in enumerate(row):
                if (v >> 10) & 3:
                    d.rectangle([x * 16, y * 16, x * 16 + 15, y * 16 + 15], fill=(255, 0, 0, 90))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    if grid:
        Z = 2
        img = img.resize((w * 16 * Z, h * 16 * Z), Image.NEAREST)
        d = ImageDraw.Draw(img)
        for x in range(w + 1):
            d.line([(x * 32, 0), (x * 32, h * 32)], fill=(0, 0, 0) if x % 5 else (255, 255, 255), width=1)
        for y in range(h + 1):
            d.line([(0, y * 32), (w * 32, y * 32)], fill=(0, 0, 0) if y % 5 else (255, 255, 255), width=1)
        for x in range(0, w, 5):
            for y in range(0, h, 5):
                d.text((x * 32 + 2, y * 32 + 1), f"{x},{y}", fill=(255, 255, 0))
        for (mx, my, label, colour) in marks:
            d.rectangle([mx * 32 + 2, my * 32 + 2, mx * 32 + 29, my * 32 + 29], outline=colour, width=3)
            d.text((mx * 32 + 4, my * 32 + 10), label, fill=colour)
    return img


# ---------------------------------------------------------------------------------------------------------------------
# Map designs (D51). Each: tileset, size, ops, marks (warps/arrival/events to show on the preview).
# ---------------------------------------------------------------------------------------------------------------------
MAPS = {}

GRASS = ("id", 0, 0)              # Johto primaries: plain grass is metatile 0 in NorthWest/General/NorthEast
TREES_M = ("forest_edge_south", (0, 1, 22, 8))     # Mossui forest (green + maple + cherry), 2x2 trees


def forest(x, y, w, h, pat=TREES_M):
    """Forest rect; x, y, w, h even so trees line up between rects."""
    return ("tile", pat[0], pat[1], x, y, w, h)


def house_big(x, y):
    """Ecruteak house, 8x6 incl. its cobble pad; door at (x+2, y+4)."""
    return [("stamp", "house_big", x, y), ("put", ("house_door", 0, 0), x + 2, y + 4)]


def house_small(x, y):
    """Ecruteak small house, 5x5; door at (x+1, y+3)."""
    return [("stamp", "house_small", x, y), ("put", ("house_door", 0, 0), x + 1, y + 3)]


def paddy(x, y, w, h, stamp="paddy"):
    return ("nine", stamp, (0, 0, 3, 3), (1, 1, 1, 1), x, y, w, h)


# Mossui Town (D51): crossroads village. N -> Oni Mountain W slope, S -> Kitakami Road, W -> Apple Hills,
# E -> Reveler's Road. North: Yukito's house (W), Pokémon Center (E), paddies (NE). South: Community Center (W),
# Peachy's (E), paddies both sides. Lanterns mark the four street ends.
STONE = ("street", 1, 5)
MAPS["MossuiTown"] = {
    "tileset": "gTileset_KitakamiMossui", "w": 40, "h": 32,
    "ops": [
        ("fill", GRASS),
        forest(0, 0, 16, 4), forest(24, 0, 16, 4), forest(0, 28, 16, 4), forest(24, 28, 16, 4),
        forest(0, 4, 4, 10), forest(0, 18, 4, 10), forest(36, 4, 4, 10), forest(36, 18, 4, 10),
        ("rect", STONE, 18, 0, 4, 32), ("rect", STONE, 0, 14, 40, 4),
        *house_big(6, 8),                           # Yukito's house, door (8,12)
        ("stamp", "pokemon_center", 24, 9),         # door (27,12)
        paddy(31, 5, 5, 8),
        *house_big(8, 19),                          # Community Center, door (10,23)
        *house_small(23, 19),                       # Peachy's, door (24,22)
        paddy(4, 19, 4, 8), paddy(31, 19, 5, 8),
        forest(14, 4, 2, 2), forest(4, 4, 2, 2),
        ("stamp", "lantern", 16, 2), ("stamp", "lantern", 23, 2),
        ("stamp", "lantern", 16, 28), ("stamp", "lantern", 23, 28),
        ("stamp", "lantern", 2, 12), ("stamp", "lantern", 2, 18), ("stamp", "lantern", 37, 12), ("stamp", "lantern", 37, 18),
        ("stamp", "sign", 17, 25),
        ("stamp", "signboard", 22, 4),              # signboard 3, "at the base of Oni Mountain"
    ],
    "marks": [(8, 12, "D", (255, 0, 255)), (27, 12, "D", (255, 0, 255)), (10, 23, "D", (255, 0, 255)),
              (24, 22, "D", (255, 0, 255)), (17, 25, "S", (0, 255, 255)), (22, 5, "SB3", (0, 255, 255))],
}

# --- Fields tileset (Johto General primary + Route 38/39 farmland) -------------------------------------------------
# Dirt/sand path: primary metatiles, same ids in Johto General and NorthEast (Route 38/39 and Route 45 use them).
PATH = [[("id", m, 0) for m in row] for row in ((0xD0, 0xD1, 0xD2), (0xD8, 0xD9, 0xDA), (0xE0, 0xE1, 0xE2))]
PATH_C = ("id", 0xD9, 0)                                   # path centre
# inner corners, named after the corner of a grass hole they draw: BL = grass at the tile's top-right, etc.
PATH_IN_BL, PATH_IN_BR = ("id", 0xFF, 0), ("id", 0xFE, 0)
PATH_IN_TL, PATH_IN_TR = ("id", 0x107, 0), ("id", 0x106, 0)
TALL = ("route39_all", 36, 26)                             # tall grass (wild encounters)


def path(x, y, w, h):
    return ("box", PATH, x, y, w, h)


def pine(x, y, w, h):
    """Pine forest (Route 38/45; primary metatiles 1a/1b tops, 14/15 + 1c/1d rows, same in General and NorthEast):
    top row of tree tops, then alternating rows; w even, h odd."""
    ops = []
    for j in range(h):
        row = (0x1A, 0x1B) if j == 0 else ((0x14, 0x15) if j % 2 else (0x1C, 0x1D))
        for i in range(w):
            ops.append(("put", ("id", row[i % 2], 1), x + i, y + j))
    return ops


# Kitakami Road (D51): the southern entry. Long N-S dirt road from the bus plaza (south) up to Mossui (north),
# paddies west, paddies + tall grass east, a branch east to Mossfell Confluence. Pine woods on both sides.
MAPS["KitakamiRoad"] = {
    "tileset": "gTileset_KitakamiFields", "w": 28, "h": 48,
    "ops": [
        ("fill", GRASS),
        *pine(0, 0, 6, 45), *pine(22, 0, 6, 29), *pine(22, 35, 6, 9), *pine(0, 45, 28, 3),
        path(12, -1, 4, 41), path(7, 38, 14, 7), path(13, 30, 16, 4),
        ("rect", PATH_C, 13, 30, 2, 4), ("rect", PATH_C, 15, 31, 1, 2), ("rect", PATH_C, 13, 38, 2, 1),
        ("put", PATH_IN_BL, 15, 30), ("put", PATH_IN_TL, 15, 33),
        ("put", PATH_IN_BR, 12, 38), ("put", PATH_IN_BL, 15, 38),
        paddy(6, 3, 5, 7), paddy(6, 12, 5, 7), paddy(6, 21, 5, 7), paddy(6, 30, 5, 6),
        paddy(17, 2, 5, 8), paddy(17, 12, 5, 6),
        ("rect", TALL, 17, 20, 5, 8), ("rect", TALL, 17, 35, 4, 2),
        ("put", ("route39_all", 25, 17), 11, 36),
        ("col", 13, 40, 4, 2, 1),                   # under the parked bus picture (bus object at (14,41), D50)
    ],
    "marks": [(14, 41, "BUS", (255, 255, 0)), (14, 0, "N", (255, 255, 255)), (27, 31, "E", (255, 255, 255)), (13, 42, "drv", (0, 255, 255)), (18, 40, "pol", (0, 255, 255)),
              (14, 42, "arr", (255, 0, 255)), (11, 36, "S", (0, 255, 255))],
}

# --- Mountain tileset (Johto NorthEast primary + Route 45 / Ilex / hut) ----------------------------------------------
POND_M = [[("route45_all", x, y) for x in (26, 27, 31)] for y in (80, 81, 83)]   # pond box (1a5..269)
POND_M_C = ("route45_all", 27, 81)

# Oni Mountain, west slope (D51): the climb above Mossui. Rocky switchbacks, river down from the summit, cliffs
# (Route 45 rows 0-33). The river ends in a pond at the foot; pine woods close the foot except the path south to
# Mossui (x10-13 = Mossui x18-21). Dreaded Den = the cave mouth at (14,4); Ogerpon's hut in a clearing at the foot.
# N edge (sand x25-33) -> Oni summit. The E edge is cliff: the E slope is reached over the summit.
MAPS["OniMountain_WestSlope"] = {
    "tileset": "gTileset_KitakamiMountain", "w": 46, "h": 40,
    "ops": [
        ("fill", GRASS),
        ("stamp", "route45_all", 0, 0, (0, 0, 46, 34)),
        ("put", ("route45_all", 45, 5), 45, 6),               # close Route 45's east cave mouth
        *pine(0, 34, 46, 7),
        ("box", POND_M, 15, 34, 6, 4), ("rect", POND_M_C, 17, 34, 2, 1),
        path(9, 33, 6, 8), ("rect", PATH_C, 10, 33, 4, 1),
        ("rect", GRASS, 21, 34, 10, 6),
        ("stamp", "ogerpon_hut", 21, 35, (0, 1, 9, 3)),     # the mound without Ecruteak's tree rows
        ("col", 14, 4, 1, 1, 1), ("col", 28, 37, 1, 1, 1),  # Den and hut doors closed until built (D37)
    ],
    "marks": [(14, 4, "Den", (255, 0, 255)), (28, 37, "Hut", (255, 0, 255)), (29, 0, "N", (255, 255, 255)),
              (11, 39, "S", (255, 255, 255))],
}


def step_preview(outdir, names=None):
    os.makedirs(outdir, exist_ok=True)
    for name, m in MAPS.items():
        if names and name not in names:
            continue
        c = Canvas(m["tileset"], m["w"], m["h"])
        c.run(m["ops"])
        render(m["tileset"], c.b, marks=m.get("marks", ())).save(f"{outdir}/{name}.png")
        render(m["tileset"], c.b, col=True, marks=m.get("marks", ())).save(f"{outdir}/{name}_col.png")
        render(m["tileset"], c.b, grid=False).save(f"{outdir}/{name}_plain.png")
        print(f"preview: {name} {m['w']}x{m['h']} ({m['tileset']})")


BORDERS = {   # 2x2 border per tileset: what the player sees past an unconnected map edge
    "gTileset_KitakamiMossui": ((("forest_edge_south", 0, 1), ("forest_edge_south", 1, 1)),
                                (("forest_edge_south", 0, 2), ("forest_edge_south", 1, 2))),
    "gTileset_KitakamiFields": ((("id", 0x14, 1), ("id", 0x15, 1)), (("id", 0x1C, 1), ("id", 0x1D, 1))),
    "gTileset_KitakamiMountain": ((("id", 0x14, 1), ("id", 0x15, 1)), (("id", 0x1C, 1), ("id", 0x1D, 1))),
}


def layout_id(name):
    import re
    return "LAYOUT_" + re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).upper()


def step_write(names=None):
    """Layouts only (data/layouts/<Map>/map.bin + border.bin, data/layouts/layouts.json). Maps/events: 6d-3 wiring."""
    path = "data/layouts/layouts.json"
    doc = json.load(open(path, encoding="utf-8"))
    entries = {l.get("name"): l for l in doc["layouts"]}
    for name, m in MAPS.items():
        if names and name not in names:
            continue
        c = Canvas(m["tileset"], m["w"], m["h"])
        c.run(m["ops"])
        folder = f"data/layouts/{name}"
        os.makedirs(folder, exist_ok=True)
        with open(f"{folder}/map.bin", "wb") as f:
            f.write(b"".join(struct.pack("<H", v) for row in c.b for v in row))
        border = [c.block(b) for row in BORDERS[m["tileset"]] for b in row]
        with open(f"{folder}/border.bin", "wb") as f:
            f.write(struct.pack("<4H", *border))
        entry = {"id": layout_id(name), "name": f"{name}_Layout", "width": m["w"], "height": m["h"],
                 "border_width": 2, "border_height": 2, "primary_tileset": catalog()[m["tileset"]]["primary"],
                 "secondary_tileset": m["tileset"], "border_filepath": f"{folder}/border.bin",
                 "blockdata_filepath": f"{folder}/map.bin", "layout_version": "frlg"}
        if entry["name"] in entries:
            entries[entry["name"]].clear()
            entries[entry["name"]].update(entry)
        else:
            doc["layouts"].append(entry)
        print(f"write: {name} -> {folder} ({entry['id']})")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")


def step_stamps(outdir):
    os.makedirs(outdir, exist_ok=True)
    for tname, entry in catalog().items():
        for sname, st in entry["stamps"].items():
            render(tname, st["blocks"], col=True).save(f"{outdir}/{tname[9:]}_{sname}.png")
    print("stamps written")


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "preview":
        step_preview(sys.argv[2], set(sys.argv[3:]) or None)
    elif len(sys.argv) >= 2 and sys.argv[1] == "write":
        step_write(set(sys.argv[2:]) or None)
    elif len(sys.argv) >= 3 and sys.argv[1] == "stamps":
        step_stamps(sys.argv[2])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
