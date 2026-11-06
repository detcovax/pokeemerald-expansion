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


_mb_names = None


def behaviour_name(tname, mid):
    global _mb_names
    if _mb_names is None:
        import re
        _mb_names = re.findall(r"^\s+(MB_\w+)\s*,", open("include/constants/metatile_behaviors.h", encoding="utf-8").read(), re.M)
    b = attr(tname, mid) & 0x1FF
    return _mb_names[b] if b < len(_mb_names) else "MB_INVALID"


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
        self.points = {}

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

    def op_copy(self, sx, sy, x, y):
        """Copy one block of this map (used to cover a source map's ladders/holes with the floor beside them)."""
        self.b[y][x] = self.b[sy][sx]

    def op_swap(self, table, x=0, y=0, w=None, h=None):
        """Replace metatile ids (keeping collision/elevation) over a rect (default: whole map)."""
        w, h = w or self.w, h or self.h
        for j in range(y, min(self.h, y + h)):
            for i in range(x, min(self.w, x + w)):
                v = self.b[j][i]
                if (v & 0x3FF) in table:
                    self.b[j][i] = (v & ~0x3FF) | table[v & 0x3FF]

    # -- walkability (Gen 3 rules, roughly: collision, elevation, water, ledges) --------------------------------------
    def walkable(self, x, y):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return False
        v = self.b[y][x]
        if (v >> 10) & 3:
            return False
        return "WATER" not in behaviour_name(self.tname, v & 0x3FF)

    def elev(self, x, y):
        return self.b[y][x] >> 12

    def reach(self, starts):
        """Tiles reachable on foot from starts (elevation-aware; ledges one way)."""
        from collections import deque
        seen = set()
        q = deque()
        for (x, y) in starts:
            if self.walkable(x, y):
                z = self.elev(x, y)
                seen.add((x, y, z))
                q.append((x, y, z))
        while q:
            x, y, z = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not self.walkable(nx, ny):
                    continue
                b = behaviour_name(self.tname, self.b[ny][nx] & 0x3FF)
                if b.startswith("MB_JUMP_"):
                    if {"SOUTH": (0, 1), "NORTH": (0, -1), "EAST": (1, 0), "WEST": (-1, 0)}.get(b[8:]) != (dx, dy):
                        continue
                    nx, ny = nx + dx, ny + dy
                    if not self.walkable(nx, ny):
                        continue
                nz = self.elev(nx, ny)
                if z not in (0, 15) and nz not in (0, 15) and nz != z:
                    continue
                key = (nx, ny, z if nz in (0, 15) else nz)
                if key not in seen:
                    seen.add(key)
                    q.append(key)
        return {(x, y) for (x, y, _) in seen}

    def op_connect(self, exits, avoid_water=True):
        """Make every exit tile reachable from the first one: carve the cheapest sand line through rock to the
        area the first exit reaches (first pass of a hand-built map; D51)."""
        import heapq
        for ex in exits[1:]:
            main = self.reach([exits[0]])
            if tuple(ex) in main:
                continue
            dist, prev = {tuple(ex): 0}, {}
            heap = [(0, tuple(ex))]
            goal = None
            while heap:
                d, (x, y) = heapq.heappop(heap)
                if (x, y) in main and self.elev(x, y) in (0, 3):
                    goal = (x, y)
                    break
                if d > dist[(x, y)]:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (x + dx, y + dy)
                    if not (1 <= n[0] < self.w - 1 and 1 <= n[1] < self.h - 1) and n not in main:
                        continue
                    v = self.b[n[1]][n[0]]
                    bn = behaviour_name(self.tname, v & 0x3FF)
                    cost = 0 if (self.walkable(*n) and self.elev(*n) in (0, 3)) else (8 if "WATER" in bn else 1)
                    if d + cost < dist.get(n, 1 << 30):
                        dist[n] = d + cost
                        prev[n] = (x, y)
                        heapq.heappush(heap, (d + cost, n))
            node = goal
            while node is not None:
                x, y = node
                if not (self.walkable(x, y) and self.elev(x, y) in (0, 3)):
                    self.b[y][x] = self.block(PATH_C)
                node = prev.get(node)

    LAND = {0x0, 0x1, 0x4, 0x8, 0x9, 0x0D, 0x2B, 0xD1, 0xD8, 0xD9, 0xE1, 0xFE, 0xFF, 0x106, 0x107} | set(range(0x284, 0x29F))

    def op_flatten(self):
        """Route 45 ground/bridges at one elevation (3), so crops and drawn paths join; rock tops and water keep
        theirs (Mountain maps only: these ids are the NorthEast primary's and the Mountain secondary's)."""
        for row in self.b:
            for i, v in enumerate(row):
                if not (v >> 10) & 3 and (v & 0x3FF) in self.LAND and (v >> 12) != 15:
                    row[i] = (v & 0x0FFF) | (3 << 12)

    def op_autodoor(self, name, start, near, blk):
        """Put a cave mouth on the cliff face nearest `near` that has ground below it reachable from `start`."""
        reach = self.reach([start])
        best = None
        for y in range(1, self.h - 1):
            for x in range(1, self.w - 1):
                if (self.b[y][x] >> 10) & 3 and (self.b[y][x] & 0x3FF) in (0x79, 0x7C) and (x, y + 1) in reach:
                    d = abs(x - near[0]) + abs(y - near[1])
                    if best is None or d < best[0]:
                        best = (d, x, y)
        _, x, y = best
        self.b[y][x] = self.block(blk)
        self.points[name] = (x, y)

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
        # D52: maps on other tilesets are reached by warps, not connections (the GBA draws a connected map with
        # this map's tiles). North: torii gate up Oni Mountain (walk north on its inner top row); south: street edge.
        ("stamp", "gate", 18, 0), ("put", ("gate_warp_north_l", 0, 0), 19, 1), ("put", ("gate_warp_north_r", 0, 0), 20, 1),
        ("rect", STONE, 19, 3, 2, 1),               # Ecruteak's gate sill is a south arrow warp: plain stone here

        ("rect", ("street_warp_south", 0, 0), 18, 31, 4, 1),
        ("rect", ("street_warp_west", 0, 0), 0, 14, 1, 4),     # west: Apple Hills (Fields)
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
        ("rect", ("path_warp_north", 0, 0), 13, 0, 2, 1),   # D52: edge warp north to Mossui
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
        ("col", 14, 4, 1, 1, 1), ("col", 28, 37, 1, 1, 0),  # Den closed until built (D37); hut door walk-in
        ("rect", ("path_warp_south", 0, 0), 10, 39, 4, 1),  # D52: edge warp south to Mossui's torii gate
        ("flatten",),
    ],
    "marks": [(14, 4, "Den", (255, 0, 255)), (28, 37, "Hut", (255, 0, 255)), (29, 0, "N", (255, 255, 255)),
              (11, 39, "S", (255, 255, 255))],
}


