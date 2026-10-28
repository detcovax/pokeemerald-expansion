#!/usr/bin/env python3
"""TREY (6d-1, TREY_PLAN.md D49): build Kitakami's four secondary tilesets.

Kitakami is hand-built (D47), so there is no source tileset to import. Each Kitakami tileset is put together from
"stamps": rectangles cut out of existing TREY maps (Ecruteak, Bellchime Trail, Route 38/39, Route 45, Ilex Forest,
caves) plus a few pieces of new art drawn here (rice paddies, festival stalls, signboards, apple trees, ...).
Every stamp is rendered to pixels and re-tiled for the Kitakami tileset, so a stamp may come from a map with another
primary tileset or be recoloured (Kitakami Hall, Crystal Pool):
  - an 8x8 tile identical to a tile of the target primary (any palette, any flip) points at the primary;
  - other tiles go into the new secondary; their colours are packed into the secondary's 6 palettes
    (building pieces and nature pieces never share a palette, so 6-S seasons keep roofs and walls unchanged).
    When the colours don't fit, the cheapest pairs of near colours are merged (rare shades first).
Metatile attributes (behaviour, layer type) come from the source metatile; new art states its own.

Run from the repo root:
    python3 tools/trey/kitakami_tiles.py build [Name...]   # write data/tilesets/secondary/kitakami_*/, the C header
                                                           # and docs/trey/kitakami_tiles.json (stamp catalog, 6d-3)
    python3 tools/trey/kitakami_tiles.py preview DIR       # metatile sheets + every stamp, read back from the files

The catalog stores each stamp as rows of map blocks (metatile id | collision << 10 | elevation << 12, collision and
elevation from the source map) so the 6d-3 map writer can stamp them straight into layouts.
"""
import colorsys
import json
import os
import re
import struct
import sys
from collections import Counter

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import season_art as S  # noqa: E402

HEADER = "src/data/tilesets/trey_kitakami.h"
CATALOG = "docs/trey/kitakami_tiles.json"
NUM_PRI_TILES, NUM_PRI_MT, NUM_PRI_PALS = 640, 640, 7
MAX_TILES, MAX_MT, MAX_PALS = 384, 384, 6
LAYER_NORMAL, LAYER_COVERED, LAYER_SPLIT = 0, 1, 2

_layouts = None
_ts_cache = {}


def layouts():
    global _layouts
    if _layouts is None:
        _layouts = {l["name"]: l for l in json.load(open("data/layouts/layouts.json", encoding="utf-8"))["layouts"] if "id" in l}
    return _layouts


def tileset(name):
    if name not in _ts_cache:
        ts = S.load_any_tileset(name)
        mdir = S.tileset_files(name)[2]
        data = open(f"{mdir}/metatile_attributes.bin", "rb").read()
        ts["attrs"] = [a for (a,) in struct.iter_unpack("<I", data)]
        _ts_cache[name] = ts
    return _ts_cache[name]


def map_blocks(mapname):
    lay = layouts()[mapname + "_Layout"]
    w, h = lay["width"], lay["height"]
    data = open(lay["blockdata_filepath"], "rb").read()
    return lay, w, struct.unpack(f"<{w * h}H", data[:w * h * 2])


# ---------------------------------------------------------------------------------------------------------------------
# Rendering metatiles to RGBA layers (None = colour index 0)
# ---------------------------------------------------------------------------------------------------------------------
def tile_rgba(prim, sec, entry, pals):
    t, hf, vf, p = entry & 0x3FF, (entry >> 10) & 1, (entry >> 11) & 1, entry >> 12
    tl, i = (prim["tiles"], t) if t < NUM_PRI_TILES else (sec["tiles"], t - NUM_PRI_TILES)
    tile = tl[i] if i < len(tl) else [0] * 64
    out = []
    for y in range(8):
        for x in range(8):
            c = tile[(7 - y if vf else y) * 8 + (7 - x if hf else x)]
            out.append(None if c == 0 else tuple(pals[p][c]))
    return tuple(out)


def metatile_layers(prim, sec, mid):
    """[layer0 tiles x4, layer1 tiles x4] as 64-pixel tuples, and the attribute word."""
    pals = prim["pals"][:NUM_PRI_PALS] + sec["pals"][NUM_PRI_PALS:13]
    if mid < NUM_PRI_MT:
        mt, attr = prim["metatiles"][mid], prim["attrs"][mid]
    else:
        j = mid - NUM_PRI_MT
        mt, attr = (sec["metatiles"][j], sec["attrs"][j]) if j < len(sec["metatiles"]) else ((0,) * 8, 0)
    return [tile_rgba(prim, sec, e, pals) for e in mt], attr


