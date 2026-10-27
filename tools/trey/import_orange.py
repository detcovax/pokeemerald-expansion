#!/usr/bin/env python3
"""TREY (6c, TREY_PLAN.md D39): import the Orange Islands from the ROM hack (on FireRed 1.0) into TREY.

No source repo exists: everything is read from the patched .gba (tools/trey/orange_rom.py). Maps stay FRLG format
(D31). FireRed's own files (../pokefirered) give the tileset names and upstream's FireRed -> TREY behaviour numbers.

Steps (run from the project root):
  tilesets   the tilesets the Orange maps use: FireRed-identical ones are shared with TREY's FRLG copies, the
             others are written to data/tilesets/*/orange_*/ (tiles.png, palettes, metatiles, FRLG 32-bit attributes
             with behaviours converted exactly as upstream converted FireRed's) and src/data/tilesets/trey_orange.h.
  preview    render maps from the written files and compare them pixel for pixel with the ROM.

Options: --rom (the Orange Islands .gba, FireRed 1.0 base), --fr (a clean FireRed 1.0 .gba), --pokefirered (repo).
"""
import argparse
import collections
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orange_rom import Rom, TILESETS, fr_tileset_names  # noqa: E402

DEFAULT_ROM = "../orange islands/1636 - Pokemon Fire Red (U)(Squirrels) (patched).gba"
DEFAULT_FR = "build/fr10.gba"   # clean FireRed 1.0 (unzip "1636 - Pokemon Fire Red (U)(Squirrels).zip" there)

# D39 scope: every Orange place plus the hack's start area (Orange Pallet). Not imported: untouched Sevii leftovers.
SKIP_PLACES = {"PATTERN BUSH", "ALTERING CAVE", "MONEAN CHAMBER", "SEVII ISLE 23", "DOTTED HOLE", "TANOBY CHAMBERS",
               "SEVAULT CANYON", "TRAINER TOWER", "WATER PATH", "RUIN VALLEY"}

# FireRed tileset the hack started from -> TREY name (D39: Orange + the main place that uses it; generic names for
# tilesets the hack uses all over).
NAMES = {
    "General": "OrangeGeneral", "Building": "OrangeBuilding", "PokemonCenter": "OrangePokemonCenter",
    "SSAnne": "OrangeShowboat", "GenericBuilding2": "OrangeHouse2", "SafariZoneBuilding": "OrangeGymHall",
    "SilphCo": "OrangeOldSilph", "GenericBuilding1": "OrangeHouse1", "Mart": "OrangeMart",
    "SeafoamIslands": "OrangeAscorbiaForest", "MtEmber": "OrangeSalveyo", "ViridianForest": "OrangePark",
    "Dummy1": "OrangeRoutes", "IslandHarbor": "OrangeHarbor", "PokemonTower": "OrangeButwal",
    "ViridianCity": "OrangeValencia", "CeruleanCity": "OrangeMikan", "Lab": "OrangeLab", "ViridianGym": "OrangeSewers",
    "FuchsiaCity": "OrangeLightning", "SeviiIslands123": "OrangeIslands1", "PewterGym": "OrangeGym",
    "DepartmentStore": "OrangeTrovitoDept", "SaffronCity": "OrangeTrovita", "PewterCity": "OrangeTangelo",
    "CableClub": "OrangeCableClub", "PowerPlant": "OrangePowerPlant", "SeviiIslands67": "OrangeIslands3",
    "Museum": "OrangeMuseum", "FanClubDaycare": "OrangeDaycare", "PokemonMansion": "OrangeNewIsland",
    "CeruleanCave": "OrangeIceCave", "CeladonCity": "OrangeNavel", "HoennBuilding": "OrangeShamouti",
    "SeviiIslands45": "OrangeIslands2", "Dummy2": "OrangeUnderwater", "BikeShop": "OrangeShop",
    "HallOfFame": "OrangeHallOfFame", "Cave": "OrangeCave", "NavelRock": "OrangeLightningShrine",
    "TanobyRuins": "OrangeRuins", "LavenderTown": "OrangeMandarinNorth", "School": "OrangeSchool",
    "RestaurantHotel": "OrangeHotel", "RockTunnel": "OrangeSalveyoCave", "UndergroundPath": "OrangeShamoutiPath",
    "FuchsiaGym": "OrangeFireGym", "PalletTown": "OrangePallet", "VermilionCity": "OrangeKinnow",
    "CinnabarIsland": "OrangeYambera", "IndigoPlateau": "OrangeGolden", "UnusedGatehouse1": "OrangeNavelMountain",
    "UnusedGatehouse2": "OrangeLeagueGate", "BurgledHouse": "OrangeMikanHouse", "CeruleanGym": "OrangeMikanGym",
    "CinnabarGym": "OrangeTrovitaGym", "GameCorner": "OrangeGameCorner", "SeaCottage": "OrangeSeaCottage",
    "Condominiums": "OrangeCondominiums", "BerryForest": "OrangeBerryForest", "TrainerTower": "OrangeTrainerTower",
    "DiglettsCave": "OrangeDiglettsCave", "VermilionGym": "OrangeVermilionGym", "CeladonGym": "OrangeCeladonGym",
    "SaffronGym": "OrangeSaffronGym", "PokemonLeague": "OrangeLeague", "UnusedGatehouse": "OrangeGatehouse",
    "Dummy3": "OrangeDummy3", "Dummy4": "OrangeDummy4", "SafariZone": "OrangeSafari",
}