# =====================================================================================================================
# Map headers and events (6d-3c). `events` writes data/maps/<Map>/map.json + scripts.inc for every Kitakami map and
# data/scripts/trey_kitakami_maps.inc. Harmless events only (signs, nurse, clerk, bus); story comes later.
# =====================================================================================================================
def map_id(name):
    return "MAP_" + layout_id(name)[len("LAYOUT_"):]


# name: (group, mapsec, music, map type)
HEADERS = {
    "MossuiTown": ("Outdoor", "MAPSEC_MOSSUI_TOWN", "MUS_HG_AZALEA", "MAP_TYPE_TOWN"),
    "KitakamiRoad": ("Outdoor", "MAPSEC_KITAKAMI_ROAD", "MUS_HG_ROUTE30", "MAP_TYPE_ROUTE"),
    "OniMountain_WestSlope": ("Outdoor", "MAPSEC_ONI_MOUNTAIN", "MUS_DP_MT_CORONET", "MAP_TYPE_ROUTE"),
    "RevelersRoad": ("Outdoor", "MAPSEC_REVELERS_ROAD", "MUS_HG_ECRUTEAK", "MAP_TYPE_ROUTE"),
    "LoyaltyPlaza": ("Outdoor", "MAPSEC_LOYALTY_PLAZA", "MUS_HG_ECRUTEAK", "MAP_TYPE_TOWN"),
    "KitakamiHall": ("Outdoor", "MAPSEC_KITAKAMI_HALL", "MUS_HG_ECRUTEAK", "MAP_TYPE_TOWN"),
    "AppleHills": ("Outdoor", "MAPSEC_APPLE_HILLS", "MUS_DPP_ROUTE205", "MAP_TYPE_ROUTE"),
    "WistfulFields": ("Outdoor", "MAPSEC_WISTFUL_FIELDS", "MUS_DPP_ROUTE205", "MAP_TYPE_ROUTE"),
    "MossfellConfluence": ("Outdoor", "MAPSEC_MOSSFELL_CONFLUENCE", "MUS_DPP_ROUTE205", "MAP_TYPE_ROUTE"),
    "OniMountain_Summit": ("Outdoor", "MAPSEC_ONI_MOUNTAIN", "MUS_DP_MT_CORONET", "MAP_TYPE_ROUTE"),
    "OniMountain_EastSlope": ("Outdoor", "MAPSEC_ONI_MOUNTAIN", "MUS_DP_MT_CORONET", "MAP_TYPE_ROUTE"),
    "InfernalPass": ("Outdoor", "MAPSEC_INFERNAL_PASS", "MUS_DP_STARK_MOUNTAIN", "MAP_TYPE_ROUTE"),
    "ParadiseBarrens": ("Outdoor", "MAPSEC_PARADISE_BARRENS", "MUS_HG_ROUTE47", "MAP_TYPE_ROUTE"),
    "DreamingPond": ("Outdoor", "MAPSEC_DREAMING_POND", "MUS_DPP_LAKE", "MAP_TYPE_ROUTE"),
    "TimelessWoods": ("Outdoor", "MAPSEC_TIMELESS_WOODS", "MUS_DPP_ETERNA_FOREST", "MAP_TYPE_ROUTE"),
    "TimelessWoods_Deep": ("Outdoor", "MAPSEC_TIMELESS_WOODS", "MUS_DPP_ETERNA_FOREST", "MAP_TYPE_ROUTE"),
    "FellhornGorge": ("Outdoor", "MAPSEC_FELLHORN_GORGE", "MUS_HG_ROUTE47", "MAP_TYPE_ROUTE"),
    "OnisMaw": ("Dungeon", "MAPSEC_ONIS_MAW", "MUS_HG_UNION_CAVE", "MAP_TYPE_UNDERGROUND"),
    "CrystalPool": ("Dungeon", "MAPSEC_CRYSTAL_POOL", "MUS_DP_LAKE_CAVERNS", "MAP_TYPE_UNDERGROUND"),
    "ChillingWaterhead": ("Dungeon", "MAPSEC_CHILLING_WATERHEAD", "MUS_HG_UNION_CAVE", "MAP_TYPE_UNDERGROUND"),
}

# Interiors reuse Johto layouts (no new layout data): name -> (layout, exit tile, mapsec, music)
INTERIORS = {
    "MossuiTown_PokemonCenter": ("LAYOUT_ECRUTEAK_CITY_POKEMON_CENTER", (7, 8), "MAPSEC_MOSSUI_TOWN", "MUS_HG_POKE_CENTER"),
    "MossuiTown_YukitosHouse": ("LAYOUT_ECRUTEAK_CITY_HOUSE1", (4, 8), "MAPSEC_MOSSUI_TOWN", "MUS_HG_AZALEA"),
    "MossuiTown_CommunityCenter": ("LAYOUT_ECRUTEAK_CITY_SAGE_OFFICE1", (13, 8), "MAPSEC_MOSSUI_TOWN", "MUS_HG_AZALEA"),
    "MossuiTown_Peachys": ("LAYOUT_ECRUTEAK_CITY_MART", (4, 7), "MAPSEC_MOSSUI_TOWN", "MUS_HG_POKE_MART"),
    "KitakamiHall_MaskHall": ("LAYOUT_ECRUTEAK_CITY_THEATER", (10, 17), "MAPSEC_KITAKAMI_HALL", "MUS_HG_ECRUTEAK"),
    "AppleHills_FarmHouse": ("LAYOUT_ROUTE39_FARM_HOUSE", (4, 8), "MAPSEC_APPLE_HILLS", "MUS_DPP_ROUTE205"),
    "OniMountain_OgerponsHut": ("LAYOUT_ECRUTEAK_CITY_HOUSE2", (4, 8), "MAPSEC_ONI_MOUNTAIN", "MUS_DP_MT_CORONET"),
}