def split_image(img):
    """RGBA 16x16 image -> four 64-pixel tuples (alpha < 128 -> None)."""
    px = img.load()
    out = []
    for k in range(4):
        ox, oy = (k % 2) * 8, (k // 2) * 8
        out.append(tuple(None if px[ox + x, oy + y][3] < 128 else tuple(px[ox + x, oy + y][:3])
                         for y in range(8) for x in range(8)))
    return out


def gba(c):
    return tuple((v >> 3) << 3 for v in c)


def flip(t, hf, vf):
    return tuple(t[(7 - y if vf else y) * 8 + (7 - x if hf else x)] for y in range(8) for x in range(8))


def layers_image(layers):
    img = Image.new("RGB", (16, 16), (255, 0, 255))
    for L in (0, 1):
        for k in range(4):
            for i, c in enumerate(layers[L * 4 + k]):
                if c is not None:
                    img.putpixel(((k % 2) * 8 + i % 8, (k // 2) * 8 + i // 8), c)
    return img


# ---------------------------------------------------------------------------------------------------------------------
# Recolours (applied to every pixel of a stamp)
# ---------------------------------------------------------------------------------------------------------------------
def recolour(fn):
    def apply(tiles):
        return [tuple(None if c is None else fn(c) for c in t) for t in tiles]
    return apply


def _hsv(c):
    return colorsys.rgb_to_hsv(*(v / 255 for v in c))


def _rgb(h, s, v):
    return tuple(int(k * 255) for k in colorsys.hsv_to_rgb(h % 1.0, max(0, min(1, s)), max(0, min(1, v))))


_snap_sets = {}


def snap_colours(tileset_name):
    """The colours of a tileset's own palettes (7-12), GBA-rounded. New colours are snapped to these so they share
    palettes with the art they sit next to instead of needing palettes of their own."""
    if tileset_name not in _snap_sets:
        pals = tileset(tileset_name)["pals"][NUM_PRI_PALS:13]
        _snap_sets[tileset_name] = sorted({gba(tuple(c)) for p in pals for c in p[1:]})
    return _snap_sets[tileset_name]


def nearest(cols, c):
    return min(cols, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, c)))


def red_thatch(c):
    """D49: Kitakami Hall = Bellchime's thatch, all red (roof, lanterns, lattice), in Ecruteak's roof reds."""
    h, s, v = _hsv(c)
    if 0.08 < h < 0.2 and s > 0.25 and v < 0.86:
        reds = [k for k in snap_colours("gTileset_Ecruteak_City_Hns") if _hsv(k)[1] > 0.3 and (_hsv(k)[0] < 0.05 or _hsv(k)[0] > 0.95)]
        return nearest(reds, _rgb(0.015, s * 1.35, v * 0.95))
    return c


def primary_colours(tileset_name):
    key = ("primary", tileset_name)
    if key not in _snap_sets:
        _snap_sets[key] = sorted({gba(tuple(c)) for p in tileset(tileset_name)["pals"][:NUM_PRI_PALS] for c in p[1:]})
    return _snap_sets[key]


def snapped(make, tileset_name, primary_name):
    """Maker wrapper: every opaque pixel of the art becomes the nearest colour of tileset_name's own palettes or of
    the primary's palettes."""
    def wrapped(ground):
        # Per 8x8 tile: the existing palette that fits its colours best, if it fits well (mean error under SNAP_MAX);
        # otherwise the tile keeps its own colours and the packer finds room for them.
        cands = [[gba(tuple(c)) for c in p[1:]] for p in tileset(primary_name)["pals"][:NUM_PRI_PALS]] + \
                [[gba(tuple(c)) for c in p[1:]] for p in tileset(tileset_name)["pals"][NUM_PRI_PALS:13]]
        rows = make(ground)
        imgs = [img for row in rows for (bottom, top) in row for img in (bottom, top) if img is not None and img is not ground]
        for img in imgs:
            px = img.load()
            for ty in (0, 8):
                for tx in (0, 8):
                    pts = [(tx + x, ty + y) for y in range(8) for x in range(8) if px[tx + x, ty + y][3] >= 128]
                    if not pts:
                        continue
                    cols = Counter(gba(px[p][:3]) for p in pts)

                    def err(pal):
                        return sum(n * sum((a - b) ** 2 for a, b in zip(nearest(pal, c), c)) for c, n in cols.items())
                    best = min(cands, key=err)
                    if err(best) / len(pts) > SNAP_MAX:
                        continue
                    for p in pts:
                        px[p] = nearest(best, gba(px[p][:3])) + (255,)
        return rows
    return wrapped


SNAP_MAX = 24 ** 2


def teal_crystal(c):
    """D49: Crystal Pool = the ice cave in teal."""
    h, s, v = _hsv(c)
    if s < 0.06:                     # the snow outside the cave walls -> dark rock
        return _rgb(0.52, 0.35, v * 0.32)
    return _rgb(h - 0.08, min(1, s * 1.5), v)


# ---------------------------------------------------------------------------------------------------------------------
# New art. A maker returns rows of (bottom layer RGBA 16x16, top layer RGBA 16x16 or None).
# ---------------------------------------------------------------------------------------------------------------------
BROWN, DBROWN, WATER, WATER2 = (152, 104, 56), (104, 64, 32), (112, 168, 232), (88, 144, 216)
RICE, RICE2, RED, WHITE, WOOD, OUT = (72, 168, 56), (136, 208, 88), (216, 48, 40), (248, 248, 240), (176, 120, 64), (56, 40, 32)


def _cut(img, w, h):
    return [[img.crop((x * 16, y * 16, x * 16 + 16, y * 16 + 16)) for x in range(w)] for y in range(h)]


def art_paddy(ground):
    """3x3 rice paddy autotile (corners, edges, centre): water with rice rows inside a dirt bund."""
    img = Image.new("RGBA", (48, 48), WATER + (255,))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 47, 47], outline=BROWN, width=3)
    d.line([0, 47, 47, 47], fill=DBROWN)
    d.line([47, 0, 47, 47], fill=DBROWN)
    d.line([3, 3, 44, 3], fill=DBROWN)
    for y in range(6, 46, 6):
        for x in range(4 + (y // 6 % 2) * 3, 46, 6):
            if 3 <= x - 1 and x + 1 <= 44 and y <= 44:
                d.point([(x, y), (x - 1, y - 1), (x + 1, y - 1), (x, y - 1)], fill=RICE)
                d.point([(x - 1, y - 2), (x + 1, y - 2)], fill=RICE2)
        if y + 2 <= 44:
            d.line([4, y + 2, 43, y + 2], fill=WATER2)
    return [[(c, None) for c in row] for row in _cut(img, 3, 3)]


def art_stall(colour):
    s = Image.new("RGBA", (48, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.rectangle([3, 10, 5, 31], fill=DBROWN)
    d.rectangle([42, 10, 44, 31], fill=DBROWN)
    d.rectangle([2, 20, 45, 29], fill=WOOD, outline=OUT)
    for i, c in enumerate([(232, 88, 64), (248, 200, 64), (120, 200, 96), (248, 248, 248), (232, 88, 64)]):
        d.ellipse([6 + i * 7, 16, 11 + i * 7, 21], fill=c, outline=OUT)
    for i in range(8):
        d.rectangle([i * 6, 0, i * 6 + 5, 9], fill=colour if i % 2 == 0 else WHITE)
        d.pieslice([i * 6, 6, i * 6 + 5, 12], 0, 180, fill=colour if i % 2 == 0 else WHITE)
    d.line([0, 0, 47, 0], fill=OUT)
    return s


def art_signboard():
    s = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.rectangle([6, 14, 8, 31], fill=DBROWN)
    d.rectangle([23, 14, 25, 31], fill=DBROWN)
    d.polygon([(1, 8), (16, 1), (31, 8), (29, 11), (3, 11)], fill=(200, 56, 48), outline=OUT)
    d.rectangle([4, 12, 27, 25], fill=(240, 224, 176), outline=OUT)
    for y in (15, 18, 21):
        d.line([7, y, 24, y], fill=(120, 96, 64))
    return s


def art_pedestal():
    """Stone plinth for the Loyal Three statues (the statues themselves are object events, 6d-3)."""
    s = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.rectangle([1, 6, 14, 15], fill=(150, 150, 160), outline=(72, 72, 88))
    d.rectangle([0, 4, 15, 7], fill=(176, 176, 184), outline=(72, 72, 88))
    d.point([(4, 10), (11, 12), (7, 13)], fill=(96, 144, 72))
    return s


def map_art(mapname, x0, y0, x1, y1):
    """Rows of (bottom layer, top layer) RGBA images of a map rectangle, for art that starts from existing art."""
    lay, w, blocks = map_blocks(mapname)
    prim, sec = tileset(lay["primary_tileset"]), tileset(lay["secondary_tileset"])
    rows = []
    for y in range(y0, y1):
        row = []
        for x in range(x0, x1):
            layers, _ = metatile_layers(prim, sec, blocks[y * w + x] & 0x3FF)
            imgs = []
            for L in (0, 1):
                img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
                for k in range(4):
                    for i, c in enumerate(layers[L * 4 + k]):
                        if c is not None:
                            img.putpixel(((k % 2) * 8 + i % 8, (k // 2) * 8 + i // 8), c + (255,))
                imgs.append(img)
            row.append(tuple(imgs))
        rows.append(row)
    return rows


def art_apple_tree(ground):
    """Apple tree (D49): Route 38's lone maple, leaves turned green, with apples."""
    rows = map_art("Route38", 27, 9, 29, 12)
    for row in rows:
        for (_, top) in row:
            px = top.load()
            for y in range(16):
                for x in range(16):
                    r, g, b, a = px[x, y]
                    if a:
                        h, s, v = _hsv((r, g, b))
                        if (h < 0.11 or h > 0.95) and s > 0.35:
                            px[x, y] = _rgb(0.27 + (0.04 if v > 0.6 else 0), s * 0.85, v * 0.92) + (255,)
    canopy = [rows[0][0][1], rows[0][1][1], rows[1][0][1], rows[1][1][1]]
    spots = [(0, 9, 7), (0, 5, 12), (1, 3, 6), (1, 9, 11), (2, 8, 3), (2, 12, 8), (3, 4, 2), (3, 2, 7)]
    for (k, x, y) in spots:
        d = ImageDraw.Draw(canopy[k])
        if canopy[k].getpixel((x, y))[3]:
            d.rectangle([x, y, x + 1, y + 1], fill=RED + (255,))
            d.point((x, y), fill=(248, 168, 152, 255))
    return rows


def art_flowers(ground):
    """Wistful Fields flower carpet: 2x2 of grass dotted with flowers (bottom layer only)."""
    img = Image.new("RGBA", (32, 32))
    for y in (0, 16):
        for x in (0, 16):
            img.paste(ground, (x, y))
    d = ImageDraw.Draw(img)
    cols = [(248, 248, 248), (248, 216, 64), (232, 120, 176), (168, 136, 232)]
    import random
    rnd = random.Random(49)
    for i in range(22):
        x, y = rnd.randrange(1, 30), rnd.randrange(1, 30)
        c = cols[i % len(cols)]
        d.point([(x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1)], fill=c + (255,))
        d.point((x, y), fill=(248, 200, 64, 255) if c != (248, 216, 64) else (232, 120, 40, 255))
    return [[(c, None) for c in row] for row in _cut(img, 2, 2)]


def over_ground(art):
    """Maker: art on top of the recipe's ground metatile."""
    def make(ground):
        w, h = art.size[0] // 16, art.size[1] // 16
        return [[(ground, c) for c in row] for row in _cut(art, w, h)]
    return make


# ---------------------------------------------------------------------------------------------------------------------
# Recipes (D49)
# ---------------------------------------------------------------------------------------------------------------------
# Map stamp: (name, kind, [(MapName, x0, y0, x1, y1), ...], optional recolour); x1/y1 exclusive, segments stack
# vertically. Art stamp: (name, kind, maker, attribute word, collision). kind: "building" or "nature".
RECIPES = {
    "KitakamiMossui": {
        "primary": "gTileset_Johto_NorthWest_Hns",
        "ground": ("EcruteakCity", 15, 2),      # a plain grass block
        "stamps": [
            ("house_big", "building", [("EcruteakCity", 17, 29, 25, 35)]),
            ("house_small", "building", [("EcruteakCity", 27, 29, 32, 34)]),
            ("pokemon_center", "building", [("EcruteakCity", 36, 44, 42, 49)]),
            ("gate", "building", [("EcruteakCity", 32, 52, 36, 56)]),
            ("lantern", "building", [("EcruteakCity", 17, 31, 18, 33)]),
            ("fence_lanterns", "building", [("EcruteakCity", 28, 25, 45, 26)]),
            ("sign", "building", [("EcruteakCity", 27, 40, 28, 41)]),
            ("kitakami_hall", "building", [("BellchimeTrail", 31, 15, 40, 23), ("BellchimeTrail", 31, 40, 40, 44)],
             recolour(red_thatch)),
            ("maple_on_pad", "nature", [("EcruteakCity", 36, 29, 38, 33)]),
            ("cherry_on_pad", "nature", [("EcruteakCity", 19, 19, 21, 23)]),
            ("forest_maple", "nature", [("EcruteakCity", 20, 0, 30, 7)]),
            ("forest_mixed", "nature", [("EcruteakCity", 0, 0, 15, 22)]),
            ("forest_edge_south", "nature", [("EcruteakCity", 10, 51, 32, 61)]),
            ("pond", "nature", [("EcruteakCity", 28, 13, 36, 23)]),
            ("street", "nature", [("EcruteakCity", 14, 22, 30, 30)]),
        ],
        "art": [(n, k, snapped(m, "gTileset_Ecruteak_City_Hns", "gTileset_Johto_NorthWest_Hns"), a, c) for (n, k, m, a, c) in [
            ("paddy", "nature", art_paddy, 0, 1),
            ("stall_red", "building", over_ground(art_stall(RED)), 0, 1),
            ("stall_blue", "building", over_ground(art_stall((56, 96, 200))), 0, 1),
            ("stall_orange", "building", over_ground(art_stall((232, 136, 40))), 0, 1),
            ("signboard", "building", over_ground(art_signboard()), 0, 1),
            ("pedestal", "building", over_ground(art_pedestal()), 0, 1),
        ]],
    },
    "KitakamiFields": {
        "primary": "gTileset_Johto_General_Hns",
        "ground": ("Route38", 1, 6),
        "stamps": [
            # Whole Route 38/39 first: every farmland piece (fields, canals, fences, ledges, river, bridges, pines).
            ("route38_all", "nature", [("Route38", 0, 0, 52, 50)]),
            ("route39_all", "nature", [("Route39", 0, 0, 40, 54)]),
            ("crop_field_canal", "nature", [("Route39", 0, 0, 40, 8)]),
            ("barn", "building", [("Route39", 13, 12, 19, 16)]),
            ("farmhouse", "building", [("Route39", 20, 13, 24, 16)]),
            ("pond_small", "nature", [("Route39", 11, 22, 14, 26)]),
            ("pine_forest", "nature", [("Route38", 42, 18, 52, 30)]),
            ("bridge", "nature", [("Route38", 6, 6, 16, 12)]),
        ],
        "art": [(n, k, snapped(m, "gTileset_Route38_Farmland_Hns", "gTileset_Johto_General_Hns"), a, c) for (n, k, m, a, c) in [
            ("apple_tree", "nature", art_apple_tree, 0, 1),
            ("paddy", "nature", art_paddy, 0, 1),
            ("flowers", "nature", art_flowers, 0, 0),
        ]],
    },
    "KitakamiMountain": {
        "primary": "gTileset_Johto_NorthEast_Hns",
        "ground": ("Route45", 0, 0),
        "stamps": [
            ("route45_all", "nature", [("Route45", 0, 0, 46, 100)]),
            ("dense_forest", "nature", [("IlexForest", 0, 0, 16, 16)]),
            ("ogerpon_hut", "building", [("EcruteakCity", 1, 51, 10, 56)]),
        ],
    },
    "KitakamiCave": {
        "primary": "gTileset_Johto_General_Hns",
        "stamps": [
            ("onis_maw_cave", "nature", [("SlowpokeWell_B1F", 0, 0, 32, 32)]),
            ("crystal_pool_1f", "nature", [("IcePath_1F", 0, 0, 53, 35)], recolour(teal_crystal)),
            ("crystal_pool_b1f", "nature", [("IcePath_B1F", 0, 0, 35, 50)], recolour(teal_crystal)),
        ],
    },
}


# ---------------------------------------------------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------------------------------------------------
class Builder:
    def __init__(self, name, recipe=None):
        self.name, self.recipe = name, recipe
        if recipe is None:
            return
        self.prim = tileset(recipe["primary"])
        self.prim_tile_index = self._index_primary_tiles()
        self.prim_mt_index = {}
        self.metatiles = []          # [(layers: 8 tile keys, attr, kind)]
        self.mt_lookup = {}          # (layers, attr) -> secondary metatile index
        self.stamps = {}
        self.notes = []
        self.tile_group = {}         # tile key -> source palette group (packing keeps a group together when it can)

    def _index_primary_tiles(self):
        idx = {}
        pals = self.prim["pals"][:NUM_PRI_PALS]
        for t in range(len(self.prim["tiles"])):
            for p in range(NUM_PRI_PALS):
                base = tile_rgba(self.prim, self.prim, t | (p << 12), pals)
                for hf in (0, 1):
                    for vf in (0, 1):
                        idx.setdefault(flip(base, hf, vf), t | (hf << 10) | (vf << 11) | (p << 12))
        return idx

    def primary_metatile(self, layers, attr):
        """Id of an identical primary metatile, or None."""
        if not self.prim_mt_index:
            for mid in range(len(self.prim["metatiles"])):
                ly, at = metatile_layers(self.prim, self.prim, mid)
                self.prim_mt_index.setdefault((tuple(ly), at), mid)
        return self.prim_mt_index.get((tuple(layers), attr))

    def add_metatile(self, layers, attr, kind):
        pid = self.primary_metatile(layers, attr)
        if pid is not None:
            return pid
        key = (tuple(layers), attr)
        if key not in self.mt_lookup:
            self.mt_lookup[key] = len(self.metatiles)
            self.metatiles.append((layers, attr, kind))
        return NUM_PRI_MT + self.mt_lookup[key]

    def add_map_stamp(self, sname, kind, segments, fn=None):
        rows = []
        for (mapname, x0, y0, x1, y1) in segments:
            lay, w, blocks = map_blocks(mapname)
            prim, sec = tileset(lay["primary_tileset"]), tileset(lay["secondary_tileset"])
            for y in range(y0, y1):
                row = []
                for x in range(x0, x1):
                    b = blocks[y * w + x]
                    mid = b & 0x3FF
                    layers, attr = metatile_layers(prim, sec, mid)
                    if fn:
                        layers = fn(layers)
                    ents = prim["metatiles"][mid] if mid < NUM_PRI_MT else (
                        sec["metatiles"][mid - NUM_PRI_MT] if mid - NUM_PRI_MT < len(sec["metatiles"]) else (0,) * 8)
                    for t, e in zip(layers, ents):
                        src = lay["primary_tileset"] if (e & 0x3FF) < NUM_PRI_TILES else lay["secondary_tileset"]
                        self.tile_group.setdefault(t, (src, e >> 12, sname if fn else ""))
                    row.append(self.add_metatile(layers, attr, kind) | (b & 0xFC00))
                rows.append(row)
        self.stamps[sname] = rows

    def add_art_stamp(self, sname, kind, make, attr, collision, ground):
        rows = []
        for row in make(ground):
            out = []
            for (bottom, top) in row:
                layers = split_image(bottom) + (split_image(top) if top else [(None,) * 64] * 4)
                for t in layers:
                    self.tile_group.setdefault(t, ("art", sname, ""))
                out.append(self.add_metatile(layers, attr | (LAYER_NORMAL << 29), kind) | (collision << 10))
            rows.append(out)
        self.stamps[sname] = rows

    def ground_image(self):
        mapname, x, y = self.recipe["ground"]
        lay, w, blocks = map_blocks(mapname)
        prim, sec = tileset(lay["primary_tileset"]), tileset(lay["secondary_tileset"])
        layers, _ = metatile_layers(prim, sec, blocks[y * w + x] & 0x3FF)
        return layers_image(layers).convert("RGBA")

    def build(self):
        for st in self.recipe["stamps"]:
            self.add_map_stamp(st[0], st[1], st[2], st[3] if len(st) > 3 else None)
        ground = self.ground_image() if "ground" in self.recipe else None
        for (sname, kind, make, attr, collision) in self.recipe.get("art", []):
            self.add_art_stamp(sname, kind, make, attr, collision, ground)
        self.pack()

    # -- tiles and palettes ------------------------------------------------------------------------------------------
    def pack(self):
        """Assign every non-primary 8x8 tile a palette (by kind), then dedupe tiles."""
        need = {}   # tile key -> kind
        for layers, _, kind in self.metatiles:
            for t in layers:
                if all(c is None for c in t) or t in self.prim_tile_index:
                    continue
                need.setdefault(t, kind)
        # Tiles whose colours all exist in one of the primary's palettes use that palette (no secondary colours).
        self.prim_pals = [[gba(tuple(c)) for c in p] for p in self.prim["pals"][:NUM_PRI_PALS]]
        self.tile_prim_pal = {}
        for t in list(need):
            cs = {gba(c) for c in t if c is not None}
            for p, pal in enumerate(self.prim_pals):
                if cs <= set(pal[1:]):
                    self.tile_prim_pal[t] = p
                    del need[t]
                    break
        # Colours are merged (cheapest pair first) until the tiles pack into MAX_PALS palettes.
        self.colour_map = {}
        merges = []
        while not self._try_pack(need):
            pair = self._cheapest_pair(need)
            if pair is None:
                sys.exit(f"kitakami_tiles.py: {self.name}: cannot fit the palettes")
            a, b, dist = pair
            self.colour_map[a] = b
            for k, v in list(self.colour_map.items()):
                if v == a:
                    self.colour_map[k] = b
            merges.append(dist)
        if merges:
            self.notes.append(f"{len(merges)} colours merged into near neighbours (largest RGB distance {max(merges) ** 0.5:.0f})")
        self.palettes = [sorted(p, key=lambda c: (sum(c), c)) for p in self.palettes]
        # tiles
        self.tiles, tile_lookup = [[0] * 64], {tuple([0] * 64): 0}
        self.entries = []
        for layers, attr, kind in self.metatiles:
            ents = []
            for t in layers:
                if all(c is None for c in t):
                    ents.append(0)
                    continue
                if t in self.prim_tile_index:
                    ents.append(self.prim_tile_index[t])
                    continue
                if t in self.tile_prim_pal:
                    pp = self.tile_prim_pal[t]
                    idx = tuple(0 if c is None else self.prim_pals[pp].index(gba(c), 1) for c in t)
                    pal_no = pp
                else:
                    pi = self.tile_pal[t]
                    idx = tuple(0 if c is None else 1 + self._nearest(self.palettes[pi], self._col(c)) for c in t)
                    pal_no = NUM_PRI_PALS + pi
                found = None
                for hf in (0, 1):
                    for vf in (0, 1):
                        f = flip(idx, hf, vf)
                        if f in tile_lookup:
                            found = tile_lookup[f] | (hf << 10) | (vf << 11)
                            break
                    if found is not None:
                        break
                if found is None:
                    tile_lookup[idx] = len(self.tiles)
                    found = len(self.tiles)
                    self.tiles.append(list(idx))
                ents.append((NUM_PRI_TILES + (found & 0x3FF)) | (found & 0xC00) | (pal_no << 12))
            self.entries.append(ents)

    def _col(self, c):
        c = gba(c)
        return self.colour_map.get(c, c)

    def _sets(self, need):
        sets = {}
        for t, kind in need.items():
            sets.setdefault(kind, []).append((t, frozenset(self._col(c) for c in t if c is not None)))
        return sets

    def _try_pack(self, need):
        """Pack source-palette groups (then single tiles of groups that don't fit whole) into palettes: first fit,
        biggest colour sets first, most shared colours wins; a palette holds one kind only. True when MAX_PALS is
        enough."""
        palettes, kinds, tile_pal = [], [], {}

        def place(kind, cs, allow_new=True):
            best = None
            for pi, p in enumerate(palettes):
                if kinds[pi] == kind and len(p | cs) <= 15:
                    score = (len(cs & p), -len(p))
                    if best is None or score > best[0]:
                        best = (score, pi)
            if best is None:
                if not allow_new or len(palettes) == MAX_PALS or len(cs) > 15:
                    return None
                palettes.append(set())
                kinds.append(kind)
                best = (None, len(palettes) - 1)
            palettes[best[1]] |= cs
            return best[1]
        groups = {}
        for t, cs in [it for items in self._sets(need).values() for it in items]:
            g = (need[t], self.tile_group.get(t, ("?",)))
            groups.setdefault(g, []).append((t, cs))
        order = sorted(groups.items(), key=lambda kv: -len(frozenset().union(*(cs for _, cs in kv[1]))))
        leftover = []
        for (kind, g), items in order:
            union = frozenset().union(*(cs for _, cs in items))
            pi = place(kind, union, allow_new=len(palettes) < MAX_PALS - 1)
            if pi is None:
                leftover.append((kind, items))
                continue
            for t, _ in items:
                tile_pal[t] = pi
        for kind, items in leftover:
            for t, cs in sorted(items, key=lambda it: -len(it[1])):
                pi = place(kind, cs)
                if pi is None:
                    return False
                tile_pal[t] = pi
        self.palettes, self.pal_kind, self.tile_pal = palettes, kinds, tile_pal
        return True

    def _cheapest_pair(self, need):
        """The cheapest pair of colours of the same kind to merge: distance x pixels of the rarer colour, so rare
        shades go first and the subtle shading of big surfaces (cobble, roofs) survives. The rarer one is replaced."""
        use = {}
        for t, kind in need.items():
            use.setdefault(kind, Counter()).update(self._col(c) for c in t if c is not None)
        best = None
        for kind, cnt in use.items():
            cols = list(cnt)
            for i in range(len(cols)):
                for j in range(i + 1, len(cols)):
                    d = sum((x - y) ** 2 for x, y in zip(cols[i], cols[j]))
                    cost = d * min(cnt[cols[i]], cnt[cols[j]])
                    if best is None or cost < best[3]:
                        a, b = (cols[i], cols[j]) if cnt[cols[i]] < cnt[cols[j]] else (cols[j], cols[i])
                        best = (a, b, d, cost)
        return best[:3] if best else None

    @staticmethod
    def _nearest(pal, c):
        if c in pal:
            return pal.index(c)
        return min(range(len(pal)), key=lambda i: sum((a - b) ** 2 for a, b in zip(pal[i], c)))

    def check(self):
        errs = []
        if len(self.metatiles) > MAX_MT:
            errs.append(f"{len(self.metatiles)} metatiles > {MAX_MT}")
        if len(self.tiles) > MAX_TILES:
            errs.append(f"{len(self.tiles)} tiles > {MAX_TILES}")
        if len(self.palettes) > MAX_PALS:
            errs.append(f"{len(self.palettes)} palettes > {MAX_PALS}")
        return errs

    # -- output ------------------------------------------------------------------------------------------------------
    def folder(self):
        return "data/tilesets/secondary/" + re.sub(r"(?<=[a-z])(?=[A-Z])", "_", self.name).lower()

    def write(self):
        folder = self.folder()
        os.makedirs(f"{folder}/palettes", exist_ok=True)
        pals = [[(0, 0, 0)] * 16 for _ in range(16)]
        for i, p in enumerate(self.palettes):
            pals[NUM_PRI_PALS + i] = [(0, 0, 0)] + list(p) + [(0, 0, 0)] * (15 - len(p))
        for i in range(16):
            S.write_pal(f"{folder}/palettes/{i:02d}.pal", pals[i])
        n = len(self.tiles)
        img = Image.new("P", (128, ((n + 15) // 16) * 8))
        img.putpalette([v for c in pals[NUM_PRI_PALS] for v in c] + [0] * (768 - 48))
        for i, t in enumerate(self.tiles):
            for k, v in enumerate(t):
                img.putpixel(((i % 16) * 8 + k % 8, (i // 16) * 8 + k // 8), v)
        img.save(f"{folder}/tiles.png")
        with open(f"{folder}/metatiles.bin", "wb") as f:
            for ents in self.entries:
                f.write(struct.pack("<8H", *ents))
        with open(f"{folder}/metatile_attributes.bin", "wb") as f:
            for _, attr, _ in self.metatiles:
                f.write(struct.pack("<I", attr))

    def c_code(self):
        folder, b = self.folder(), self.name
        gfx = (f"const u32 gTilesetTiles_{b}[] = INCGFX_U32(\"{folder}/tiles.png\", \".4bpp.fastSmol\");\n"
               f"const u16 gTilesetPalettes_{b}[][16] =\n{{\n"
               + "".join(f"    INCGFX_U16(\"{folder}/palettes/{i:02d}.pal\", \".gbapal\"),\n" for i in range(16)) + "};\n")
        mt = (f"const u16 gMetatiles_{b}[] = INCBIN_U16(\"{folder}/metatiles.bin\");\n"
              f"const u16 gMetatileAttributes_{b}[] = INCBIN_U16(\"{folder}/metatile_attributes.bin\"); // FRLG 32-bit attributes\n")
        # Seasons (6-S) come from season_art.py --write once Kitakami's outdoor maps exist (6d-3); keep its pointer.
        seasonal = os.path.exists(S.SEASONAL_H) and f"gTilesetSeasonal_{b}[" in open(S.SEASONAL_H, encoding="utf-8").read()
        hdr = (f"const struct Tileset gTileset_{b} =\n{{\n    .isCompressed = TRUE,\n    .isSecondary = TRUE,\n"
               f"    .tiles = gTilesetTiles_{b},\n    .palettes = gTilesetPalettes_{b},\n"
               f"    .metatiles = gMetatiles_{b},\n    .metatileAttributes = gMetatileAttributes_{b},\n"
               f"    .callback = NULL,\n"
               + (f"    .seasonal = gTilesetSeasonal_{b}, // TREY (6-S)\n" if seasonal else "") + "};\n")
        return gfx, mt, hdr

    def report(self):
        return (f"  gTileset_{self.name:22} {len(self.metatiles):3}/{MAX_MT} metatiles {len(self.tiles):3}/{MAX_TILES} tiles "
                f"{len(self.palettes)}/{MAX_PALS} palettes (building {self.pal_kind.count('building')}, "
                f"nature {self.pal_kind.count('nature')}), {len(self.stamps)} stamps"
                + "".join(f"\n    note: {n}" for n in self.notes))


def step_build(names=None):
    built, errors = [], []
    for name, recipe in RECIPES.items():
        if names and name not in names:
            continue
        b = Builder(name, recipe)
        b.build()
        errs = b.check()
        print(b.report())
        if errs:
            errors += [f"{name}: {e}" for e in errs]
        else:
            built.append(b)
    if errors:
        sys.exit("kitakami_tiles.py: " + "; ".join(errors))
    for b in built:
        b.write()
    catalog = json.load(open(CATALOG, encoding="utf-8")) if os.path.exists(CATALOG) else {}
    for b in built:
        catalog[f"gTileset_{b.name}"] = {"primary": b.recipe["primary"],
                                         "stamps": {k: {"w": len(v[0]), "h": len(v), "blocks": v} for k, v in b.stamps.items()}}
    os.makedirs(os.path.dirname(CATALOG), exist_ok=True)
    with open(CATALOG, "w", encoding="utf-8", newline="\n") as f:
        json.dump(catalog, f, indent=1)
    gfx, mt, hdr = [], [], []
    for name in RECIPES:     # every recipe's C code (files of tilesets not rebuilt this run are left as they are)
        g, m, h = Builder(name).c_code()
        gfx.append(g)
        mt.append(m)
        hdr.append(h)
    with open(HEADER, "w", encoding="utf-8", newline="\n") as f:
        f.write("// TREY (6d-1, D49): Kitakami's secondary tilesets, generated by tools/trey/kitakami_tiles.py (do not edit).\n"
                "// FRLG format on Johto primaries (32-bit attributes). Included at the end of src/tilesets.c.\n\n"
                + "\n".join(gfx) + "\n" + "".join(mt) + "\n" + "\n".join(hdr))
    print(f"kitakami_tiles.py: wrote {len(built)} tilesets, {HEADER}, {CATALOG}")


# ---------------------------------------------------------------------------------------------------------------------
# Preview (reads the written files back, like the game would)
# ---------------------------------------------------------------------------------------------------------------------
def step_preview(outdir):
    os.makedirs(outdir, exist_ok=True)
    catalog = json.load(open(CATALOG, encoding="utf-8"))
    for tname, entry in catalog.items():
        name = tname[len("gTileset_"):]
        folder = Builder(name).folder()
        prim = tileset(entry["primary"])
        sec = S.load_tileset(folder, True)
        sec["attrs"] = [a for (a,) in struct.iter_unpack("<I", open(f"{folder}/metatile_attributes.bin", "rb").read())]

        def draw(mid):
            return layers_image(metatile_layers(prim, sec, mid)[0])
        n = len(sec["metatiles"])
        sheet = Image.new("RGB", (16 * 16, ((n + 15) // 16) * 16), (40, 40, 40))
        for j in range(n):
            sheet.paste(draw(NUM_PRI_MT + j), ((j % 16) * 16, (j // 16) * 16))
        sheet.resize((sheet.size[0] * 2, sheet.size[1] * 2), Image.NEAREST).save(f"{outdir}/{name}_sheet.png")
        imgs = []
        for sname, st in entry["stamps"].items():
            im = Image.new("RGB", (st["w"] * 16, st["h"] * 16))
            for y, row in enumerate(st["blocks"]):
                for x, b in enumerate(row):
                    im.paste(draw(b & 0x3FF), (x * 16, y * 16))
            imgs.append((sname, im))
        W, x, y, rowh, placed = 1100, 0, 0, 0, []
        for sname, im in imgs:
            if x + im.size[0] > W:
                x, y, rowh = 0, y + rowh + 16, 0
            placed.append((sname, im, x, y + 12))
            x += im.size[0] + 10
            rowh = max(rowh, im.size[1] + 12)
        out = Image.new("RGB", (W, y + rowh + 16), (40, 40, 40))
        d = ImageDraw.Draw(out)
        for sname, im, px, py in placed:
            out.paste(im, (px, py))
            d.text((px, py - 11), sname, fill=(255, 255, 0))
        out.save(f"{outdir}/{name}_stamps.png")
        print(f"preview: {name}: {n} metatiles, {len(imgs)} stamps")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "build":
        step_build(set(sys.argv[2:]) or None)
    elif len(sys.argv) >= 3 and sys.argv[1] == "preview":
        step_preview(sys.argv[2])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