# Animations (6c-1, David: FRLG animation where one exists). The hack animates with its own code, which can't be
# imported; TREY's FRLG animation is used when the tiles it animates are unchanged from FireRed (checked here).
# General: water/sand unchanged, flowers repainted -> its own Orange callback without flowers (src/tileset_anims.c).
ANIMS = {"General": ("InitTilesetAnim_OrangeGeneral", [(416, 48), (464, 18)]),
         "SilphCo": ("InitTilesetAnim_SilphCo", [(976, 8)]),
         "MtEmber": ("InitTilesetAnim_MtEmber", [(896, 8)])}


def die(msg):
    sys.exit(f"import_orange.py: {msg}")


def snake(name):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()


def scope(rom):
    """(group, num) -> (header pointer, place name) of every map to import (D39)."""
    out = {}
    for k, h in rom.maps().items():
        name = rom.location_name(rom.header(h)["mapsec"])
        if name and name not in SKIP_PLACES:
            out[k] = (h, name)
    return out


def behaviour_table(pokefirered):
    """FireRed behaviour value -> TREY value, learned from upstream's own conversion of FireRed's tilesets
    (pokefirered's metatile_attributes.bin vs TREY's *_frlg copies), plus name matching for values FireRed's
    tilesets never use."""
    table = collections.defaultdict(collections.Counter)
    fr_dir, our_dir = os.path.join(pokefirered, "data/tilesets"), "data/tilesets"
    for kind in ("primary", "secondary"):
        for t in os.listdir(os.path.join(fr_dir, kind)):
            a = os.path.join(fr_dir, kind, t, "metatile_attributes.bin")
            b = os.path.join(our_dir, kind, t + "_frlg", "metatile_attributes.bin")
            if os.path.exists(a) and os.path.exists(b):
                for (x,), (y,) in zip(struct.iter_unpack("<I", open(a, "rb").read()), struct.iter_unpack("<I", open(b, "rb").read())):
                    table[x & 0x1FF][y & 0x1FF] += 1
    exact = {v: c.most_common(1)[0][0] for v, c in table.items()}
    fr_names = {int(v, 0): n for n, v in re.findall(r"^\s*#define\s+(MB_\w+)\s+(0x[0-9A-Fa-f]+|\d+)",
                open(os.path.join(pokefirered, "include/constants/metatile_behaviors.h"), encoding="utf-8").read(), re.M)}
    text = open("include/constants/metatile_behaviors.h", encoding="utf-8").read()
    ours = {n: i for i, n in enumerate(re.findall(r"^\s*(MB_\w+)", text[text.index("enum"):], re.M))}
    return exact, fr_names, ours


