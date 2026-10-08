#!/usr/bin/env python3
"""TREY: procedural art for the sky tileset (TREY_PLAN.md 5.2, phase 3e art pass).

Run from the repo root:
    python3 tools/trey/sky_art.py --preview OUTDIR   # preview sheet + animated GIFs only
    python3 tools/trey/sky_art.py --write            # write the game files (tileset, anims, puff sprite)

Everything is drawn in code so it can be tweaked and regenerated. Palettes (secondary slots):
    6 sky + wind streaks   7 small clouds   8 storm-cloud walls   9 mountain peaks
In rain/storms, 6-9 are swapped for storm palettes: clouds turn dark, sky, walls and mountains tint darker
(mountain mist goes dark grey).
"""
import math
import os
import random
import struct
import sys

from PIL import Image

# ---------------------------------------------------------------------------
# Palettes (index 0 = transparent)
# ---------------------------------------------------------------------------
PAL_SKY = [(0, 0, 0),
           (176, 216, 248),  # 1 sky
           (196, 228, 252),  # 2 ripple light
           (160, 204, 244),  # 3 ripple shade
           (216, 238, 255),  # 4 swirl light
           (146, 192, 238),  # 5 swirl shade
           (248, 252, 255),  # 6 wind streak head
           (222, 240, 255),  # 7 wind streak
           (188, 222, 250),  # 8 wind streak tail
           ] + [(0, 0, 0)] * 7
def tint(pal, mul=0.8, grey=0.25):
    """Darken and desaturate a palette (used for storm weather)."""
    out = []
    for (r, g, b) in pal:
        avg = (r + g + b) / 3
        out.append(tuple(int(min(255, max(0, (c * (1 - grey) + avg * grey) * mul))) for c in (r, g, b)))
    return out

PAL_SKY_STORM = tint(PAL_SKY, 0.78, 0.35)
PAL_CLOUD = [(0, 0, 0),
             (255, 255, 255),  # 1 lit
             (236, 242, 250),  # 2 light
             (212, 222, 238),  # 3 mid
             (184, 198, 224),  # 4 shade
             (156, 174, 208),  # 5 rim
             ] + [(0, 0, 0)] * 10
PAL_CLOUD_STORM = [(0, 0, 0),
                   (156, 158, 176),
                   (132, 134, 154),
                   (110, 112, 134),
                   (88, 90, 112),
                   (64, 66, 88),
                   ] + [(0, 0, 0)] * 10
PAL_WALL = [(0, 0, 0),
            (214, 218, 232),  # 1 billow highlight
            (178, 184, 206),  # 2 light
            (142, 148, 176),  # 3 mid
            (110, 114, 146),  # 4 dark
            (82, 84, 116),    # 5 deep
            (58, 58, 88),     # 6 deepest / rim
            (232, 236, 246),  # 7 top glint
            ] + [(0, 0, 0)] * 8
PAL_WALL_STORM = None  # set after PAL_WALL
PAL_MOUNTAIN = [(0, 0, 0),
                (250, 252, 255),  # 1 snow
                (214, 226, 244),  # 2 snow shade
                (184, 168, 148),  # 3 rock light
                (146, 128, 112),  # 4 rock mid
                (108, 92, 82),    # 5 rock dark
                (72, 62, 58),     # 6 rock deepest
                (206, 226, 246),  # 7 mist
                (160, 186, 214),  # 8 mist shade
                ] + [(0, 0, 0)] * 7

PAL_WALL_STORM = tint(PAL_WALL, 0.72, 0.2)
# In storms the whole mountain darkens, and the mist round its base turns dark grey (darker than the storm sky).
PAL_MOUNTAIN_STORM = tint(PAL_MOUNTAIN[:7], 0.72, 0.25) + [(100, 104, 116), (82, 86, 100)] + PAL_MOUNTAIN[9:]

SLOT_SKY, SLOT_CLOUD, SLOT_WALL, SLOT_MOUNTAIN = 6, 7, 8, 9
PALETTES = {SLOT_SKY: PAL_SKY, SLOT_CLOUD: PAL_CLOUD, SLOT_WALL: PAL_WALL, SLOT_MOUNTAIN: PAL_MOUNTAIN}

def blank(w=16, h=16):
    return [[0] * w for _ in range(h)]

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

TAU = 2 * math.pi

# ---------------------------------------------------------------------------
# Sky background (animated ripples) and swirls
# ---------------------------------------------------------------------------
SKY_FRAMES = 8

def sky_frame(frame, phase_shift=0.0):
    """16x16 seamless ripple tile. Wavy light and shade lines drift slowly."""
    img = blank()
    ph = TAU * frame / SKY_FRAMES + phase_shift
    for y in range(16):
        for x in range(16):
            c = 1
            # two wave families, integer frequencies so the tile repeats seamlessly
            w1 = (y + 1.6 * math.sin(TAU * x / 16 + ph)) % 8
            w2 = (y + 4 + 1.6 * math.sin(TAU * (x + 5) / 16 - ph)) % 8
            if w1 < 0.85 and (x + frame) % 5 != 0:
                c = 2
            elif w2 < 0.75 and (x * 3 + frame) % 4 != 0:
                c = 3
            img[y][x] = c
    return img

# Swirls rotate half as fast as the first draft: 16 frames per half turn at the sky's frame rate.
SWIRL_FRAMES = 16

def swirl_frame(frame):
    """16x16 swirl overlay (transparent background, drawn over the animated sky): two arms rotating slowly.

    The arms are symmetric every half turn, so SWIRL_FRAMES frames cover half a rotation.
    """
    img = blank()
    rot = (TAU / 2) * frame / SWIRL_FRAMES
    cx, cy = 7.5, 7.5
    for y in range(16):
        for x in range(16):
            dx, dy = x - cx, y - cy
            r = math.hypot(dx, dy)
            if r < 1.2 or r > 7.2:
                continue
            a = math.atan2(dy, dx) - rot
            # spiral: angle grows with radius
            s = (a + r * 0.75) % (TAU / 2)
            if s < 0.5:
                img[y][x] = 4 if r < 5.5 else 2
            elif s < 0.75 and r > 2.5:
                img[y][x] = 5
    return img