# Same-tileset edge connections: (map, direction, other map, offset); each pair is listed from both sides.
CONNECTIONS = [
    ("MossuiTown", "right", "RevelersRoad", 6), ("RevelersRoad", "left", "MossuiTown", -6),
    ("RevelersRoad", "right", "LoyaltyPlaza", -2), ("LoyaltyPlaza", "left", "RevelersRoad", 2),
    ("LoyaltyPlaza", "up", "KitakamiHall", -2), ("KitakamiHall", "down", "LoyaltyPlaza", 2),
    ("KitakamiRoad", "right", "MossfellConfluence", 18), ("MossfellConfluence", "left", "KitakamiRoad", -18),
    ("MossfellConfluence", "up", "WistfulFields", 20), ("WistfulFields", "down", "MossfellConfluence", -20),
    ("OniMountain_WestSlope", "up", "OniMountain_Summit", 0), ("OniMountain_Summit", "down", "OniMountain_WestSlope", 0),
    ("OniMountain_EastSlope", "up", "OniMountain_Summit", -46), ("OniMountain_Summit", "down", "OniMountain_EastSlope", 46),
    ("OniMountain_WestSlope", "right", "OniMountain_EastSlope", 0), ("OniMountain_EastSlope", "left", "OniMountain_WestSlope", 0),
    ("OniMountain_Summit", "up", "InfernalPass", 36), ("InfernalPass", "down", "OniMountain_Summit", -36),
    ("InfernalPass", "down", "DreamingPond", 40), ("DreamingPond", "up", "InfernalPass", -40),
    ("ParadiseBarrens", "right", "InfernalPass", 16), ("InfernalPass", "left", "ParadiseBarrens", -16),
    ("DreamingPond", "right", "TimelessWoods", 0), ("TimelessWoods", "left", "DreamingPond", 0),
    ("TimelessWoods", "up", "TimelessWoods_Deep", 0), ("TimelessWoods_Deep", "down", "TimelessWoods", 0),
    ("TimelessWoods", "down", "FellhornGorge", 0), ("FellhornGorge", "up", "TimelessWoods", 0),
]

# Warp links: (map A, tiles A, map B, tiles B). Tile i of A leads to tile min(i, len B - 1) of B and back.
# A tile may be a point name from the map's ops (autodoor).
WARPS = [
    ("MossuiTown", [(19, 1), (20, 1)], "OniMountain_WestSlope", [(10, 39), (11, 39), (12, 39), (13, 39)]),
    ("MossuiTown", [(18, 31), (19, 31), (20, 31), (21, 31)], "KitakamiRoad", [(13, 0), (14, 0)]),
    ("MossuiTown", [(0, 14), (0, 15), (0, 16), (0, 17)], "AppleHills", [(35, 15), (35, 16)]),
    ("MossuiTown", [(27, 12)], "MossuiTown_PokemonCenter", [(7, 8)]),
    ("MossuiTown", [(8, 12)], "MossuiTown_YukitosHouse", [(4, 8)]),
    ("MossuiTown", [(10, 23)], "MossuiTown_CommunityCenter", [(13, 8)]),
    ("MossuiTown", [(24, 22)], "MossuiTown_Peachys", [(4, 7)]),
    ("LoyaltyPlaza", [(27, 10), (27, 11), (27, 12), (27, 13)], "WistfulFields", [(0, 17), (0, 18)]),
    ("KitakamiHall", [(0, 18), (0, 19), (0, 20), (0, 21)], "OniMountain_EastSlope", [(29, 31), (29, 32)]),
    ("KitakamiHall", [(15, 11)], "KitakamiHall_MaskHall", [(10, 17)]),
    ("AppleHills", [(17, 0), (18, 0)], "ChillingWaterhead", [(9, 20)]),
    ("AppleHills", [(9, 21)], "AppleHills_FarmHouse", [(4, 8)]),
    ("WistfulFields", [(21, 0), (22, 0)], "FellhornGorge", [(16, 39), (17, 39), (18, 39), (19, 39)]),
    ("OniMountain_EastSlope", [(23, 7)], "OnisMaw", [(26, 29)]),
    ("OniMountain_Summit", ["crystal_pool"], "CrystalPool", [(49, 32)]),   # its other mats: Ice Path's far part
    ("ParadiseBarrens", [(39, 23)], "ChillingWaterhead", [(10, 32)]),
    ("OniMountain_WestSlope", [(28, 37)], "OniMountain_OgerponsHut", [(4, 8)]),
]

NOT_BUILT = "TreyKitakami_EventScript_NotBuiltYet"
# Signs: map -> [(x, y, text or script)]; text lines separated by "\n" (first line break \n, then \l).
SIGNS = {
    "MossuiTown": [(17, 25, "MOSSUI TOWN\nA quiet village at the foot of\nONI MOUNTAIN."),
                   (22, 5, "@signboard"), (23, 5, "@signboard")],
    "KitakamiRoad": [(11, 36, "KITAKAMI ROAD\nNorth: MOSSUI TOWN")],
    "OniMountain_WestSlope": [(31, 4, "ONI MOUNTAIN\nSouth: MOSSUI TOWN"), (14, 4, NOT_BUILT)],
    "LoyaltyPlaza": [(18, 16, "@signboard"), (19, 16, "@signboard")],
    "KitakamiHall": [(11, 16, "@signboard"), (12, 16, "@signboard")],
}
SIGNBOARD_TEXT = "It's an old signboard. It tells a\ntale of the ogre of ONI MOUNTAIN\nand the LOYAL THREE."