def convert_attributes(data, beh, where, notes):
    exact, fr_names, ours = beh
    out = bytearray()
    for (a,) in struct.iter_unpack("<I", data):
        v = a & 0x1FF
        if v in exact:
            n = exact[v]
        elif fr_names.get(v) in ours:
            n = ours[fr_names[v]]
        else:
            notes[f"{where}: unknown behaviour {v:#x} -> MB_NORMAL"] += 1
            n = 0
        out += struct.pack("<I", (a & ~0x1FF) | n)
    return bytes(out)


def write_png(path, tiles, palette):
    from PIL import Image
    n = len(tiles) // 32
    rows = (n + 15) // 16
    img = Image.new("P", (128, rows * 8))
    img.putpalette([c for rgb in palette for c in rgb] + [0] * (768 - 48))
    px = img.load()
    for i in range(n):
        b = tiles[i * 32:i * 32 + 32]
        ox, oy = (i % 16) * 8, (i // 16) * 8
        for y in range(8):
            for x in range(4):
                v = b[y * 4 + x]
                px[ox + 2 * x, oy + y] = v & 0xF
                px[ox + 2 * x + 1, oy + y] = v >> 4
    img.save(path)


def write_pal(path, pal):
    with open(path, "w", newline="\r\n") as f:
        f.write("JASC-PAL\n0100\n16\n" + "".join(f"{r} {g} {b}\n" for r, g, b in pal))


def step_tilesets(a):
    rom, fr = Rom(a.rom), Rom(a.fr)
    frnames = fr_tileset_names(os.path.join(a.pokefirered, "src/data/tilesets/headers.h"))
    def fr_index(ptr):
        i, r = divmod(ptr - 0x08000000 - TILESETS, 0x18)
        return i if r == 0 and 0 <= i < len(frnames) else None
    maps = scope(rom)
    used, maxmt = collections.Counter(), collections.Counter()
    notes = collections.Counter()
    # metatile counts: the highest metatile any hack map (in scope or not) uses with that tileset, + border blocks
    for (g, n), h in rom.maps().items():
        hd = rom.header(h)
        if not rom.isptr(hd["layout"]):
            continue
        lay = rom.layout(hd["layout"])
        if not (0 < lay["width"] < 256 and 0 < lay["height"] < 256 and rom.isptr(lay["blocks"])):
            continue
        o = rom.off(lay["blocks"])
        ids = [b & 0x3FF for b in struct.unpack_from(f"<{lay['width'] * lay['height']}H", rom.d, o)]
        if rom.isptr(lay["border"]):
            ids += [b & 0x3FF for b in struct.unpack_from(f"<{lay['border_w'] * lay['border_h']}H", rom.d, rom.off(lay["border"]))]
        for t, lo, hi in ((lay["primary"], 0, 640), (lay["secondary"], 640, 1024)):
            inside = [i - lo for i in ids if lo <= i < hi]
            if inside and fr_index(t) is not None:
                maxmt[t] = max(maxmt[t], max(inside) + 1)
        if (g, n) in maps:
            for t in (lay["primary"], lay["secondary"]):
                if fr_index(t) is not None:
                    used[t] += 1
                else:
                    notes[f"map {g}.{n}: tileset pointer {t:#x} is not a tileset (fixed in 6c-4)"] += 1
    beh = behaviour_table(a.pokefirered)
    hdr = open("src/data/tilesets/headers.h", encoding="utf-8").read()
    gfx = open("src/data/tilesets/graphics.h", encoding="utf-8").read()
    out_gfx, out_mt, out_hdr, mapping, report = [], [], [], {}, []
    for t, count in sorted(used.items(), key=lambda kv: -kv[1]):
        fn = frnames[fr_index(t)][len("gTileset_"):]
        ts, fts = rom.tileset(t), fr.tileset(t)
        prim = ts["secondary"] == 0
        tiles = rom.tileset_tiles(ts)
        nmt = maxmt[t] or (640 if prim else 384)
        mts = rom.d[rom.off(ts["metatiles"]):rom.off(ts["metatiles"]) + nmt * 16]
        attrs = rom.d[rom.off(ts["attributes"]):rom.off(ts["attributes"]) + nmt * 4]
        pals = rom.tileset_palettes(ts)
        same = False
        if fr.isptr(fts["tiles"]) and fr.isptr(fts["metatiles"]):
            try:
                same = (tiles == fr.tileset_tiles(fts) and pals == fr.tileset_palettes(fts)
                        and mts == fr.d[fr.off(fts["metatiles"]):fr.off(fts["metatiles"]) + nmt * 16]
                        and attrs == fr.d[fr.off(fts["attributes"]):fr.off(fts["attributes"]) + nmt * 4])
            except ValueError:
                same = False
        if same:
            m = re.search(r"const struct Tileset (gTileset_" + fn + r"(?:_Frlg)?)\s*=", hdr)
            if not m:
                die(f"{fn} is identical to FireRed but TREY has no FRLG copy")
            mapping[f"{t:#x}"] = m.group(1)
            report.append(f"  shared  {fn} -> {m.group(1)} ({count} maps)")
            continue
        if fn not in NAMES:
            die(f"no TREY name for the hack's {fn} tileset (add it to NAMES)")
        name = NAMES[fn]
        folder = f"data/tilesets/{'primary' if prim else 'secondary'}/{snake(name)}"
        callback = "NULL"
        if fn in ANIMS and ts["callback"]:
            cb, slots = ANIMS[fn]
            ftiles = fr.tileset_tiles(fts)
            base = 0 if prim else 640
            if all(tiles[(s - base) * 32:(s - base + k) * 32] == ftiles[(s - base) * 32:(s - base + k) * 32] for s, k in slots):
                callback = cb
            else:
                notes[f"{name}: animated tiles repainted, static"] += 1
        elif ts["callback"]:
            notes[f"{name}: custom animation, static"] += 1
        if not a.dry:
            os.makedirs(os.path.join(folder, "palettes"), exist_ok=True)
            write_png(os.path.join(folder, "tiles.png"), tiles, pals[0 if prim else 7])
            for i, p in enumerate(pals):
                write_pal(os.path.join(folder, "palettes", f"{i:02d}.pal"), p)
            open(os.path.join(folder, "metatiles.bin"), "wb").write(mts)
            open(os.path.join(folder, "metatile_attributes.bin"), "wb").write(convert_attributes(attrs, beh, name, notes))
        b = name
        out_gfx.append(f"const u32 gTilesetTiles_{b}[] = INCGFX_U32(\"{folder}/tiles.png\", \".4bpp.fastSmol\");\n"
                       f"const u16 gTilesetPalettes_{b}[][16] =\n{{\n"
                       + "".join(f"    INCGFX_U16(\"{folder}/palettes/{i:02d}.pal\", \".gbapal\"),\n" for i in range(16)) + "};\n\n")
        out_mt.append(f"const u16 gMetatiles_{b}[] = INCBIN_U16(\"{folder}/metatiles.bin\");\n"
                      f"const u16 gMetatileAttributes_{b}[] = INCBIN_U16(\"{folder}/metatile_attributes.bin\"); // FRLG 32-bit attributes\n")
        out_hdr.append(f"const struct Tileset gTileset_{b} =\n{{\n    .isCompressed = TRUE,\n    .isSecondary = {'FALSE' if prim else 'TRUE'},\n"
                       f"    .tiles = gTilesetTiles_{b},\n    .palettes = gTilesetPalettes_{b},\n"
                       f"    .metatiles = gMetatiles_{b},\n    .metatileAttributes = gMetatileAttributes_{b},\n"
                       f"    .callback = {callback},\n}};\n\n")
        mapping[f"{t:#x}"] = f"gTileset_{b}"
        report.append(f"  {'primary' if prim else 'second.'} {fn:20} -> gTileset_{b:26} {len(tiles) // 32:4} tiles {nmt:4} metatiles "
                      f"{count:3} maps{'  anim ' + callback if callback != 'NULL' else ''}")
    head = ("// TREY (6c-1): generated by tools/trey/import_orange.py from the Orange Islands ROM hack (FireRed 1.0 base).\n"
            "// FRLG format (640/7 primary, 32-bit attributes). Included at the end of src/tilesets.c. Animations: TREY's\n"
            "// FRLG ones where the animated tiles are unchanged (InitTilesetAnim_OrangeGeneral: water and sand only).\n\n"
            "void InitTilesetAnim_OrangeGeneral(void);\n\n")
    if not a.dry:
        with open("src/data/tilesets/trey_orange.h", "w", encoding="utf-8", newline="\n") as f:
            f.write(head + "".join(out_gfx) + "".join(out_mt) + "\n" + "".join(out_hdr))
        import json
        os.makedirs("docs/trey", exist_ok=True)
        with open("docs/trey/orange_tilesets.json", "w", encoding="utf-8", newline="\n") as f:
            json.dump(mapping, f, indent=2)   # ROM tileset address -> TREY tileset (used by the maps step)
    print("\n".join(report))
    for k, v in sorted(notes.items()):
        print(f"  note: {k} ({v})")
    print(f"import_orange.py tilesets: {sum(1 for r in report if 'shared' not in r)} Orange tilesets, "
          f"{sum(1 for r in report if 'shared' in r)} shared with FRLG")


# ---------------------------------------------------------------------------------------------------
# Sprites (6c-2): object event graphics. David: import every changed/new sprite (players and story cast too);
# Pokemon NPCs are switched to TREY's follower sprites in the maps step when their script names the species.
# ---------------------------------------------------------------------------------------------------
FR_GFX_TABLE, FR_PAL_TABLE = 0x39FDB0, 0x3A5158        # FireRed 1.0
GFX_TABLE_REF, PAL_TABLE_REF = 0x5F2F4, 0x5F4D8          # code words holding the table pointers (the hack repoints)
ORANGE_PAL_TAG_START = 0x1500                            # free: weather 0x1200, gates 0x1300, followers 0x4000+
SPR_MARK_BEGIN, SPR_MARK_END = "    // TREY (6c-2) BEGIN", "    // TREY (6c-2) END\n"


def gfx_table(rom, t, limit=600):
    out = []
    while len(out) < limit and rom.isptr(rom.u32(t + 4 * len(out))):
        out.append(rom.u32(t + 4 * len(out)))
    return out


def pal_table(rom, t, limit=400):
    out = {}
    for n in range(limit):
        p, tag, pad = struct.unpack_from("<IHH", rom.d, t + 8 * n)
        if not rom.isptr(p) or not 0x1100 <= tag < 0x1400:
            break
        out.setdefault(tag, p)
    return out


def gfx_info(rom, p):
    o = rom.off(p)
    tile, pal, refl, size, w, h = struct.unpack_from("<HHHHhh", rom.d, o)
    bits, tracks = rom.d[o + 12], rom.d[o + 13]
    oam, subs, anims, images, affine = struct.unpack_from("<IIIII", rom.d, o + 16)
    return {"pal": pal, "refl": refl, "size": size, "w": w, "h": h, "slot": bits & 0xF, "shadow": (bits >> 4) & 3,
            "inanimate": (bits >> 6) & 1, "tracks": tracks, "oam": oam, "subs": subs, "anims": anims, "images": images}


def frame_pixels(rom, data_ptr, w, h):
    d = rom.d[rom.off(data_ptr):rom.off(data_ptr) + w * h // 2]
    tw, px = w // 8, [0] * (w * h)
    for t in range(len(d) // 32):
        tx, ty = (t % tw) * 8, (t // tw) * 8
        for y in range(8):
            for x in range(4):
                v = d[t * 32 + y * 4 + x]
                px[(ty + y) * w + tx + 2 * x] = v & 0xF
                px[(ty + y) * w + tx + 2 * x + 1] = v >> 4
    return px


def camel_const(name):
    return "".join(p.capitalize() for p in name.lower().split("_"))


def step_sprites(a):
    from PIL import Image
    rom, fr = Rom(a.rom), Rom(a.fr)
    fr_names = {int(v): n for n, v in re.findall(r"#define OBJ_EVENT_GFX_(\w+)\s+(\d+)",
                open(os.path.join(a.pokefirered, "include/constants/event_objects.h"), encoding="utf-8").read())}
    ev = open("include/constants/event_objects.h", encoding="utf-8").read()
    ptrs = open("src/data/object_events/object_event_graphics_info_pointers.h", encoding="utf-8").read()
    infos_c = open("src/data/object_events/object_event_graphics_info.h", encoding="utf-8").read()
    anims_c = open("src/data/object_events/object_event_anims.h", encoding="utf-8").read()
    fe = gfx_table(fr, FR_GFX_TABLE)
    oe = gfx_table(rom, rom.off(rom.u32(GFX_TABLE_REF)))
    fpal, opal = pal_table(fr, FR_PAL_TABLE), pal_table(rom, rom.off(rom.u32(PAL_TABLE_REF)))

    def trey_const(i):
        n = fr_names.get(i)
        for c in (f"OBJ_EVENT_GFX_{n}_FRLG", f"OBJ_EVENT_GFX_{n}"):
            if n and re.search(r"\b" + c + r"\b", ev):
                return c
        return None
    # FireRed oam/subsprite/anim pointers -> TREY symbols, via TREY's own FRLG graphics infos
    sym = {}
    for i, p in enumerate(fe):
        c = trey_const(i)
        m = c and re.search(r"\[" + c + r"\]\s*=\s*&(\w+)", ptrs)
        body = m and re.search(r"const struct ObjectEventGraphicsInfo " + m.group(1) + r"\s*=\s*\{(.*?)\};", infos_c, re.S)
        if not body:
            continue
        g = gfx_info(fr, p)
        for field, key in (("oam", "oam"), ("subspriteTables", "subs"), ("anims", "anims")):
            fm = re.search(r"\." + field + r"\s*=\s*&?(\w+)", body.group(1))
            if fm:
                sym.setdefault((key, g[key]), fm.group(1))

    def frames_of(anim_table):
        m = re.search(r"\b" + anim_table + r"\[\]\s*=\s*\{(.*?)\};", anims_c, re.S)
        nums = []
        for seq in re.findall(r"\b(sAnim_\w+)\b", m.group(1) if m else ""):
            sm = re.search(r"\b" + seq + r"\[\]\s*=\s*\{(.*?)\};", anims_c, re.S)
            nums += [int(x) for x in re.findall(r"ANIMCMD_FRAME\((\d+)", sm.group(1) if sm else "")]
        return max(nums) + 1 if nums else 1

    def same_as_fr(i):
        if i >= len(fe):
            return False
        A, B = gfx_info(rom, oe[i]), gfx_info(fr, fe[i])
        if (A["w"], A["h"]) != (B["w"], B["h"]) or not (rom.isptr(A["images"]) and fr.isptr(B["images"])):
            return False
        fa, fb = rom.u32(rom.off(A["images"])), fr.u32(fr.off(B["images"]))
        if not (rom.isptr(fa) and fr.isptr(fb)):
            return False
        pa = opal.get(A["pal"]); pb = fpal.get(B["pal"])
        return (frame_pixels(rom, fa, A["w"], A["h"]) == frame_pixels(fr, fb, B["w"], B["h"])
                and pa and pb and rom.d[rom.off(pa):rom.off(pa) + 32] == fr.d[fr.off(pb):fr.off(pb) + 32])

    mapping, items, consts, pal_tags, notes = {}, [], [], {}, collections.Counter()
    for i, p in enumerate(oe):
        g = gfx_info(rom, p)
        if not (0 < g["w"] <= 128 and 0 < g["h"] <= 128) or not rom.isptr(g["images"]):
            notes["unreadable sprite entry skipped"] += 1
            continue
        if same_as_fr(i) and trey_const(i):
            mapping[i] = trey_const(i)
            notes["identical to FireRed (TREY's FRLG sprite)"] += 1
            continue
        base = fr_names.get(i) if i < len(fe) else None
        cname = f"OBJ_EVENT_GFX_ORANGE_{base}" if base else f"OBJ_EVENT_GFX_ORANGE_{i}"
        sname = "Orange" + (camel_const(base) if base else str(i))
        anims = sym.get(("anims", g["anims"]))
        guessed = anims is None
        if guessed:
            anims = "sAnimTable_Inanimate" if g["inanimate"] else "sAnimTable_Standard"
        oam = sym.get(("oam", g["oam"])) or f"gObjectEventBaseOam_{g['w']}x{g['h']}"
        subs = sym.get(("subs", g["subs"])) or f"sOamTables_{g['w']}x{g['h']}"
        known = (open("src/data/object_events/base_oam.h", encoding="utf-8").read()
                 + open("src/data/object_events/object_event_subsprites.h", encoding="utf-8").read())
        if not re.search(r"\b" + oam + r"\b", known) or not re.search(r"\b" + subs + r"\b", known):
            notes[f"{sname}: no {oam}/{subs} in TREY, skipped"] += 1
            continue
        nframes = frames_of(anims)
        frames = []
        for k in range(nframes):
            fp = rom.u32(rom.off(g["images"]) + 8 * k)
            if not rom.isptr(fp):
                break
            frames.append(frame_pixels(rom, fp, g["w"], g["h"]))
        if len(frames) < nframes:   # fewer frames than its animation table uses (objects): show the first, still
            anims, frames = "sAnimTable_Inanimate", frames[:1]
            notes[f"{sname}: {len(frames)} frame(s) for an {nframes}-frame animation -> inanimate"] += 1
        if g["pal"] not in pal_tags:
            pal_tags[g["pal"]] = f"OBJ_EVENT_PAL_TAG_ORANGE_{g['pal']:04X}"
        items.append((i, cname, sname, g, anims, oam, subs, frames))
        mapping[i] = cname
    if len(pal_tags) > 256:
        die(f"{len(pal_tags)} palettes, but only 256 Orange palette tags (0x1500-0x15FF)")

    out, ptr_lines, ext_lines, pal_lines = [], [], [], []
    for i, cname, sname, g, anims, oam, subs, frames in items:
        snake_name = snake(sname)
        png = f"graphics/object_events/pics/orange/{snake_name}.png"
        tw, th = g["w"] // 8, g["h"] // 8
        if not a.dry:
            os.makedirs(os.path.dirname(png), exist_ok=True)
            img = Image.new("P", (g["w"] * len(frames), g["h"]))
            pal = opal[g["pal"]]
            cols = [((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3) for c in struct.unpack_from("<16H", rom.d, rom.off(pal))]
            img.putpalette([v for c in cols for v in c] + [0] * (768 - 48))
            px = img.load()
            for k, f in enumerate(frames):
                for y in range(g["h"]):
                    for x in range(g["w"]):
                        px[k * g["w"] + x, y] = f[y * g["w"] + x]
            img.save(png)
        out.append(f"const u32 gObjectEventPic_{sname}[] = INCGFX_U32(\"{png}\", \".4bpp\", \"-mwidth {tw} -mheight {th}\");\n\n"
                   f"static const struct SpriteFrameImage sPicTable_{sname}[] = {{\n"
                   + "".join(f"    overworld_frame(gObjectEventPic_{sname}, {tw}, {th}, {k}),\n" for k in range(len(frames)))
                   + "};\n\n"
                   f"const struct ObjectEventGraphicsInfo gObjectEventGraphicsInfo_{sname} = {{TAG_NONE, {pal_tags[g['pal']]}, "
                   f"OBJ_EVENT_PAL_TAG_NONE, {g['w'] * g['h'] // 2}, {g['w']}, {g['h']}, {g['slot']}, {g['shadow']}, "
                   f"{'TRUE' if g['inanimate'] else 'FALSE'}, FALSE, {g['tracks']}, &{oam}, {subs}, {anims}, "
                   f"sPicTable_{sname}, gDummySpriteAffineAnimTable}};\n")
        ptr_lines.append(f"    [{cname}] = &gObjectEventGraphicsInfo_{sname},\n")
        ext_lines.append(f"extern const struct ObjectEventGraphicsInfo gObjectEventGraphicsInfo_{sname};\n")
        consts.append(cname)
    tag_defs = []
    for n, (hack_tag, tag) in enumerate(sorted(pal_tags.items())):
        path = f"graphics/object_events/palettes/orange/{hack_tag:04x}.pal"
        cols = [((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3)
                for c in struct.unpack_from("<16H", rom.d, rom.off(opal[hack_tag]))]
        if not a.dry:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            write_pal(path, cols)
        out.append(f"const u16 gObjectEventPal_Orange{hack_tag:04X}[] = INCGFX_U16(\"{path}\", \".gbapal\");\n")
        pal_lines.append(f"    {{gObjectEventPal_Orange{hack_tag:04X}, {tag}}},\n")
        tag_defs.append(f"#define {tag:<40} 0x{ORANGE_PAL_TAG_START + n:04X}\n")
    head = "// TREY (6c-2): generated by tools/trey/import_orange.py (sprites) from the Orange Islands ROM hack. Do not edit.\n"
    print(f"import_orange.py sprites: {len(items)} Orange sprites, {len(pal_tags)} palettes, "
          f"{sum(1 for v in mapping.values() if 'ORANGE' not in v)} shared with FRLG. "
          + ", ".join(f"{k} {v}" for k, v in sorted(notes.items())))
    if a.dry:
        return
    od = "src/data/object_events"
    open(f"{od}/trey_orange_object_events.h", "w", encoding="utf-8", newline="\n").write(
        head + "// Orange Islands sprites: pics, palettes, pic tables and graphics infos (included by event_object_movement.c).\n\n"
        + "\n".join(out))
    open(f"{od}/trey_orange_object_event_pointers.h", "w", encoding="utf-8", newline="\n").write(head + "".join(ptr_lines))
    open(f"{od}/trey_orange_object_event_externs.h", "w", encoding="utf-8", newline="\n").write(head + "".join(ext_lines))
    open(f"{od}/trey_orange_object_event_palettes.h", "w", encoding="utf-8", newline="\n").write(head + "".join(pal_lines))
    open("include/constants/trey_orange_event_object_pals.h", "w", encoding="utf-8", newline="\n").write(head + "".join(tag_defs))
    # enum entries go straight into event_objects.h between markers (preproc can't follow an #include in an enum)
    text = open("include/constants/event_objects.h", encoding="utf-8").read()
    block = (SPR_MARK_BEGIN + ": Orange Islands sprites (written by tools/trey/import_orange.py sprites)\n"
             + "".join(f"    {c},\n" for c in consts) + SPR_MARK_END)
    if SPR_MARK_BEGIN in text:
        b = text.index(SPR_MARK_BEGIN)
        e = text.index(SPR_MARK_END) + len(SPR_MARK_END)
        text = text[:b] + block + text[e:]
    else:
        anchor = "    // TREY (6a) END\n"
        text = text.replace(anchor, anchor + block, 1)
    open("include/constants/event_objects.h", "w", encoding="utf-8", newline="\n").write(text)
    import json
    json.dump({str(k): v for k, v in mapping.items()}, open("docs/trey/orange_sprites.json", "w", encoding="utf-8"), indent=1)


def step_regionmap(a):
    """6c-4a (D41): the hack's Orange region map page (tools/trey/orange_regionmap.py)."""
    import orange_regionmap
    rom = Rom(a.rom)
    report, _ = orange_regionmap.build(rom, a.dry)
    print(f"regionmap: {report['grid_cells']} grid cells, {len(report['added'])} new locations"
          + (f", {report['tiles']} tiles, {report['colours']} colours" if "tiles" in report else " (dry run)"))
    if report["stale_orange_ids"]:
        print("  Orange locations the hack doesn't use:", ", ".join(report["stale_orange_ids"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["tilesets", "sprites", "regionmap"])
    ap.add_argument("--rom", default=DEFAULT_ROM)
    ap.add_argument("--fr", default=DEFAULT_FR)
    ap.add_argument("--pokefirered", default="../pokefirered")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    if not os.path.exists("Makefile"):
        die("run from the project root")
    {"tilesets": step_tilesets, "sprites": step_sprites, "regionmap": step_regionmap}[a.step](a)


if __name__ == "__main__":
    main()