# ---------------------------------------------------------------------------
# Jet streams (animated wind streaks over the sky)
# ---------------------------------------------------------------------------
WIND_FRAMES = 8
# Jet streams animate twice as fast as the sky: they advance WIND_SPEED frames per sky/swirl frame.
WIND_SPEED = 2
# Chosen style (2026-10-07): thin streaks over the normal sky, no lane. (row, length, offset) in a 16 px period.
STREAKS = [(2, 9, 0), (6, 6, 9), (9, 11, 4), (13, 7, 12)]

def wind_h_frame(frame):
    """Eastward streaks on a transparent background (top layer over the animated sky), 2 px per frame."""
    img = blank()
    shift = frame * 2
    for (row, length, off) in STREAKS:
        for i in range(length):
            x = (off + shift + i) % 16
            t = i / max(1, length - 1)   # 0 = tail, 1 = head (east end)
            img[row][x] = 6 if t > 0.7 else (7 if t > 0.35 else 8)
            if t > 0.8:
                img[(row + 1) % 16][x] = 7
    return img

def wind_v_frame(frame):
    """Southward streaks (transpose of the eastward art)."""
    h = wind_h_frame(frame)
    return [[h[x][y] for x in range(16)] for y in range(16)]

# ---------------------------------------------------------------------------
# Small clouds (single 16x16 metatile) and the puff effect
# ---------------------------------------------------------------------------
def draw_cloud(img, blobs, light=(-0.6, -0.8), rim=True, w=16, h=16, edge_is_cloud=False):
    """Union of circles, shaded by a top-left light, with a soft rim."""
    inside = [[False] * w for _ in range(h)]
    shade = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            best = None
            for (bx, by, br) in blobs:
                d = math.hypot(x + 0.5 - bx, y + 0.5 - by)
                if d <= br:
                    # normal-ish shading inside this blob
                    nx, ny = (x + 0.5 - bx) / br, (y + 0.5 - by) / br
                    s = nx * light[0] + ny * light[1]
                    if best is None or s > best:
                        best = s
            if best is not None:
                inside[y][x] = True
                shade[y][x] = best
    for y in range(h):
        for x in range(w):
            if not inside[y][x]:
                continue
            def open_at(nx, ny):
                if not (0 <= nx < w and 0 <= ny < h):
                    return not edge_is_cloud
                return not inside[ny][nx]
            edge = any(open_at(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            s = shade[y][x]
            if edge and rim and s < 0.1:
                c = 5
            elif s > 0.45:
                c = 1
            elif s > 0.05:
                c = 2
            elif s > -0.35:
                c = 3
            else:
                c = 4
            img[y][x] = c
    return img

# Clouds fill most of their tile, and bulge out to the middle of each edge so packed clouds merge
# into one big cloud. Rims are only drawn against open sky inside the tile, never along the tile edge.
# Single clouds: big rounded puffs that fill most of the tile (for scattered clouds).
CLOUD_SHAPES = [
    [(8.0, 8.5, 6.2), (4.0, 9.5, 4.4), (12.0, 9.5, 4.4), (8.0, 4.2, 4.4), (8.0, 13.0, 3.6), (11.5, 5.5, 3.2)],  # A
    [(8.0, 9.0, 6.0), (3.5, 8.0, 4.0), (12.5, 8.5, 4.2), (6.0, 4.5, 3.6), (10.5, 4.2, 3.6), (8.0, 13.2, 3.4)],  # B
    [(8.0, 8.0, 6.4), (3.6, 10.0, 4.0), (12.4, 10.2, 4.0), (7.0, 3.8, 3.8), (12.0, 5.0, 3.0), (8.0, 13.4, 3.2)],  # C
]

def cloud_tile(shape):
    return draw_cloud(blank(), CLOUD_SHAPES[shape])

PUFF_FRAMES = 6

def puff_frame(frame, shape=0):
    """32x32 sprite drawn over the player: the cloud swells, then breaks into puffs that drift away."""
    img = blank(32, 32)
    base = CLOUD_SHAPES[shape]
    if frame < 2:
        scale = 1.12 if frame == 0 else 1.25
        blobs = [(8 + (bx - 8) * scale + 8, 8 + (by - 8) * scale + 10, br * scale) for (bx, by, br) in base]
        # only the parts that reach outside / above the player are visible as a swell
        return draw_cloud(img, blobs, w=32, h=32)
    rnd = random.Random(7)
    t = (frame - 1) / (PUFF_FRAMES - 1)
    puffs = []
    for i in range(7):
        ang = TAU * i / 7 + rnd.uniform(-0.3, 0.3)
        dist = 4 + 9 * t + rnd.uniform(0, 2)
        r = max(0.8, 3.2 * (1 - t) + rnd.uniform(-0.3, 0.4))
        puffs.append((16 + math.cos(ang) * dist, 18 + math.sin(ang) * dist * 0.8 - 3 * t, r))
    return draw_cloud(img, puffs, w=32, h=32)

# ---------------------------------------------------------------------------
# Storm-cloud walls (autotile, impassable)
# ---------------------------------------------------------------------------
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

def dither_level(v, levels, x, y):
    """v in 0..1 -> index 0..levels-1 with 4x4 ordered dithering between levels."""
    f = clamp(v, 0.0, 0.9999) * (levels - 1)
    base = int(f)
    frac = f - base
    if frac > (BAYER[y % 4][x % 4] + 0.5) / 16:
        base += 1
    return clamp(base, 0, levels - 1)

# Big billows on a 32 px torus, so a 2x2 block of centre pieces repeats without seams.
WALL_BILLOWS = [(6, 7, 9.5), (22, 5, 8.5), (15, 18, 10.5), (2, 24, 8.0), (27, 22, 9.0), (10, 31, 7.5), (30, 12, 6.5)]

def wall_height(x, y):
    best = 0.0
    for (bx, by, br) in WALL_BILLOWS:
        for ox in (-32, 0, 32):
            for oy in (-32, 0, 32):
                d2 = (x + 0.5 - bx - ox) ** 2 + (y + 0.5 - by - oy) ** 2
                if d2 < br * br:
                    best = max(best, math.sqrt(br * br - d2) / br)
    return best

def wall_texture(x, y):
    """Storm-cloud tops: big pale billows with strong shading (chosen style: version 2)."""
    h = wall_height(x, y)
    hx = wall_height(x + 1, y) - wall_height(x - 1, y)
    hy = wall_height(x, y + 1) - wall_height(x, y - 1)
    light = clamp(0.55 + h * 0.25 - (hx * 0.9 + hy * 1.2) * 1.6, 0, 1)  # chosen style: version 2
    # 1 = brightest .. 5 = deep
    return 5 - dither_level(light, 5, x, y)

def wall_edge(u):
    """Storm walls: smooth wavy edge (period 16, so neighbouring pieces line up)."""
    return 3.0 + 1.1 * math.sin(TAU * u / 16 + 0.6)

def cloud_edge(u):
    """Cloud banks: round bumps every 8 px with the dips pointing inward, like a cloud outline."""
    # one big round bump per tile edge (top at the middle), meeting the next tile's bump in a dip
    t = (u % 16) - 7.5
    return 1.0 + 7.0 - math.sqrt(max(0.0, 7.0 ** 2 - (abs(t) * 0.78) ** 2))

def autotile_piece(n, e, s, w, ne=False, nw=False, se=False, sw=False, ox=0, oy=0,
                   texture=None, edge=wall_edge, rim=(7, 5, 3, 1, 4, 2), corner_r=5.6, notch_r=4.6):
    """One 16x16 piece of a solid mass (storm wall or cloud bank).

    n/e/s/w: True if that side is open sky. ne..sw: True for an inner-corner notch (diagonal open).
    ox/oy select which part of the 32 px texture this piece shows, so a 2x2 block of pieces tiles seamlessly.
    rim: colours for (top edge, bottom edge, side edge, 2nd row below top, 2nd row above bottom, 2nd column in).
    """
    img = blank()
    for y in range(16):
        for x in range(16):
            solid = True
            # In a quadrant where both neighbouring sides are open (an outer corner), the outline is one
            # round curve; elsewhere each open side follows the edge profile.
            corner = None
            for (open_a, open_b, left, top) in ((n, w, True, True), (n, e, False, True), (s, w, True, False), (s, e, False, False)):
                if open_a and open_b and (x <= 7) == left and (y <= 7) == top:
                    corner = True
            if corner:
                if math.hypot(x - 7.5, y - 7.5) > corner_r:
                    solid = False
            else:
                if n and y < edge(x):
                    solid = False
                if s and (15 - y) < edge(x):
                    solid = False
                if w and x < edge(y):
                    solid = False
                if e and (15 - x) < edge(y):
                    solid = False
            for (flag, cx, cy) in ((nw, 0, 0), (ne, 15, 0), (sw, 0, 15), (se, 15, 15)):
                if flag and math.hypot(x - cx, y - cy) < notch_r:
                    solid = False
            if solid:
                img[y][x] = texture(x + ox, y + oy)
    # Smooth rim: flat colours by facing direction, no dithering on the outer two pixels.
    out = [row[:] for row in img]
    def is_open(x, y):
        return 0 <= x < 16 and 0 <= y < 16 and img[y][x] == 0
    top, bottom, side, top2, bottom2, side2 = rim
    for y in range(16):
        for x in range(16):
            if img[y][x] == 0:
                continue
            if is_open(x, y - 1):
                out[y][x] = top
            elif is_open(x, y + 1):
                out[y][x] = bottom
            elif is_open(x - 1, y) or is_open(x + 1, y):
                out[y][x] = side
            elif is_open(x, y - 2) or is_open(x - 1, y - 1) or is_open(x + 1, y - 1):
                out[y][x] = top2
            elif is_open(x, y + 2) or is_open(x - 1, y + 1) or is_open(x + 1, y + 1):
                out[y][x] = bottom2
            elif is_open(x - 2, y) or is_open(x + 2, y):
                out[y][x] = side2
    return out

def wall_tile(n, e, s, w, ne=False, nw=False, se=False, sw=False, ox=0, oy=0):
    return autotile_piece(n, e, s, w, ne, nw, se, sw, ox, oy, texture=wall_texture)

# Cloud banks (multi-tile autotiled clouds) were tried on 2026-10-07 and dropped for now: next to the single
# clouds they looked less detailed. Encounter areas are patches of single clouds, used like tall grass.

WALL_PIECES = {
    "wall_center": (False, False, False, False),
    "wall_n": (True, False, False, False),
    "wall_s": (False, False, True, False),
    "wall_w": (False, False, False, True),
    "wall_e": (False, True, False, False),
    "wall_nw": (True, False, False, True),
    "wall_ne": (True, True, False, False),
    "wall_sw": (False, False, True, True),
    "wall_se": (False, True, True, False),
    # one-tile-wide parts: ends of a strip, straight strips, and a lone tile (n, e, s, w open)
    "wall_end_n": (True, True, False, True),
    "wall_end_s": (False, True, True, True),
    "wall_end_w": (True, False, True, True),
    "wall_end_e": (True, True, True, False),
    "wall_ns": (True, False, True, False),
    "wall_ew": (False, True, False, True),
    "wall_single": (True, True, True, True),
}
WALL_INNER = {
    "wall_inner_nw": dict(nw=True),
    "wall_inner_ne": dict(ne=True),
    "wall_inner_sw": dict(sw=True),
    "wall_inner_se": dict(se=True),
}

# ---------------------------------------------------------------------------
# Mountain peaks (seen from above, poking through the sky layer)
# ---------------------------------------------------------------------------
# Chosen style (2026-10-07): version 1 peaks and ridge.
def peak_image(size, seed):
    """size x size px peak: chunky rounded rock, snowy top, soft mist edge."""
    rnd = random.Random(seed)
    img = blank(size, size)
    c = (size - 1) / 2
    radius = size / 2 - 1
    ridges = [rnd.uniform(0, TAU) for _ in range(5)]
    for y in range(size):
        for x in range(size):
            dx, dy = x - c, y - c
            r = math.hypot(dx, dy)
            a = math.atan2(dy, dx)
            wobble = 1 + 0.12 * math.sin(a * 5 + seed) + 0.06 * math.sin(a * 9 + seed * 2)
            rr = r / (radius * wobble)
            if rr > 1.0:
                continue
            ridge = max(math.cos(a - ra) for ra in ridges)
            hgt = 1 - rr + 0.18 * max(0, ridge) ** 6 * (1 - rr)
            lit = -(dx * 0.6 + dy * 0.8) / (r + 0.01)   # slope facing the top-left is lit
            if rr > 0.86:
                col = 7 if lit > 0 else 8               # mist at the base
            elif hgt > 0.62 or (hgt > 0.5 and ridge > 0.97):
                col = 1 if lit > -0.2 else 2            # snow
            elif hgt > 0.45 and ridge > 0.9:
                col = 2 if lit > 0 else 3
            else:
                col = 3 if lit > 0.35 else 4 if lit > -0.25 else 5
                if ridge > 0.985 and lit < 0:
                    col = 6
            img[y][x] = col
    return img

def ridge_image(width, height, seed, cap=None):
    """Horizontal ridge piece (repeats left-right). cap = 'left' / 'right' rounds that end."""
    img = blank(width, height)
    cy = (height - 1) / 2
    for y in range(height):
        for x in range(width):
            u = x / width
            crest = cy + 1.2 * math.sin(TAU * u * 2 + 0.7)  # periodic in width -> seamless
            half = height / 2 - 2 + 1.0 * math.sin(TAU * u + 1.9)
            if cap == "left":
                half *= min(1, (x + 1) / 10) ** 0.5
            if cap == "right":
                half *= min(1, (width - x) / 10) ** 0.5
            d = (y - crest) / max(0.5, half)
            if abs(d) > 1:
                continue
            if abs(d) < 0.22:
                col = 1 if y <= crest else 2
            elif abs(d) > 0.86:
                col = 7 if d < 0 else 8
            elif d < 0:
                col = 3 if (x + y) % 7 else 4
            else:
                col = 5 if (x * 3 + y) % 9 else 6
            img[y][x] = col
    return img

# ---------------------------------------------------------------------------
# Rendering helpers for previews
# ---------------------------------------------------------------------------
def to_rgba(img, pal):
    h, w = len(img), len(img[0])
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = out.load()
    for y in range(h):
        for x in range(w):
            if img[y][x]:
                px[x, y] = pal[img[y][x]] + (255,)
    return out

def hflip(img):
    return [row[::-1] for row in img]

def vflip(img):
    return img[::-1]

AUTOTILE_KEYS = {(0, 0, 0, 0): "center", (1, 0, 0, 0): "n", (0, 0, 1, 0): "s", (0, 0, 0, 1): "w",
                 (0, 1, 0, 0): "e", (1, 0, 0, 1): "nw", (1, 1, 0, 0): "ne", (0, 0, 1, 1): "sw", (0, 1, 1, 0): "se",
                 (1, 1, 0, 1): "end_n", (0, 1, 1, 1): "end_s", (1, 0, 1, 1): "end_w", (1, 1, 1, 0): "end_e",
                 (1, 0, 1, 0): "ns", (0, 1, 0, 1): "ew", (1, 1, 1, 1): "single"}

def autotile_key(cells, x, y, edge_solid):
    """Which piece a cell of a solid mass needs, from its neighbours (edge_solid: off-map counts as solid)."""
    def solid(px, py):
        if (px, py) in cells:
            return True
        return edge_solid(px, py)
    n, s_, e, w_ = not solid(x, y - 1), not solid(x, y + 1), not solid(x + 1, y), not solid(x - 1, y)
    key = AUTOTILE_KEYS.get((int(n), int(e), int(s_), int(w_)), "center")
    if key == "center":
        for (k, dx, dy) in (("inner_se", 1, 1), ("inner_sw", -1, 1), ("inner_ne", 1, -1), ("inner_nw", -1, -1)):
            if not solid(x + dx, y + dy):
                return k
    return key

def autotile_set(make, pal):
    """All pieces (and their 2x2 texture variants) of a mass, rendered with palette pal."""
    pieces = {}
    for vx in (0, 1):
        for vy in (0, 1):
            for k, v in WALL_PIECES.items():
                pieces[(k[5:], vx, vy)] = to_rgba(make(*v, ox=vx * 16, oy=vy * 16), pal)
            for k, v in WALL_INNER.items():
                pieces[(k[5:], vx, vy)] = to_rgba(make(False, False, False, False, ox=vx * 16, oy=vy * 16, **v), pal)
    return pieces

def sample_route(frame, storm=False, w=20, h=16):
    """A small sample route: storm walls as borders, a mountain range, clouds and a jet stream."""
    cloud_pal = PAL_CLOUD_STORM if storm else PAL_CLOUD
    sky_pal = PAL_SKY_STORM if storm else PAL_SKY
    wall_pal = PAL_WALL_STORM if storm else PAL_WALL
    mountain_pal = PAL_MOUNTAIN_STORM if storm else PAL_MOUNTAIN
    canvas = Image.new("RGBA", (w * 16, h * 16), (0, 0, 0, 255))
    sky_a = to_rgba(sky_frame(frame % SKY_FRAMES), sky_pal)
    sky_b = to_rgba(sky_frame(frame % SKY_FRAMES, math.pi), sky_pal)
    swirl = to_rgba(swirl_frame(frame % SWIRL_FRAMES), sky_pal)  # overlay on the sky below
    wind_e = to_rgba(wind_h_frame(frame * WIND_SPEED % WIND_FRAMES), sky_pal)
    wind_s = to_rgba(wind_v_frame(frame * WIND_SPEED % WIND_FRAMES), sky_pal)
    walls = {}
    for vx in (0, 1):
        for vy in (0, 1):
            for k, v in WALL_PIECES.items():
                walls[(k, vx, vy)] = to_rgba(wall_tile(*v, ox=vx * 16, oy=vy * 16), wall_pal)
            for k, v in WALL_INNER.items():
                walls[(k, vx, vy)] = to_rgba(wall_tile(False, False, False, False, ox=vx * 16, oy=vy * 16, **v), wall_pal)
    clouds = [to_rgba(cloud_tile(i), cloud_pal) for i in range(3)]
    rnd = random.Random(3)
    # base sky
    for y in range(h):
        for x in range(w):
            canvas.alpha_composite(sky_a if (x * 7 + y * 3) % 5 else sky_b, (x * 16, y * 16))
    for (x, y) in ((5, 4), (14, 11), (9, 13)):
        canvas.alpha_composite(swirl, (x * 16, y * 16))
    # storm walls: top 2 rows, bottom 2 rows, left column
    solid = set()
    for x in range(w):
        for y in (0, 1, h - 2, h - 1):
            solid.add((x, y))
    for y in range(h):
        solid.add((0, y))
    for (x, y) in ((1, 2), (1, 3), (2, 2), (1, h - 3), (2, h - 3), (1, h - 4)):
        solid.add((x, y))
    def is_solid(x, y):
        return (x, y) in solid or x < 0 or y < 0 or x >= w or y >= h
    for (x, y) in solid:
        n, s_, e, w_ = not is_solid(x, y - 1), not is_solid(x, y + 1), not is_solid(x + 1, y), not is_solid(x - 1, y)
        key = {(0, 0, 0, 0): "wall_center", (1, 0, 0, 0): "wall_n", (0, 0, 1, 0): "wall_s", (0, 0, 0, 1): "wall_w",
               (0, 1, 0, 0): "wall_e", (1, 0, 0, 1): "wall_nw", (1, 1, 0, 0): "wall_ne", (0, 0, 1, 1): "wall_sw",
               (0, 1, 1, 0): "wall_se"}.get((int(n), int(e), int(s_), int(w_)), "wall_center")
        if key == "wall_center":
            if not is_solid(x + 1, y + 1):
                key = "wall_inner_se"
            elif not is_solid(x - 1, y + 1):
                key = "wall_inner_sw"
            elif not is_solid(x + 1, y - 1):
                key = "wall_inner_ne"
            elif not is_solid(x - 1, y - 1):
                key = "wall_inner_nw"
        canvas.alpha_composite(walls[(key, x % 2, y % 2)], (x * 16, y * 16))
    # jet stream eastward along row 7, then south down column 15
    for x in range(3, 15):
        canvas.alpha_composite(wind_e, (x * 16, 7 * 16))
    for y in range(8, 12):
        canvas.alpha_composite(wind_s, (15 * 16, y * 16))
    # mountains
    canvas.alpha_composite(to_rgba(peak_image(48, 11), mountain_pal), (6 * 16, 9 * 16))
    canvas.alpha_composite(to_rgba(peak_image(32, 5), mountain_pal), (11 * 16, 3 * 16))
    canvas.alpha_composite(to_rgba(ridge_image(16, 32, 1, "left"), mountain_pal), (16 * 16, 3 * 16))
    canvas.alpha_composite(to_rgba(ridge_image(16, 32, 1), mountain_pal), (17 * 16, 3 * 16))
    canvas.alpha_composite(to_rgba(ridge_image(16, 32, 1, "right"), mountain_pal), (18 * 16, 3 * 16))
    # cloud patches: single clouds packed like tall grass, plus a few scattered ones
    patches = [(3, 3), (4, 3), (5, 3), (3, 4), (4, 4), (5, 4), (6, 4), (4, 5), (5, 5),
               (2, 9), (3, 9), (4, 9), (2, 10), (3, 10), (4, 10), (3, 11), (4, 11),
               (16, 9), (17, 9), (18, 9), (16, 10), (17, 10), (18, 10), (17, 11),
               (8, 4), (9, 5), (12, 12), (13, 12), (7, 13), (14, 5)]
    for (x, y) in patches:
        canvas.alpha_composite(clouds[(x * 2 + y) % 3], (x * 16, y * 16))
    return canvas

def make_preview(out):
    os.makedirs(out, exist_ok=True)
    S = 3
    # 1. tile sheet
    items = []
    def add(label, img, pal):
        items.append((label, to_rgba(img, pal)))
    for f in range(SKY_FRAMES):
        add(f"sky {f}", sky_frame(f), PAL_SKY)
    for f in range(SWIRL_FRAMES):
        add(f"swirl {f}", swirl_frame(f), PAL_SKY)
    for f in range(WIND_FRAMES):
        add(f"wind E {f}", wind_h_frame(f), PAL_SKY)
    for f in range(WIND_FRAMES):
        add(f"wind S {f}", wind_v_frame(f), PAL_SKY)
    for i in range(3):
        add(f"cloud {'ABC'[i]}", cloud_tile(i), PAL_CLOUD)
    for i in range(3):
        add(f"storm {'ABC'[i]}", cloud_tile(i), PAL_CLOUD_STORM)
    for k, v in WALL_PIECES.items():
        add(k[5:], wall_tile(*v), PAL_WALL)
    for k, v in WALL_INNER.items():
        add(k[5:], wall_tile(False, False, False, False, **v), PAL_WALL)
    sky_bg = to_rgba(sky_frame(0), PAL_SKY)
    cols = 8
    cell = 16 * S + 12
    sheet = Image.new("RGBA", (cols * cell + 8, ((len(items) + cols - 1) // cols) * (cell + 10) + 8), (40, 44, 60, 255))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for i, (label, im) in enumerate(items):
        x, y = 8 + (i % cols) * cell, 8 + (i // cols) * (cell + 10)
        bg = sky_bg.copy()
        bg.alpha_composite(im)
        sheet.paste(bg.resize((16 * S, 16 * S), Image.NEAREST), (x, y))
        d.text((x, y + 16 * S + 1), label, fill=(230, 230, 240))
    sheet.save(f"{out}/sky_tiles_sheet.png")

    # 2. mountains + puff frames
    big = Image.new("RGBA", (16 * 12, 16 * 4), (0, 0, 0, 0))
    for y in range(4):
        for x in range(12):
            big.alpha_composite(to_rgba(sky_frame(0), PAL_SKY), (x * 16, y * 16))
    big.alpha_composite(to_rgba(peak_image(32, 5), PAL_MOUNTAIN), (0, 8))
    big.alpha_composite(to_rgba(peak_image(48, 11), PAL_MOUNTAIN), (34, 0))
    for i, cap in enumerate(("left", None, None, "right")):
        big.alpha_composite(to_rgba(ridge_image(16, 32, 1, cap), PAL_MOUNTAIN), (90 + i * 16, 16))
    big.resize((big.width * S, big.height * S), Image.NEAREST).save(f"{out}/sky_mountains.png")

    frames = []
    for f in range(PUFF_FRAMES):
        fr = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        for y in range(2):
            for x in range(2):
                fr.alpha_composite(to_rgba(sky_frame(0), PAL_SKY), (x * 16, y * 16))
        fr.alpha_composite(to_rgba(cloud_tile(0), PAL_CLOUD), (8, 10))
        fr.alpha_composite(to_rgba(puff_frame(f), PAL_CLOUD), (0, 0))
        frames.append(fr.resize((32 * 4, 32 * 4), Image.NEAREST))
    strip = Image.new("RGBA", (len(frames) * 132, 128), (40, 44, 60, 255))
    for i, fr in enumerate(frames):
        strip.paste(fr, (i * 132, 0))
    strip.save(f"{out}/sky_cloud_puff_frames.png")
    frames[0].save(f"{out}/sky_cloud_puff.gif", save_all=True, append_images=frames[1:] + [frames[-1]] * 3,
                   duration=90, loop=0, disposal=2)

    # 3. sample route, animated (normal and storm)
    for storm in (False, True):
        gif = [sample_route(f, storm).resize((20 * 16 * 2, 16 * 16 * 2), Image.NEAREST) for f in range(16)]
        name = "sky_route_storm" if storm else "sky_route"
        gif[0].save(f"{out}/{name}.png")
        gif[0].save(f"{out}/{name}.gif", save_all=True, append_images=gif[1:], duration=120, loop=0)
    print("preview written to", out)

# ---------------------------------------------------------------------------
# Game files (--write)
# ---------------------------------------------------------------------------
TILESET_DIR = "data/tilesets/secondary/trey_sky"
LAYOUT_DIR = "data/layouts/TreyTest_Route101Sky"
PUFF_DIR = "graphics/field_effects/pics"
METATILE_HEADER = "include/constants/trey_sky_metatiles.h"

# Behaviours (include/constants/metatile_behaviors.h)
MB_NORMAL = 0x00
MB_SKY_CLOUD = 0x05
MB_SKY_WIND_NORTH, MB_SKY_WIND_SOUTH, MB_SKY_WIND_WEST, MB_SKY_WIND_EAST = 0x54, 0x55, 0x56, 0x57
LAYER_COVERED = 1  # both layers are drawn below the player

# Animated 2x2 tile blocks, at fixed tile indexes (tile 0 is transparent). Frame 0 is also stored in tiles.png.
ANIM_BLOCKS = [("sky_a", 1), ("sky_b", 5), ("swirl", 9), ("wind_e", 13), ("wind_s", 17)]
FIRST_STATIC_TILE = 21

def split_tiles(img16):
    """16x16 image -> 4 tiles (TL, TR, BL, BR) as tuples of 64 indices."""
    out = []
    for ty in (0, 8):
        for tx in (0, 8):
            out.append(tuple(img16[ty + y][tx + x] for y in range(8) for x in range(8)))
    return out

def tile_flips(t):
    rows = [t[i * 8:(i + 1) * 8] for i in range(8)]
    h = tuple(v for r in rows for v in r[::-1])
    v = tuple(v for r in rows[::-1] for v in r)
    hv = tuple(v for r in rows[::-1] for v in r[::-1])
    return {(0, 0): t, (1, 0): h, (0, 1): v, (1, 1): hv}

class TileSheet:
    def __init__(self):
        self.tiles = [tuple([0] * 64)]
        for (name, base) in ANIM_BLOCKS:
            pass
        self.tiles += [tuple([0] * 64)] * (FIRST_STATIC_TILE - 1)  # anim slots, filled below
        self.lookup = {}

    def set_anim_block(self, base, img16):
        for i, t in enumerate(split_tiles(img16)):
            self.tiles[base + i] = t

    def add(self, t):
        """Returns (index, hflip, vflip), reusing an existing tile (or a flip of one) when possible."""
        if all(v == 0 for v in t):
            return (0, 0, 0)
        for (hf, vf), ft in tile_flips(t).items():
            if ft in self.lookup:
                return (self.lookup[ft], hf, vf)
        self.tiles.append(t)
        self.lookup[t] = len(self.tiles) - 1
        return (len(self.tiles) - 1, 0, 0)

def entry(index, hf, vf, pal):
    return (512 + index) | (hf << 10) | (vf << 11) | (pal << 12)

def anim_entries(base, pal, hflip_block=False, vflip_block=False):
    """Entries for a 2x2 animated block, optionally mirrored as a whole."""
    order = [0, 1, 2, 3]
    if hflip_block:
        order = [order[1], order[0], order[3], order[2]]
    if vflip_block:
        order = [order[2], order[3], order[0], order[1]]
    return [entry(base + i, int(hflip_block), int(vflip_block), pal) for i in order]

def write_pal(path, colors):
    with open(path, "w", newline="\r\n") as f:
        f.write("JASC-PAL\n0100\n16\n")
        for r, g, b in colors:
            f.write(f"{r} {g} {b}\n")

def write_png(path, img, pal, bits=4):
    h, w = len(img), len(img[0])
    im = Image.new("P", (w, h), 0)
    flat = []
    for c in pal:
        flat.extend(c)
    im.putpalette(flat)
    px = im.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = img[y][x]
    im.save(path, bits=bits)

def build_metatiles(sheet):
    """Returns [(name, bottom 4 entries, top 4 entries, behaviour)] in metatile order (IDs from 0x200)."""
    sky_a = anim_entries(1, SLOT_SKY)
    sky_b = anim_entries(5, SLOT_SKY)
    blank4 = [entry(0, 0, 0, SLOT_SKY)] * 4
    mts = []
    def top_from(img16, pal):
        out = []
        for t in split_tiles(img16):
            i, hf, vf = sheet.add(t)
            out.append(entry(i, hf, vf, pal))
        return out
    mts.append(("Sky", sky_a, blank4, MB_NORMAL))
    mts.append(("SkyAlt", sky_b, blank4, MB_NORMAL))
    mts.append(("Swirl", sky_a, anim_entries(9, SLOT_SKY), MB_NORMAL))
    mts.append(("WindEast", sky_a, anim_entries(13, SLOT_SKY), MB_SKY_WIND_EAST))
    mts.append(("WindWest", sky_a, anim_entries(13, SLOT_SKY, hflip_block=True), MB_SKY_WIND_WEST))
    mts.append(("WindSouth", sky_a, anim_entries(17, SLOT_SKY), MB_SKY_WIND_SOUTH))
    mts.append(("WindNorth", sky_a, anim_entries(17, SLOT_SKY, vflip_block=True), MB_SKY_WIND_NORTH))
    for i, letter in enumerate("ABC"):
        mts.append((f"Cloud{letter}", sky_a, top_from(cloud_tile(i), SLOT_CLOUD), MB_SKY_CLOUD))
    # storm-cloud walls: variants keep the 32 px texture continuous along edges and in the middle
    def wall_variants(key):
        if key == "center":
            return [(0, 0), (1, 0), (0, 1), (1, 1)]
        if key in ("n", "s"):
            return [(0, 0), (1, 0)]
        if key in ("e", "w"):
            return [(0, 0), (0, 1)]
        return [(0, 0)]
    for k, v in list(WALL_PIECES.items()) + list(WALL_INNER.items()):
        key = k[5:]
        for (vx, vy) in wall_variants(key):
            if k in WALL_PIECES:
                img = wall_tile(*v, ox=vx * 16, oy=vy * 16)
            else:
                img = wall_tile(False, False, False, False, ox=vx * 16, oy=vy * 16, **v)
            suffix = "" if len(wall_variants(key)) == 1 else f"_{vx}{vy}"
            name = "Wall_" + "".join(p.capitalize() for p in key.split("_")) + suffix
            mts.append((name, sky_a, top_from(img, SLOT_WALL), MB_NORMAL))
    # mountains
    def add_big(prefix, img, w, h):
        for my in range(h):
            for mx in range(w):
                part = [row[mx * 16:(mx + 1) * 16] for row in img[my * 16:(my + 1) * 16]]
                mts.append((f"{prefix}_{mx}{my}", sky_a, top_from(part, SLOT_MOUNTAIN), MB_NORMAL))
    add_big("PeakSmall", peak_image(32, 5), 2, 2)
    add_big("PeakLarge", peak_image(48, 11), 3, 3)
    for cap, nm in ((None, "RidgeMid"), ("left", "RidgeLeft"), ("right", "RidgeRight")):
        add_big(nm, ridge_image(16, 32, 1, cap), 1, 2)
    return mts

def write_game_files():
    os.makedirs(f"{TILESET_DIR}/palettes/storm", exist_ok=True)
    sheet = TileSheet()
    sheet.set_anim_block(1, sky_frame(0))
    sheet.set_anim_block(5, sky_frame(0, math.pi))
    sheet.set_anim_block(9, swirl_frame(0))
    sheet.set_anim_block(13, wind_h_frame(0))
    sheet.set_anim_block(17, wind_v_frame(0))
    mts = build_metatiles(sheet)
    assert len(sheet.tiles) <= 512, len(sheet.tiles)
    assert len(mts) <= 512

    # tiles.png: 16 tiles per row
    rows = (len(sheet.tiles) + 15) // 16
    img = [[0] * 128 for _ in range(rows * 8)]
    for i, t in enumerate(sheet.tiles):
        ox, oy = (i % 16) * 8, (i // 16) * 8
        for y in range(8):
            for x in range(8):
                img[oy + y][ox + x] = t[y * 8 + x]
    write_png(f"{TILESET_DIR}/tiles.png", img, PAL_SKY)

    storm = {SLOT_SKY: PAL_SKY_STORM, SLOT_CLOUD: PAL_CLOUD_STORM, SLOT_WALL: PAL_WALL_STORM, SLOT_MOUNTAIN: PAL_MOUNTAIN_STORM}
    for i in range(16):
        write_pal(f"{TILESET_DIR}/palettes/{i:02d}.pal", PALETTES.get(i, [(0, 0, 0)] * 16))
    for slot, pal in storm.items():
        write_pal(f"{TILESET_DIR}/palettes/storm/{slot:02d}.pal", pal)

    with open(f"{TILESET_DIR}/metatiles.bin", "wb") as f:
        for (_, bottom, top, _) in mts:
            f.write(struct.pack("<8H", *(bottom + top)))
    with open(f"{TILESET_DIR}/metatile_attributes.bin", "wb") as f:
        for (_, _, _, beh) in mts:
            f.write(struct.pack("<H", beh | (LAYER_COVERED << 12)))

    # animation frames (one 16x16 png = 4 tiles per frame)
    for (name, frames, fn) in (("sky_a", SKY_FRAMES, lambda f: sky_frame(f)),
                               ("sky_b", SKY_FRAMES, lambda f: sky_frame(f, math.pi)),
                               ("swirl", SWIRL_FRAMES, swirl_frame),
                               ("wind_e", WIND_FRAMES, wind_h_frame),
                               ("wind_s", WIND_FRAMES, wind_v_frame)):
        d = f"{TILESET_DIR}/anim/{name}"
        os.makedirs(d, exist_ok=True)
        for fr in range(frames):
            tiles = split_tiles(fn(fr))
            # store as an 8x32 strip so gbagfx writes the 4 tiles in TL, TR, BL, BR order
            strip = [[t[y * 8 + x] for x in range(8)] for t in tiles for y in range(8)]
            write_png(f"{d}/{fr}.png", strip, PAL_SKY)

    # cloud puff sprite: 6 frames of 32x32 stacked vertically
    os.makedirs(PUFF_DIR, exist_ok=True)
    puff = []
    for fr in range(PUFF_FRAMES):
        puff.extend(puff_frame(fr))
    write_png(f"{PUFF_DIR}/trey_cloud_puff.png", puff, PAL_CLOUD)
    write_pal("graphics/field_effects/palettes/trey_cloud_puff.pal", PAL_CLOUD)
    write_pal("graphics/field_effects/palettes/trey_cloud_puff_storm.pal", PAL_CLOUD_STORM)

    # metatile ID constants
    ids = {name: 0x200 + i for i, (name, _, _, _) in enumerate(mts)}
    with open(METATILE_HEADER, "w", newline="\n") as f:
        f.write("#ifndef GUARD_CONSTANTS_TREY_SKY_METATILES_H\n#define GUARD_CONSTANTS_TREY_SKY_METATILES_H\n\n")
        f.write("// TREY: metatiles of gTileset_TreySky. Generated by tools/trey/sky_art.py --write; do not edit.\n")
        f.write("// Wall pieces with _XY suffixes are texture variants: paint them by map position (X = x % 2, Y = y % 2).\n")
        f.write("// Peaks and ridges are multi-metatile pictures: _XY is the column/row inside the picture.\n\n")
        for name, v in ids.items():
            f.write(f"#define METATILE_TreySky_{name:<22} 0x{v:03X}\n")
        f.write("\n#endif // GUARD_CONSTANTS_TREY_SKY_METATILES_H\n")

    write_test_layout(ids)
    print(f"sky_art.py: {len(sheet.tiles)} tiles, {len(mts)} metatiles written")

def write_test_layout(ids):
    """Route 101 sky test map (20x20, same size as Route 101 below it)."""
    W, H = 20, 20
    ELEV = 3
    grid = [["Sky" if (x * 7 + y * 3) % 5 else "SkyAlt" for x in range(W)] for y in range(H)]
    coll = [[0] * W for _ in range(H)]
    # storm-cloud wall around the edge (1 tile), a little thicker in two corners
    wall_cells = {(x, y) for x in range(W) for y in range(H) if x in (0, W - 1) or y in (0, H - 1)}
    wall_cells |= {(1, 1), (2, 1), (1, 2), (18, 17), (17, 18), (18, 18), (1, 17), (1, 18), (2, 18)}
    edge_solid = lambda px, py: px < 0 or py < 0 or px >= W or py >= H
    for (x, y) in wall_cells:
        key = autotile_key(wall_cells, x, y, edge_solid)
        name = "Wall_" + "".join(p.capitalize() for p in key.split("_"))
        if key == "center":
            name += f"_{x % 2}{y % 2}"
        elif key in ("n", "s"):
            name += f"_{x % 2}0"
        elif key in ("e", "w"):
            name += f"_0{y % 2}"
        grid[y][x] = name
        coll[y][x] = 1
    # a small peak and a ridge
    def place(prefix, x0, y0, w, h):
        for my in range(h):
            for mx in range(w):
                grid[y0 + my][x0 + mx] = f"{prefix}_{mx}{my}"
                coll[y0 + my][x0 + mx] = 1
    place("PeakSmall", 12, 3, 2, 2)
    place("RidgeLeft", 4, 13, 1, 2)
    place("RidgeMid", 5, 13, 1, 2)
    place("RidgeRight", 6, 13, 1, 2)
    # swirls
    for (x, y) in ((6, 5), (15, 11), (10, 16)):
        grid[y][x] = "Swirl"
    # jet stream: east along row 9, then south down column 15
    for x in range(3, 15):
        grid[9][x] = "WindEast"
    for y in range(9, 14):
        grid[y][15] = "WindSouth"
    # cloud patches (encounters)
    patches = [(3, 3), (4, 3), (5, 3), (3, 4), (4, 4), (5, 4), (4, 5),
               (8, 5), (9, 5), (8, 6), (9, 6), (10, 6),
               (2, 10), (3, 10), (2, 11), (3, 11), (4, 11), (3, 12),
               (12, 12), (13, 12), (12, 13), (13, 13), (14, 14), (13, 14),
               (16, 3), (16, 4), (17, 4), (16, 5)]
    for (x, y) in patches:
        grid[y][x] = "Cloud" + "ABC"[(x * 2 + y) % 3]
    with open(f"{LAYOUT_DIR}/map.bin", "wb") as f:
        for y in range(H):
            for x in range(W):
                f.write(struct.pack("<H", ids[grid[y][x]] | (coll[y][x] << 10) | (ELEV << 12)))
    with open(f"{LAYOUT_DIR}/border.bin", "wb") as f:
        for _ in range(4):
            f.write(struct.pack("<H", ids["Sky"] | (ELEV << 12)))

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--preview":
        make_preview(sys.argv[2])
    elif len(sys.argv) >= 2 and sys.argv[1] == "--write":
        if not os.path.exists("Makefile"):
            print("Run from the project's root folder.")
            sys.exit(1)
        write_game_files()
    else:
        print(__doc__)