# Objects: map -> [(local id suffix or None, graphics, x, y, movement, script)]
OBJECTS = {
    "KitakamiRoad": [("BUS", "OBJ_EVENT_GFX_TREY_BUS", 14, 41, "MOVEMENT_TYPE_FACE_LEFT", "TreyTransit_EventScript_Bus"),
                     ("BUS_DRIVER", "OBJ_EVENT_GFX_OFFICER_HNS", 13, 42, "MOVEMENT_TYPE_FACE_DOWN", "@busdriver"),
                     (None, "OBJ_EVENT_GFX_TREY_BUS_STOP", 18, 40, "MOVEMENT_TYPE_NONE", "TreyTransit_EventScript_BusStopSign")],
    "MossuiTown_PokemonCenter": [("NURSE", "OBJ_EVENT_GFX_NURSE_HNS", 7, 2, "MOVEMENT_TYPE_FACE_DOWN", "@nurse")],
    "MossuiTown_Peachys": [("CLERK", "OBJ_EVENT_GFX_MART_EMPLOYEE_HNS", 2, 3, "MOVEMENT_TYPE_FACE_RIGHT", "@clerk")],
}

PEACHYS_STOCK = ["ITEM_POKE_BALL", "ITEM_GREAT_BALL", "ITEM_POTION", "ITEM_SUPER_POTION", "ITEM_ANTIDOTE",
                 "ITEM_PARALYZE_HEAL", "ITEM_AWAKENING", "ITEM_BURN_HEAL", "ITEM_ICE_HEAL", "ITEM_ESCAPE_ROPE", "ITEM_REPEL"]


def all_maps():
    return list(HEADERS) + list(INTERIORS)


def canvases():
    out = {}
    for name, m in MAPS.items():
        c = Canvas(m["tileset"], m["w"], m["h"])
        c.run(m["ops"])
        out[name] = c
    return out


def warp_tables(cv):
    """map -> [[x, y, dest map, dest index]] built from WARPS."""
    tables = {n: [] for n in all_maps()}
    index = {}

    def pt(m, t):
        return cv[m].points[t] if isinstance(t, str) else tuple(t)
    for k, (a, ta, b, tb) in enumerate(WARPS):
        for side, (m, ts) in enumerate(((a, ta), (b, tb))):
            for i, t in enumerate(ts):
                index[(k, side, i)] = len(tables[m])
                tables[m].append([*pt(m, t), None, None])
    for k, (a, ta, b, tb) in enumerate(WARPS):
        for i in range(len(ta)):
            tables[a][index[(k, 0, i)]][2:] = [b, index[(k, 1, min(i, len(tb) - 1))]]
        for i in range(len(tb)):
            tables[b][index[(k, 1, i)]][2:] = [a, index[(k, 0, min(i, len(ta) - 1))]]
    return tables


def text_lines(t):
    lines = t.split("\n")
    out = []
    for i, line in enumerate(lines):
        end = "$" if i == len(lines) - 1 else ("\\n" if i == 0 else "\\l")
        out.append(f'\t.string "{line}{end}"')
    return "\n".join(out)


