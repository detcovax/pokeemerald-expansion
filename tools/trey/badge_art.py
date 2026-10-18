#!/usr/bin/env python3
"""TREY: Trainer Card badge sheets per region (TREY_PLAN.md 5.9, Phase 4 chunk 4e).

Run from the repo root:
    python3 tools/trey/badge_art.py --import        Johto badges from the Heart & Soul repo (../pokehns-expansion)
    python3 tools/trey/badge_art.py --placeholders  simple placeholder badges for Sinnoh and Orange
    python3 tools/trey/badge_art.py --preview DIR   a 4x preview sheet of every region's badges

Sheet format (same as graphics/trainer_card/badges.png): 128x16, 16-colour indexed PNG, badge i in x 16*i..16*i+15,
colour 0 transparent. The build makes the .4bpp.lz and .gbapal from the PNG. Kanto and Hoenn use the
existing sheets (graphics/trainer_card/frlg/badges.png and graphics/trainer_card/badges.png).
To replace a placeholder with final art, overwrite graphics/trainer_card/trey/<region>_badges.png in this format.
"""
import math
import os
import sys

from PIL import Image

OUT_DIR = "graphics/trainer_card/trey"
HNS = "../pokehns-expansion/graphics/trainer_card/hns/combined_badges.png"
SHEETS = [("KANTO", "graphics/trainer_card/frlg/badges.png", 8), ("ORANGE", OUT_DIR + "/orange_badges.png", 5),
          ("JOHTO", OUT_DIR + "/johto_badges.png", 8), ("HOENN", "graphics/trainer_card/badges.png", 8),
          ("SINNOH", OUT_DIR + "/sinnoh_badges.png", 8)]

TRANSPARENT = (136, 96, 112)
WHITE = (248, 248, 248)
OUTLINE = (40, 40, 56)


def import_johto():
    src = Image.open(HNS)
    johto = src.crop((0, 0, 128, 16))  # top row = Johto (bottom row is Kanto, which we already have)
    johto.putpalette(src.getpalette())
    os.makedirs(OUT_DIR, exist_ok=True)
    johto.save(OUT_DIR + "/johto_badges.png")
    print("badge_art.py: Johto badges imported from Heart & Soul")


# --- placeholders: plain shapes, one colour each --------------------------------------------------------------
def inside(shape, x, y):
    cx, cy = x - 7.5, y - 7.5
    r = math.hypot(cx, cy)
    a = math.atan2(cy, cx)
    if shape == "circle":
        return r <= 7
    if shape == "diamond":
        return abs(cx) + abs(cy) <= 7.5
    if shape == "hexagon":
        return abs(cy) <= 6.5 and abs(cx) * 0.58 + abs(cy) * 0.5 <= 5.2
    if shape == "square":
        return max(abs(cx), abs(cy)) <= 6 and r <= 8
    if shape == "star":
        k = (math.cos(5 * (a + math.pi / 2)) + 1) / 2
        return r <= 3.6 + 3.8 * k
    if shape == "triangle":
        return cy <= 6 and cy >= -7 and abs(cx) <= (cy + 7) * 0.55
    if shape == "octagon":
        return max(abs(cx), abs(cy)) <= 7 and abs(cx) + abs(cy) <= 10
    if shape == "drop":
        return (r <= 5.5 and cy >= -1) or (cy < -1 and abs(cx) <= (cy + 8) * 0.8)
    if shape == "shell":
        return r <= 7 and cy <= 4 or (cy > 4 and abs(cx) <= 2.5 and cy <= 7)
    if shape == "cup":
        bowl = cy <= 1 and cy >= -7 and abs(cx) <= 6 - max(0, cy + 2) * 0.9
        stem = -1 <= cx <= 1 and 1 < cy <= 5
        base = abs(cx) <= 4.5 and 5 < cy <= 7
        handles = (abs(cx) > 6 and abs(cx) <= 7.5 and -6 <= cy <= -3)
        return bowl or stem or base or handles
    raise ValueError(shape)


def make_sheet(path, badges):
    colours = [TRANSPARENT, WHITE, OUTLINE] + [c for _, c in badges]
    pal = colours + [(0, 0, 0)] * (16 - len(colours))
    im = Image.new("P", (128, 16), 0)
    flat = []
    for c in pal:
        flat += list(c)
    im.putpalette(flat + [0] * (768 - len(flat)))
    for i, (shape, _) in enumerate(badges):
        fill = 3 + i
        mask = [[inside(shape, x, y) for x in range(16)] for y in range(16)]
        for y in range(16):
            for x in range(16):
                if not mask[y][x]:
                    continue
                edge = any(not (0 <= x + dx < 16 and 0 <= y + dy < 16 and mask[y + dy][x + dx])
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                im.putpixel((16 * i + x, y), 2 if edge else fill)
        # a small highlight, top-left of the shape
        for y in range(16):
            row = [x for x in range(16) if mask[y][x] and im.getpixel((16 * i + x, y)) == fill]
            if row:
                im.putpixel((16 * i + row[0], y), 1)
                if len(row) > 2:
                    im.putpixel((16 * i + row[0] + 1, y), 1)
                break
    os.makedirs(OUT_DIR, exist_ok=True)
    im.save(path)


def placeholders():
    make_sheet(OUT_DIR + "/sinnoh_badges.png", [
        ("hexagon", (160, 112, 72)), ("circle", (88, 184, 72)), ("drop", (64, 136, 216)), ("octagon", (168, 96, 200)),
        ("diamond", (144, 152, 168)), ("triangle", (216, 64, 48)), ("square", (152, 216, 240)), ("star", (240, 200, 56)),
    ])
    make_sheet(OUT_DIR + "/orange_badges.png", [
        ("shell", (240, 136, 56)), ("shell", (240, 128, 160)), ("shell", (72, 168, 216)), ("shell", (224, 200, 112)),
        ("cup", (248, 200, 40)),  # Winner's Trophy (slot 5)
    ])
    print("badge_art.py: placeholder badges written for Sinnoh and Orange")


def preview(out_dir):
    scale = 4
    rows = []
    for name, path, count in SHEETS:
        im = Image.open(path).convert("RGBA")
        pal = Image.open(path).getpalette()
        key = tuple(pal[0:3])
        data = [(0, 0, 0, 0) if px[:3] == key else px for px in im.getdata()]
        im.putdata(data)
        rows.append((name, im.crop((0, 0, 16 * count, 16)), count))
    sheet = Image.new("RGBA", (128 * scale + 80, len(rows) * 20 * scale), (112, 192, 112, 255))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for r, (name, im, count) in enumerate(rows):
        d.text((4, r * 20 * scale + 28), name, fill=(255, 255, 255, 255))
        big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        sheet.alpha_composite(big, (76, r * 20 * scale + 8))
    os.makedirs(out_dir, exist_ok=True)
    sheet.save(os.path.join(out_dir, "trey_badges_preview.png"))
    print("badge_art.py: preview ->", os.path.join(out_dir, "trey_badges_preview.png"))


def main():
    if not os.path.exists("Makefile"):
        print("badge_art.py: run from the project's root folder.")
        return 1
    args = sys.argv[1:]
    if "--import" in args:
        import_johto()
    if "--placeholders" in args:
        placeholders()
    if "--preview" in args:
        preview(args[args.index("--preview") + 1])
    if not args:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