def step_events(names=None):
    cv = canvases()
    warps = warp_tables(cv)
    for name in all_maps():
        if names and name not in names:
            continue
        inside = name in INTERIORS
        if inside:
            layout, _, mapsec, music = INTERIORS[name]
            mtype = "MAP_TYPE_INDOOR"
        else:
            _, mapsec, music, mtype = HEADERS[name]
            layout = layout_id(name)
        script, texts, objs, bgs = [f"@ TREY (6d-3, D51/D52): {name}, generated by tools/trey/kitakami_maps.py (events)."
                                    " Story comes later.\n", f"{name}_MapScripts::"], [], [], []
        if name == "MossuiTown_PokemonCenter":
            script += [f"\tmap_script MAP_SCRIPT_ON_TRANSITION, {name}_OnTransition", "\t.byte 0", "",
                       f"{name}_OnTransition:", "\tsetrespawn HEAL_LOCATION_MOSSUI_TOWN", "\tend"]
        else:
            script.append("\t.byte 0")
        for n, (x, y, t) in enumerate(SIGNS.get(name, [])):
            if t.startswith("Trey"):
                s = t
            else:
                s = f"{name}_EventScript_Sign{n}"
                body = SIGNBOARD_TEXT if t == "@signboard" else t
                script += ["", f"{s}::", f"\tmsgbox {name}_Text_Sign{n}, MSGBOX_SIGN", "\tend"]
                texts += ["", f"{name}_Text_Sign{n}:", text_lines(body)]
            bgs.append({"type": "sign", "x": x, "y": y, "elevation": 0,
                        "player_facing_dir": "BG_EVENT_PLAYER_FACING_ANY", "script": s})
        for (lid, gfx, x, y, mov, s) in OBJECTS.get(name, []):
            local = f"LOCALID_{map_id(name)[4:]}_{lid}" if lid else None
            if s == "@busdriver":
                s = f"{name}_EventScript_BusDriver"
                script += ["", f"{s}::", "\tlock", "\tfaceplayer", "\tsetvar VAR_0x8004, TRANSIT_BUS",
                           "\tsetvar VAR_0x8005, TRANSIT_STOP_MOSSUI", "\tsetvar VAR_0x8007, 0",
                           f"\tsetvar VAR_0x8009, LOCALID_{map_id(name)[4:]}_BUS", f"\tsetvar VAR_0x800A, {local}",
                           "\tgoto TreyTransit_EventScript_BusDriver"]
            elif s == "@nurse":
                s = f"{name}_EventScript_Nurse"
                script += ["", f"{s}::", f"\tsetvar VAR_0x800B, {local}", "\tcall Common_EventScript_PkmnCenterNurse",
                           "\twaitmessage", "\twaitbuttonpress", "\trelease", "\tend"]
            elif s == "@clerk":
                s = f"{name}_EventScript_Clerk"
                script += ["", f"{s}::", "\tlock", "\tfaceplayer", "\tmessage gText_HowMayIServeYou", "\twaitmessage",
                           f"\tpokemart {name}_Pokemart", "\tmsgbox gText_PleaseComeAgain", "\trelease", "\tend",
                           "", "\t.align 2", f"{name}_Pokemart:"] + [f"\t.2byte {i}" for i in PEACHYS_STOCK] + ["\tpokemartlistend"]
            o = {"graphics_id": gfx, "x": x, "y": y, "elevation": 3, "movement_type": mov, "movement_range_x": 0,
                 "movement_range_y": 0, "trainer_type": "TRAINER_TYPE_NONE", "trainer_sight_or_berry_tree_id": "0",
                 "script": s, "flag": "0"}
            if local:
                o = {"local_id": local, **o}
            objs.append(o)
        doc = {"id": map_id(name), "name": name, "layout": layout, "music": music, "region_map_section": mapsec,
               "requires_flash": False, "weather": "WEATHER_NONE", "map_type": mtype,
               "allow_cycling": not inside, "allow_escaping": mtype == "MAP_TYPE_UNDERGROUND",
               "allow_running": True, "show_map_name": not inside, "battle_scene": "MAP_BATTLE_SCENE_NORMAL",
               "connections": [{"map": map_id(o), "offset": off, "direction": d}
                               for (m, d, o, off) in CONNECTIONS if m == name],
               "object_events": objs,
               "warp_events": [{"x": x, "y": y, "elevation": 0, "dest_map": map_id(d), "dest_warp_id": str(i)}
                               for (x, y, d, i) in warps[name]],
               "coord_events": [], "bg_events": bgs, "region": "REGION_KITAKAMI", "floor_number": 0}
        os.makedirs(f"data/maps/{name}", exist_ok=True)
        with open(f"data/maps/{name}/map.json", "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
            f.write("\n")
        with open(f"data/maps/{name}/scripts.inc", "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(script + texts) + "\n")
    with open("data/scripts/trey_kitakami_maps.inc", "w", encoding="utf-8", newline="\n") as f:
        f.write("@ TREY (6d-3, D51): Kitakami maps, generated by tools/trey/kitakami_maps.py (events).\n\n"
                "@ D37: doors whose interior isn't built yet.\n"
                f"{NOT_BUILT}::\n\tmsgbox TreyKitakami_Text_NotBuiltYet, MSGBOX_SIGN\n\tend\n\n"
                "TreyKitakami_Text_NotBuiltYet:\n\t.string \"(Not built yet.)$\"\n\n"
                + "".join(f'\t.include "data/maps/{n}/scripts.inc"\n' for n in all_maps()))
    print("events: map.json + scripts.inc for", len(all_maps()), "maps")
    print("groups:", {g: [n for n in HEADERS if HEADERS[n][0] == g] for g in ("Outdoor", "Dungeon")},
          "Indoor:", list(INTERIORS))


VIEW_ONLY = {("OniMountain_WestSlope", "OniMountain_EastSlope"), ("OniMountain_EastSlope", "OniMountain_WestSlope")}
SPLIT_OK = {("ChillingWaterhead", (10, 32))}   # Ice Path B1F is two grottos: one from Apple Hills, one from the Barrens


def step_check():
    """Every warp tile and connection gap of a map reachable from its first warp/gap (on foot)."""
    cv = canvases()
    warps = warp_tables(cv)
    bad = 0
    for name, c in cv.items():
        pts = [(x, y) for (x, y, _, _) in warps[name]]
        edges = []
        for (m, d, o, off) in CONNECTIONS:
            if m != name or (m, o) in VIEW_ONLY:
                continue
            edge = {"up": [(x, 0) for x in range(c.w)], "down": [(x, c.h - 1) for x in range(c.w)],
                    "left": [(0, y) for y in range(c.h)], "right": [(c.w - 1, y) for y in range(c.h)]}[d]
            edges.append((d, o, [p for p in edge if c.walkable(*p)]))
        if not pts and edges and edges[0][2]:
            pts.append(edges[0][2][0])
        if not pts:
            continue
        # doors: the tile in front (south) of a door is what you walk on
        stand = [(x, y + 1) if (c.b[y][x] >> 10) & 3 else (x, y) for (x, y) in pts]
        reach = c.reach([stand[0]])
        for p, s in zip(pts, stand):
            if s not in reach and (name, p) not in SPLIT_OK:
                print(f"check: {name}: warp {p} not reachable from {pts[0]}")
                bad += 1
        for d, o, open_ in edges:
            if not any(p in reach for p in open_):
                print(f"check: {name}: no reachable open tile on its {d} edge ({o})")
                bad += 1
    # seams: some tile pair across each connection is walkable on both sides at the same elevation
    for (m, d, o, off) in CONNECTIONS:
        if (m, o) in VIEW_ONLY:
            continue
        a, b = cv[m], cv[o]
        pairs = []
        if d in ("up", "down"):
            ya, yb = (0, b.h - 1) if d == "up" else (a.h - 1, 0)
            pairs = [((x, ya), (x - off, yb)) for x in range(a.w) if 0 <= x - off < b.w]
        else:
            xa, xb = (0, b.w - 1) if d == "left" else (a.w - 1, 0)
            pairs = [((xa, y), (xb, y - off)) for y in range(a.h) if 0 <= y - off < b.h]
        ok = [p for p, q in pairs if a.walkable(*p) and b.walkable(*q) and a.elev(*p) == b.elev(*q)]
        if not ok:
            print(f"check: seam {m} -{d}-> {o} (offset {off}): no matching open tiles")
            bad += 1
    print(f"check: {bad} problem(s)")


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


# =====================================================================================================================
# 6d-3c: the rest of Kitakami (D51/D52). Positions of the Mountain cluster (tiles, for the connections):
#   Paradise Barrens X-8..35 Y-40..-1 | Infernal Pass X36..95 Y-24..-1 | Timeless Woods 2 X112..147 Y-36..-1
#   Oni summit X0..75 Y0..27 | Dreaming Pond X76..111 Y0..31 | Timeless Woods 1 X112..151 Y0..39
#   W slope X0..45 Y28..67 | E slope X46..75 Y28..67 | Fellhorn Gorge X112..147 Y40..79
# Seams between connected Mountain maps are rock bands (2 tiles each side) with a sand gap at the same place on
# both sides; maps on other tilesets are joined by edge warps (D52).
# =====================================================================================================================
def street_warps(direction, x, y, w, h):
    return ("rect", (f"street_warp_{direction}", 0, 0), x, y, w, h)


def path_warps(direction, x, y, w, h):
    return ("rect", (f"path_warp_{direction}", 0, 0), x, y, w, h)


# --- Mossui tileset --------------------------------------------------------------------------------------------------
# Reveler's Road: the festival road east of Mossui. Stalls on the north side, lantern fence on the south.
MAPS["RevelersRoad"] = {
    "tileset": "gTileset_KitakamiMossui", "w": 40, "h": 20,
    "ops": [
        ("fill", GRASS), forest(0, 0, 40, 4), forest(0, 16, 40, 4),
        ("rect", STONE, 0, 8, 40, 4),
        ("stamp", "stall_red", 3, 5), ("stamp", "stall_blue", 9, 5), ("stamp", "stall_orange", 15, 5),
        ("stamp", "stall_red", 23, 5), ("stamp", "stall_blue", 29, 5), ("stamp", "stall_orange", 35, 5),
        ("stamp", "fence_lanterns", 2, 13), ("stamp", "fence_lanterns", 21, 13),
        ("stamp", "lantern", 20, 12), ("stamp", "lantern", 1, 4),
    ],
    "marks": [],
}

# Loyalty Plaza: stone square with the Loyal Three monument (3 pedestals) and signboard 1. N -> Kitakami Hall,
# W -> Reveler's Road, E -> Wistful Fields (edge warp).
MAPS["LoyaltyPlaza"] = {
    "tileset": "gTileset_KitakamiMossui", "w": 28, "h": 24,
    "ops": [
        ("fill", GRASS),
        forest(0, 0, 12, 4), forest(16, 0, 12, 4), forest(0, 20, 28, 4),
        forest(0, 4, 4, 6), forest(0, 14, 4, 6), forest(24, 4, 4, 6), forest(24, 14, 4, 6),
        ("rect", STONE, 6, 5, 16, 13), ("rect", STONE, 12, 0, 4, 5), ("rect", STONE, 0, 10, 28, 4),
        ("stamp", "pedestal", 10, 7), ("stamp", "pedestal", 13, 6), ("stamp", "pedestal", 16, 7),
        ("stamp", "signboard", 18, 15),
        ("stamp", "lantern", 6, 5), ("stamp", "lantern", 21, 5), ("stamp", "lantern", 6, 16), ("stamp", "lantern", 21, 16),
        street_warps("east", 27, 10, 1, 4),
    ],
    "marks": [(10, 7, "P", (0, 255, 255)), (13, 6, "P", (0, 255, 255)), (16, 7, "P", (0, 255, 255)),
              (18, 16, "SB1", (0, 255, 255))],
}

# Kitakami Hall: the red hall (Mask Hall door at (15,11)), festival stalls, signboard 2. S -> Loyalty Plaza,
# W -> Oni Mountain E slope (edge warp).
MAPS["KitakamiHall"] = {
    "tileset": "gTileset_KitakamiMossui", "w": 32, "h": 28,
    "ops": [
        ("fill", GRASS), forest(0, 0, 32, 2),
        forest(0, 2, 10, 16), forest(0, 22, 14, 6), forest(20, 2, 12, 12), forest(18, 22, 14, 6), forest(28, 14, 4, 8),
        ("stamp", "kitakami_hall", 11, 2),
        ("rect", STONE, 14, 14, 4, 14), ("rect", STONE, 0, 18, 14, 4),
        ("stamp", "stall_red", 20, 15), ("stamp", "stall_blue", 24, 15), ("stamp", "stall_orange", 20, 19),
        ("stamp", "lantern", 13, 14), ("stamp", "lantern", 18, 14),
        ("stamp", "signboard", 11, 15),
        street_warps("west", 0, 18, 1, 4),
    ],
    "marks": [(15, 11, "D", (255, 0, 255)), (11, 16, "SB2", (0, 255, 255))],
}

# --- Fields tileset --------------------------------------------------------------------------------------------------
TALL_F = TALL


def apples(xs, ys):
    return [("stamp", "apple_tree", x, y) for x in xs for y in ys]


def flowers(xs, ys):
    return [("stamp", "flowers", x, y) for x in xs for y in ys]


# Apple Hills: the orchard west of Mossui. Farmhouse (door (9,21)) and barn; path north into Chilling Waterhead
# (edge warp), path east to Mossui (edge warp).
MAPS["AppleHills"] = {
    "tileset": "gTileset_KitakamiFields", "w": 36, "h": 32,
    "ops": [
        ("fill", GRASS),
        *pine(0, 0, 16, 5), *pine(20, 0, 16, 5), *pine(0, 5, 4, 27), *pine(4, 29, 32, 3),
        *pine(32, 5, 4, 9), *pine(32, 18, 4, 11),
        path(16, 14, 21, 4), path(16, -1, 4, 16),
        ("rect", PATH_C, 17, 14, 2, 3), ("rect", ("id", 0xD8, 0), 16, 14, 1, 3), ("put", PATH_IN_BL, 19, 14),
        *apples((6, 10, 22, 26), (5, 9)), *apples((6, 10), (24,)),
        ("stamp", "farmhouse", 8, 19), ("stamp", "barn", 23, 21), ("col", 25, 24, 2, 1, 1),
        ("rect", TALL_F, 13, 20, 8, 7), *flowers((22, 28), (26,)),
        path_warps("north", 17, 0, 2, 1), path_warps("east", 35, 15, 1, 2),
    ],
    "marks": [(9, 21, "D", (255, 0, 255))],
}

# Wistful Fields: flower fields with tall grass and a pond. W -> Loyalty Plaza (edge warp), N -> Fellhorn Gorge
# (edge warp), S -> Mossfell Confluence (connection, path x26-29).
MAPS["WistfulFields"] = {
    "tileset": "gTileset_KitakamiFields", "w": 44, "h": 36,
    "ops": [
        ("fill", GRASS),
        *pine(0, 0, 20, 5), *pine(24, 0, 20, 5), *pine(0, 31, 26, 5), *pine(30, 31, 14, 5),
        *pine(0, 5, 4, 11), *pine(0, 20, 4, 11), *pine(40, 5, 4, 26),
        path(20, -1, 4, 4), path(-1, 16, 4, 4), path(26, 31, 4, 6),
        *flowers(range(6, 38, 6), range(6, 30, 5)),
        ("rect", TALL_F, 8, 21, 10, 6), ("rect", TALL_F, 28, 7, 10, 8),
        ("stamp", "pond_small", 18, 9),
        path_warps("north", 21, 0, 2, 1), path_warps("west", 0, 17, 1, 2),
    ],
    "marks": [],
}

# Mossfell Confluence: the lake where the rivers meet (Surf, fishing). W -> Kitakami Road (connection, rows 12-15),
# N -> Wistful Fields (connection, path x46-49).
MAPS["MossfellConfluence"] = {
    "tileset": "gTileset_KitakamiFields", "w": 64, "h": 28,
    "ops": [
        ("fill", GRASS),
        *pine(0, 0, 46, 5), *pine(50, 0, 14, 5), *pine(0, 23, 64, 5),
        *pine(0, 5, 4, 7), *pine(0, 16, 4, 7), *pine(60, 5, 4, 18),
        ("nine", "pond_small", (0, 0, 3, 4), (1, 1, 1, 1), 14, 6, 30, 14),
        path(-1, 12, 14, 4), path(46, -1, 4, 8),
        ("rect", TALL_F, 48, 9, 10, 12), ("rect", TALL_F, 5, 17, 8, 5),
    ],
    "marks": [],
}

# --- Mountain tileset ------------------------------------------------------------------------------------------------
ROCK = ("id", 0x71, 1)          # Route 45 rock top, made solid for the seam bands
SAND = PATH_C
TALL_M = ("id", 0x0D, 0)
DOOR_M = ("route45_all", 39, 53)     # cave mouth (non-animated door, walkable)
DENSE = ("dense_forest", (0, 0, 3, 2))


def r45(x, y, sx, sy, w, h):
    return ("stamp", "route45_all", x, y, (sx, sy, w, h))


def band(x, y, w, h, gaps=()):
    """Solid rock band with sand gaps [(gx, gy, gw, gh)]."""
    return [("rect", ROCK, x, y, w, h)] + [("rect", SAND, *g) for g in gaps]


def dense(x, y, w, h):
    return ("tile", DENSE[0], DENSE[1], x, y, w, h)


# Oni Mountain summit: the "head" ridge above both slopes. S -> W slope (gap x25-33) and E slope (gap x56-59),
# N -> Infernal Pass (gap x40-43). Crystal Pool cave mouth on the ridge.
MAPS["OniMountain_Summit"] = {
    "tileset": "gTileset_KitakamiMountain", "w": 76, "h": 28,
    "ops": [
        ("fill", GRASS), r45(0, 0, 0, 56, 46, 28), r45(46, 0, 16, 14, 30, 28),
        *band(0, 26, 76, 2, [(25, 26, 9, 2), (56, 26, 4, 2)]),
        *band(0, 0, 76, 2, [(40, 0, 4, 2)]),
        *band(0, 0, 2, 28), *band(74, 0, 2, 28),
        ("flatten",), ("connect", [(29, 27), (57, 27), (41, 0)]),
        ("autodoor", "crystal_pool", (29, 27), (38, 14), DOOR_M),
    ],
    "marks": [],
}

# Oni Mountain, east slope: above Kitakami Hall. N -> summit (gap x10-13), W -> W slope (rock, no crossing),
# E -> Kitakami Hall (edge warp rows 31-32). Oni's Maw cave mouth at (23,7).
MAPS["OniMountain_EastSlope"] = {
    "tileset": "gTileset_KitakamiMountain", "w": 30, "h": 40,
    "ops": [
        ("fill", GRASS), r45(0, 0, 16, 46, 30, 40),
        *band(0, 0, 30, 2, [(10, 0, 4, 2)]), *band(0, 0, 2, 40), *band(0, 38, 30, 2),
        *band(28, 0, 2, 38, [(28, 30, 2, 4)]),
        path_warps("east", 29, 31, 1, 2),
        ("flatten",), ("connect", [(11, 0), (29, 31), (23, 8)]),
    ],
    "marks": [(23, 7, "Maw", (255, 0, 255))],
}

# Infernal Pass: rocky ridge path around the north rim. S -> summit (gap x4-7) and Dreaming Pond (gap x46-49),
# W -> Paradise Barrens (gap rows 8-11).
MAPS["InfernalPass"] = {
    "tileset": "gTileset_KitakamiMountain", "w": 60, "h": 24,
    "ops": [
        ("fill", GRASS), r45(0, 0, 0, 10, 46, 24), r45(46, 0, 0, 10, 14, 24),
        *band(0, 22, 60, 2, [(4, 22, 4, 2), (46, 22, 4, 2)]), *band(0, 0, 60, 2),
        *band(0, 0, 2, 24, [(0, 8, 2, 4)]), *band(58, 0, 2, 24),
        ("flatten",), ("connect", [(5, 23), (47, 23), (0, 9)]),
    ],
    "marks": [],
}

# Paradise Barrens: dry rocky wasteland (grass turned to sand). E -> Infernal Pass (gap rows 24-27).
# Cave mouth into Chilling Waterhead at (39,23).
BARREN = {0x0: 0xD9, 0x1: 0xD9, 0x8: 0xD9, 0x9: 0xD9, 0x0D: 0xD9}
MAPS["ParadiseBarrens"] = {
    "tileset": "gTileset_KitakamiMountain", "w": 44, "h": 40,
    "ops": [
        ("fill", SAND), r45(0, 0, 0, 30, 44, 40), ("swap", BARREN),
        *band(0, 0, 44, 2), *band(0, 38, 44, 2), *band(0, 0, 2, 40), *band(42, 0, 2, 40, [(42, 24, 2, 4)]),
        ("flatten",), ("connect", [(43, 25), (39, 24)]),
    ],
    "marks": [(39, 23, "Cave", (255, 0, 255))],
}

# Dreaming Pond: forest lake. N -> Infernal Pass (gap x6-9), E -> Timeless Woods (gap rows 12-15).
MAPS["DreamingPond"] = {
    "tileset": "gTileset_KitakamiMountain", "w": 36, "h": 32,
    "ops": [
        ("fill", GRASS),
        dense(0, 0, 36, 4), dense(0, 28, 36, 4), dense(0, 4, 4, 24), dense(32, 4, 4, 24),
        ("rect", GRASS, 6, 0, 4, 4), ("rect", GRASS, 32, 12, 4, 4),
        ("box", POND_M, 11, 9, 16, 12),
        ("rect", TALL_M, 5, 22, 8, 5), ("rect", TALL_M, 26, 5, 5, 6),
        path(6, -1, 4, 5), path(31, 12, 6, 4),
    ],
    "marks": [],
}

# Timeless Woods (outer): dense forest with clearings. W -> Dreaming Pond (rows 12-15), N -> deep woods (x18-21),
# S -> Fellhorn Gorge (x18-21).
MAPS["TimelessWoods"] = {
    "tileset": "gTileset_KitakamiMountain", "w": 40, "h": 40,
    "ops": [
        dense(0, 0, 40, 40),
        ("rect", GRASS, 18, 0, 4, 40), ("rect", GRASS, 0, 12, 18, 4), ("rect", GRASS, 8, 17, 24, 12),
        ("rect", GRASS, 26, 4, 8, 8), ("rect", TALL_M, 10, 19, 6, 8), ("rect", TALL_M, 26, 19, 5, 8),
        ("rect", TALL_M, 27, 5, 6, 6), ("rect", TALL_M, 19, 31, 2, 6),
    ],
    "marks": [],
}

# Timeless Woods (deep): the dark clearing of the Bloodmoon Beast. S -> outer woods (x18-21).
MAPS["TimelessWoods_Deep"] = {
    "tileset": "gTileset_KitakamiMountain", "w": 36, "h": 36,
    "ops": [
        dense(0, 0, 36, 36),
        ("rect", GRASS, 18, 24, 4, 12), ("rect", GRASS, 10, 8, 18, 16), ("rect", GRASS, 13, 5, 12, 22),
        ("rect", TALL_M, 11, 10, 4, 6), ("rect", TALL_M, 24, 16, 3, 6),
    ],
    "marks": [(19, 14, "BM", (255, 0, 0))],
}

# Fellhorn Gorge: river gorge around the broken horn (rock pillar). N -> Timeless Woods (x18-21),
# S -> Wistful Fields (edge warp x16-19).
MAPS["FellhornGorge"] = {
    "tileset": "gTileset_KitakamiMountain", "w": 36, "h": 40,
    "ops": [
        ("fill", GRASS), r45(0, 0, 5, 56, 36, 40),
        *band(0, 0, 36, 2, [(18, 0, 4, 2)]), *band(0, 38, 36, 2, [(16, 38, 4, 2)]),
        *band(0, 0, 2, 40), *band(34, 0, 2, 40),
        path_warps("south", 16, 39, 4, 1),
        ("flatten",), ("connect", [(19, 0), (17, 39)]),
    ],
    "marks": [],
}

# --- Caves (Cave tileset) --------------------------------------------------------------------------------------------
# Oni's Maw: Slowpoke Well B1F. Entrance = its ladder (26,29); the ladder down at (11,19) is covered.
MAPS["OnisMaw"] = {
    "tileset": "gTileset_KitakamiCave", "w": 32, "h": 32,
    "ops": [("stamp", "onis_maw_cave", 0, 0), ("copy", 12, 19, 11, 19)],
    "marks": [(26, 29, "exit", (255, 0, 255))],
}
# Crystal Pool: Ice Path 1F in teal. Exits (13,23)/(14,24) and (49,32) all lead to the summit; ladders covered.
MAPS["CrystalPool"] = {
    "tileset": "gTileset_KitakamiCave", "w": 53, "h": 35,
    "ops": [("stamp", "crystal_pool_1f", 0, 0), ("copy", 49, 10, 50, 10), ("copy", 49, 18, 50, 18)],
    "marks": [(49, 32, "exit", (255, 0, 255)), (14, 24, "exit", (255, 0, 255))],
}
# Chilling Waterhead: Ice Path B1F in teal. Ladder (9,20) -> Apple Hills, ladder (10,32) -> Paradise Barrens;
# the other ladders and holes are covered.
MAPS["ChillingWaterhead"] = {
    "tileset": "gTileset_KitakamiCave", "w": 35, "h": 50,
    "ops": [("stamp", "crystal_pool_b1f", 0, 0),
            ("copy", 16, 6, 17, 6), ("copy", 23, 6, 24, 6), ("copy", 9, 11, 10, 11), ("copy", 10, 16, 11, 16),
            ("copy", 17, 17, 18, 17), ("copy", 16, 34, 17, 34)],
    "marks": [(9, 20, "AH", (255, 0, 255)), (10, 32, "PB", (255, 0, 255))],
}

BORDERS = {   # 2x2 border per tileset: what the player sees past an unconnected map edge
    "gTileset_KitakamiMossui": ((("forest_edge_south", 0, 1), ("forest_edge_south", 1, 1)),
                                (("forest_edge_south", 0, 2), ("forest_edge_south", 1, 2))),
    "gTileset_KitakamiFields": ((("id", 0x14, 1), ("id", 0x15, 1)), (("id", 0x1C, 1), ("id", 0x1D, 1))),
    "gTileset_KitakamiMountain": ((("id", 0x14, 1), ("id", 0x15, 1)), (("id", 0x1C, 1), ("id", 0x1D, 1))),
    "gTileset_KitakamiCave": ((("onis_maw_cave", 0, 0), ("onis_maw_cave", 0, 0)),
                              (("onis_maw_cave", 0, 0), ("onis_maw_cave", 0, 0))),
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
    elif len(sys.argv) >= 2 and sys.argv[1] == "events":
        step_events(set(sys.argv[2:]) or None)
    elif len(sys.argv) >= 2 and sys.argv[1] == "check":
        step_check()
    elif len(sys.argv) >= 2 and sys.argv[1] == "write":
        step_write(set(sys.argv[2:]) or None)
    elif len(sys.argv) >= 3 and sys.argv[1] == "stamps":
        step_stamps(sys.argv[2])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
