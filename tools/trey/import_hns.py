#!/usr/bin/env python3
"""TREY (6a, TREY_PLAN.md D31): import Johto (and the Sinjoh Ruins) from Heart & Soul (../pokehns-expansion).

Heart & Soul keeps its own layout version "hns": FRLG-sized tilesets (640 primary tiles/metatiles, 7 palettes,
FRLG doors) with Emerald's 16-bit metatile attributes. TREY's engine knows Emerald and FRLG layouts only, so this
tool converts every imported tileset to FRLG format: the attributes become FRLG's 32-bit layout
(behaviour bits 0-8, layer type bits 29-30), and behaviours are matched BY NAME, because Heart & Soul's
behaviour numbers differ from TREY's. The border logic of "hns" layouts is FRLG's, so layouts just become "frlg".

Steps (run from the project root; --hns points at a Heart & Soul checkout or a copy of the needed files):
  tilesets   copy the tilesets the Johto/Sinjoh maps use, convert attributes, write
             src/data/tilesets/trey_hns.h (graphics, metatiles, headers) and src/data/tilesets/trey_hns_anims.h
             (tile animations, included at the end of src/tileset_anims.c).
  sprites    Johto NPC sprites (object events, palettes).
  music      HGSS/DP songs, voicegroups, key split tables and samples.
Later steps (maps, wild) are added as 6a goes on.
"""
import argparse
import json
import os
import re
import shutil
import struct
import sys

SKIP_REGIONS = {"REGION_KANTO", "REGION_ALOLA"}
KEEP_REGIONS = {"REGION_JOHTO", "REGION_HISUI"}   # Heart & Soul marks the Sinjoh Ruins as Hisui


def die(msg):
    sys.exit(f"import_hns.py: {msg}")


def read(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def behaviour_names(header):
    """enum value -> name (and name -> value) from a metatile_behaviors.h."""
    text = read(header)
    text = text[text.index("enum"):]
    names = re.findall(r"^\s*(MB_\w+)", text, re.M)
    return names, {n: i for i, n in enumerate(names)}


# ---------------------------------------------------------------------------------------------------
# Map selection (shared by every step)
# ---------------------------------------------------------------------------------------------------
def selected_maps(hns):
    ours = set(os.listdir("data/maps"))
    groups = json.load(open(os.path.join(hns, "data/maps/map_groups.json"), encoding="utf-8"))
    out = []
    for grp in groups["group_order"]:
        for m in groups[grp]:
            if m in ours and not m.endswith("_hns"):
                continue
            p = os.path.join(hns, "data/maps", m, "map.json")
            if not os.path.exists(p):
                continue
            d = json.load(open(p, encoding="utf-8"))
            if d.get("region") in KEEP_REGIONS:
                out.append((grp, m, d))
    return out


def needed_tilesets(hns, maps):
    layouts = {l["id"]: l for l in json.load(open(os.path.join(hns, "data/layouts/layouts.json"), encoding="utf-8"))["layouts"] if l}
    need = set()
    for _, _, d in maps:
        l = layouts[d["layout"]]
        need.add(l["primary_tileset"])
        need.add(l["secondary_tileset"])
    ours = read("src/data/tilesets/headers.h")
    return sorted(t for t in need if not re.search(r"const struct Tileset " + t + r"\s*=", ours))


# ---------------------------------------------------------------------------------------------------
# Tilesets
# ---------------------------------------------------------------------------------------------------
UNKNOWN_BEHAVIOURS = {}


def convert_attributes(data, hns_names, our_values, where):
    out = bytearray()
    for (attr,) in struct.iter_unpack("<H", data):
        behaviour = attr & 0x00FF
        layer = (attr & 0xF000) >> 12
        if behaviour == 0xFF:  # MB_INVALID on unused metatiles: keep it
            out += struct.pack("<I", 0xFF | (layer << 29))
            continue
        name = hns_names[behaviour] if behaviour < len(hns_names) else None
        if name is not None and name.startswith("MB_UNUSED") and name not in our_values:
            name = "MB_NORMAL"  # an unused Heart & Soul slot on some metatiles: no behaviour
        if name is None:
            UNKNOWN_BEHAVIOURS[where] = UNKNOWN_BEHAVIOURS.get(where, 0) + 1
            name = "MB_NORMAL"  # out-of-range value (unused metatile)
        if name not in our_values:
            die(f"{where}: Heart & Soul behaviour {behaviour} ({name}) has no TREY equivalent")
        out += struct.pack("<I", our_values[name] | (layer << 29))
    return bytes(out)


def step_tilesets(hns, dry):
    maps = selected_maps(hns)
    names = needed_tilesets(hns, maps)
    hdr = read(os.path.join(hns, "src/data/tilesets/headers.h"))
    gfx = read(os.path.join(hns, "src/data/tilesets/graphics.h"))
    mts = read(os.path.join(hns, "src/data/tilesets/metatiles.h"))
    hns_names, _ = behaviour_names(os.path.join(hns, "include/constants/metatile_behaviors.h"))
    _, our_values = behaviour_names("include/constants/metatile_behaviors.h")

    out_gfx, out_mt, out_hdr, callbacks = [], [], [], set()
    for t in names:
        m = re.search(r"const struct Tileset " + t + r"\s*=\s*\{(.*?)\};", hdr, re.S)
        if not m:
            die(f"{t}: not found in Heart & Soul's headers.h")
        body = m.group(1)
        field = lambda k: re.search(r"\." + k + r"\s*=\s*(\w+)", body).group(1)
        tiles, pals, metatiles, attrs, cb = field("tiles"), field("palettes"), field("metatiles"), field("metatileAttributes"), field("callback")
        secondary = field("isSecondary") == "TRUE"
        tiles_path = re.search(re.escape(tiles) + r"\[\]\s*=\s*INC\w+\(\"([^\"]+)\"", gfx).group(1)
        tdir = tiles_path.rsplit("/", 1)[0]
        pal_dir = os.path.join(hns, tdir, "palettes")
        pal_paths = [f"{tdir}/palettes/{n}" for n in sorted(os.listdir(pal_dir)) if n.endswith(".pal")]
        if len(pal_paths) < 13:  # NUM_PALS_TOTAL (13): primaries use 0-6, secondaries 7-12
            die(f"{t}: expected at least 13 .pal files in {pal_dir}, found {len(pal_paths)}")
        mt_path = re.search(re.escape(metatiles) + r"\[\]\s*=\s*INC\w+\(\"([^\"]+)\"", mts).group(1)
        at_path = re.search(re.escape(attrs) + r"\[\]\s*=\s*INC\w+\(\"([^\"]+)\"", mts).group(1)
        if os.path.exists(tdir):
            die(f"{tdir} already exists in TREY")
        if not dry:
            shutil.copytree(os.path.join(hns, tdir), tdir)
            with open(os.path.join(hns, at_path), "rb") as f:
                conv = convert_attributes(f.read(), hns_names, our_values, t)
            with open(at_path, "wb") as f:
                f.write(conv)
        base = t[len("gTileset_"):]
        out_gfx.append(f"const u32 gTilesetTiles_{base}[] = INCGFX_U32(\"{tdir}/tiles.png\", \".4bpp.fastSmol\");\n")
        out_gfx.append(f"const u16 gTilesetPalettes_{base}[][16] =\n{{\n"
                       + "".join(f"    INCGFX_U16(\"{p.rsplit('.', 1)[0]}.pal\", \".gbapal\"),\n" for p in pal_paths) + "};\n\n")
        out_mt.append(f"const u16 gMetatiles_{base}[] = INCBIN_U16(\"{mt_path}\");\n"
                      f"const u16 gMetatileAttributes_{base}[] = INCBIN_U16(\"{at_path}\"); // FRLG 32-bit attributes (converted)\n")
        if cb != "NULL":
            callbacks.add(cb)
        out_hdr.append(f"const struct Tileset {t} =\n{{\n    .isCompressed = TRUE,\n    .isSecondary = {'TRUE' if secondary else 'FALSE'},\n"
                       f"    .tiles = gTilesetTiles_{base},\n    .palettes = gTilesetPalettes_{base},\n"
                       f"    .metatiles = gMetatiles_{base},\n    .metatileAttributes = gMetatileAttributes_{base},\n"
                       f"    .callback = {cb},\n}};\n\n")

    head = ("// TREY (6a): generated by tools/trey/import_hns.py from Heart & Soul. Johto/Sinjoh tilesets, converted to\n"
            "// FRLG format (640/7 primary, 32-bit attributes). Included at the end of src/tilesets.c.\n\n")
    decls = "".join(f"void {cb}(void);\n" for cb in sorted(callbacks))
    text = head + decls + "\n" + "".join(out_gfx) + "".join(out_mt) + "\n" + "".join(out_hdr)
    if not dry:
        with open("src/data/tilesets/trey_hns.h", "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        write_anims(hns, callbacks, names)
    if UNKNOWN_BEHAVIOURS:
        print("  out-of-range behaviours set to MB_NORMAL:", ", ".join(f"{k} {v}" for k, v in sorted(UNKNOWN_BEHAVIOURS.items())))
    print(f"import_hns.py tilesets: {len(names)} tilesets, {len(callbacks)} animations: {', '.join(sorted(callbacks))}")


def split_items(block):
    """Top-level C items (functions, arrays, declarations), each with its text."""
    items, cur, depth = [], [], 0
    for line in block.split("\n"):
        cur.append(line)
        depth += line.count("{") - line.count("}")
        s = line.strip()
        if depth == 0 and (s.endswith(";") or s == "}" or s.startswith("#") or s.startswith("//") or s == ""):
            items.append("\n".join(cur))
            cur = []
    if cur:
        items.append("\n".join(cur))
    return items


def write_anims(hns, callbacks, tilesets):
    """Copy Heart & Soul's Johto tileset animations (the IS_HNS block of its tileset_anims.c), keeping only the
    animations of tilesets we import."""
    src = read(os.path.join(hns, "src/tileset_anims.c"))
    start = src.index("#if IS_HNS")
    end = src.index("#endif // IS_HNS", start)
    block = src[start + len("#if IS_HNS"):end]
    keep = {cb[len("InitTilesetAnim_"):] for cb in callbacks}
    drop = set(re.findall(r"InitTilesetAnim_(\w+)\s*\(void\)", block)) - keep
    out = [it for it in split_items(block) if not any(re.search(r"\b\w*" + re.escape(n) + r"\w*\b", it) for n in drop)]
    # Frame data of tilesets we don't import (e.g. HnS's Kanto fountains, whose callbacks live outside the IS_HNS
    # block): drop items that INCBIN from a tileset folder we didn't copy, then anything that uses what was dropped.
    imported = {d for d in (os.path.join("data/tilesets", k, n) for k in ("primary", "secondary")
                            for n in (os.listdir(os.path.join("data/tilesets", k)) if os.path.isdir(os.path.join("data/tilesets", k)) else []))}
    def missing_dir(it):
        for p in re.findall(r'INCBIN_\w+\("(data/tilesets/(?:primary|secondary)/[^/"]+)/', it):
            if p not in imported:
                return True
        return False
    gone = set()
    while True:
        bad = [it for it in out if missing_dir(it) or any(re.search(r"\b" + re.escape(s) + r"\b", it) for s in gone)]
        if not bad:
            break
        for it in bad:
            gone.update(re.findall(r"^\s*(?:static\s+)?(?:const\s+)?[\w\s\*]*?\b(\w+)\s*(?:\[[^\]]*\])*\s*=", it, re.M))
            gone.update(re.findall(r"^\s*(?:static\s+)?void\s+(\w+)\s*\(", it, re.M))
        out = [it for it in out if it not in bad]
    head = ("// TREY (6a): generated by tools/trey/import_hns.py from Heart & Soul's tileset_anims.c (its IS_HNS block).\n"
            "// Included at the end of src/tileset_anims.c. Imported tilesets are FRLG format, so secondaries start at tile 640.\n"
            "#define sSecondaryTilesetBaseTile NUM_TILES_IN_PRIMARY_FRLG\n")
    with open("src/data/tilesets/trey_hns_anims.h", "w", encoding="utf-8", newline="\n") as f:
        f.write(head + "\n".join(out) + "\n#undef sSecondaryTilesetBaseTile\n")
    print("  animations dropped (tilesets not imported):", ", ".join(sorted(drop)))



# ---------------------------------------------------------------------------------------------------
# Sprites (NPC object events)
# ---------------------------------------------------------------------------------------------------
OBJ_FILES = ["src/data/object_events/object_event_graphics.h", "src/data/object_events/object_event_pic_tables.h",
             "src/data/object_events/object_event_anims.h", "src/data/object_events/object_event_subsprites.h",
             "src/data/object_events/object_event_graphics_info.h",
             "src/data/field_effects/field_effect_objects.h", "src/data/field_effects/field_effect_object_template_pointers.h"]
DEF_RE = re.compile(r"^(?:static )?(?:const )?(?:union |struct )?\w+(?: \*const| const|\s*\*)*\s*(\w+)\s*(?:\[\w*\])*\s*=", re.M)


def c_items(text):
    """name -> full text of every top-level definition 'TYPE NAME[...] = ...;' in a C data file."""
    items = {}
    for m in DEF_RE.finditer(text):
        start = m.start()
        depth, i = 0, m.end()
        while i < len(text):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            elif ch == ";" and depth == 0:
                break
            i += 1
        items.setdefault(m.group(1), text[start:i + 1])
    return items


def step_sprites(hns, dry):
    maps = selected_maps(hns)
    ours_ev = read("include/constants/event_objects.h")
    used = {e["graphics_id"] for _, _, d in maps for e in d.get("object_events", [])}
    need = sorted(g for g in used if "MON_BASE" not in g and not re.search(r"\b" + g + r"\b", ours_ev))
    ptr = read(os.path.join(hns, "src/data/object_events/object_event_graphics_info_pointers.h"))
    hitems = {}
    for f in OBJ_FILES:
        if os.path.exists(os.path.join(hns, f)):
            hitems.update(c_items(read(os.path.join(hns, f))))
    oitems = set()
    for f in OBJ_FILES + ["src/data/object_events/object_event_graphics_info_followers.h", "src/data/object_events/base_oam.h"]:
        if os.path.exists(f):
            oitems |= set(c_items(read(f)))
    hns_ev = read(os.path.join(hns, "include/constants/event_objects.h"))

    order, seen = [], set()
    def visit(name):
        if name in seen or name in oitems or name not in hitems:
            return
        seen.add(name)
        for tok in set(re.findall(r"\b[A-Za-z_]\w*\b", hitems[name])) - {name}:
            visit(tok)
        order.append(name)
    infos = {}
    for g in need:
        m = re.search(r"\[" + g + r"\]\s*=\s*&(\w+)", ptr)
        if not m:
            die(f"{g}: no graphics info in Heart & Soul's pointer table")
        infos[g] = m.group(1)
        visit(m.group(1))

    pal_tags = sorted({t for n in order for t in re.findall(r"\bOBJ_EVENT_PAL_TAG_\w+", hitems[n]) if not re.search(r"\b" + t + r"\b", ours_ev)})
    pal_defs = []
    for t in pal_tags:
        m = re.search(r"#define\s+" + t + r"\s+(0x[0-9A-Fa-f]+|\d+)", hns_ev)
        if not m:
            die(f"{t}: not defined in Heart & Soul's event_objects.h")
        pal_defs.append((t, m.group(1)))
    # palettes for those tags (Heart & Soul's sObjectEventSpritePalettes)
    mv = read(os.path.join(hns, "src/event_object_movement.c"))
    pal_entries = []
    for t, _ in pal_defs:
        m = re.search(r"\{\s*(gObjectEventPal_\w+)\s*,\s*" + t + r"\s*\}", mv)
        if not m:
            die(f"{t}: no palette entry in Heart & Soul's sObjectEventSpritePalettes")
        pal_entries.append((m.group(1), t))
        visit(m.group(1))

    # image files and conversion args: INCBIN .4bpp -> INCGFX with the frame size its pic table uses
    frame_size = {}
    for n in order:
        for pic, w, h in re.findall(r"overworld_(?:frame|ascending_frames)\((\w+),\s*(\d+),\s*(\d+)", hitems[n]):
            frame_size[pic] = (w, h)
    files, out = [], []
    for n in order:
        text = hitems[n]
        m = re.search(r"INCBIN_(U\d+)\(\"([^\"]+)\.(4bpp|gbapal)\"\)", text)
        if m:
            kind, base, ext = m.groups()
            if ext == "4bpp":
                w, h = frame_size.get(n, (None, None))
                args = f", \"-mwidth {w} -mheight {h}\"" if w else ""
                text = text.replace(m.group(0), f"INCGFX_{kind}(\"{base}.png\", \".4bpp\"{args})")
                files.append(base + ".png")
            else:
                text = text.replace(m.group(0), f"INCGFX_{kind}(\"{base}.pal\", \".gbapal\")")
                files.append(base + ".pal")
        for p in re.findall(r"INCGFX_\w+\(\"([^\"]+)\"", text):
            files.append(p)
        out.append(text)

    missing = [f for f in files if not os.path.exists(os.path.join(hns, f))]
    if missing:
        die("missing image files in Heart & Soul: " + ", ".join(missing[:10]))
    if not dry:
        for f in sorted(set(files)):
            os.makedirs(os.path.dirname(f), exist_ok=True)
            if os.path.exists(f):
                die(f"{f} already exists in TREY")
            shutil.copy2(os.path.join(hns, f), f)
        head = "// TREY (6a): generated by tools/trey/import_hns.py from Heart & Soul. Do not edit.\n"
        with open("src/data/object_events/trey_hns_object_events.h", "w", encoding="utf-8", newline="\n") as f:
            f.write(head + "// Johto NPC sprites: pics, palettes, pic tables, anims and graphics infos (included by event_object_movement.c).\n\n"
                    + "\n\n".join(out) + "\n")
        with open("src/data/object_events/trey_hns_object_event_pointers.h", "w", encoding="utf-8", newline="\n") as f:
            f.write(head + "".join(f"    [{g}] = &{infos[g]},\n" for g in need))
        with open("src/data/object_events/trey_hns_object_event_externs.h", "w", encoding="utf-8", newline="\n") as f:
            f.write(head + "".join(f"extern const struct ObjectEventGraphicsInfo {infos[g]};\n" for g in need))
        with open("src/data/object_events/trey_hns_object_event_palettes.h", "w", encoding="utf-8", newline="\n") as f:
            f.write(head + "".join(f"    {{{p}, {t}}},\n" for p, t in pal_entries))
        # The enum entries go straight into event_objects.h between the TREY (6a) markers: scripts read the enum
        # through preproc, which doesn't follow an #include inside an enum.
        ev = read("include/constants/event_objects.h")
        b = ev.index("    // TREY (6a) BEGIN")
        e = ev.index("    // TREY (6a) END\n") + len("    // TREY (6a) END\n")
        block = ("    // TREY (6a) BEGIN: Johto NPC sprites from Heart & Soul (written by tools/trey/import_hns.py sprites)\n"
                 + "".join(f"    {g},\n" for g in need) + "    // TREY (6a) END\n")
        with open("include/constants/event_objects.h", "w", encoding="utf-8", newline="\n") as f:
            f.write(ev[:b] + block + ev[e:])
        with open("include/constants/trey_hns_event_object_pals.h", "w", encoding="utf-8", newline="\n") as f:
            f.write(head + "".join(f"#define {t:<44} {v}\n" for t, v in pal_defs))
    print(f"import_hns.py sprites: {len(need)} sprites, {len(order)} data items, {len(set(files))} image files, {len(pal_defs)} palette tags")


# ---------------------------------------------------------------------------------------------------
# Music (HGSS and DP songs, their voicegroups, key split tables and samples)
# ---------------------------------------------------------------------------------------------------
MUSIC_MARK = "TREY (6a): HGSS/DP music from Heart & Soul"


def splice_once(path, anchor, text, after=True):
    s = read(path)
    if MUSIC_MARK in s:
        return False
    if s.count(anchor) != 1:
        die(f"{path}: anchor not found once: {anchor!r}")
    i = s.index(anchor) + (len(anchor) if after else 0)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(s[:i] + text + s[i:])
    return True


def between(text, start, end):
    i = text.index(start)
    return text[i:text.index(end, i)]


def step_music(hns, dry):
    """Copy every Heart & Soul song we don't have (mus_hg_*, mus_dp_*): midis and their midi.cfg lines, song ids
    (after the phoneme songs, so no existing id moves), song table rows, voicegroups 191-273, key split tables
    5-58 and the samples they use. The HQ mixer the songs were arranged for is ported by hand (src/m4a*.s/c)."""
    hmid, mid = os.path.join(hns, "sound/songs/midi"), "sound/songs/midi"
    new = sorted(set(f for f in os.listdir(hmid) if f.endswith(".mid")) - set(os.listdir(mid)))
    if not new:
        die("no new songs (already imported?)")
    cfg = {l.split(":")[0]: l for l in read(os.path.join(hmid, "midi.cfg")).splitlines() if ":" in l}
    vgs = sorted(f for f in os.listdir(os.path.join(hns, "sound/voicegroups")) if re.fullmatch(r"voicegroup\d+\.inc", f))
    vgs = [f for f in vgs if not os.path.exists(os.path.join("sound/voicegroups", f))]

    # song ids: Heart & Soul's HG/DP block, moved after our last phoneme song
    hsongs = read(os.path.join(hns, "include/constants/songs.h"))
    hg = between(hsongs, "#define HG_MUSIC_START", "#define DP_MUSIC_START")
    dp = between(hsongs, "#define DP_MUSIC_START", "#define END_MUS")
    hg = hg.replace("(MUS_RG_TEACHY_TV_MENU + 1)", "(PH_NURSE_SOLO + 1)")
    ids = f"\n// {MUSIC_MARK} (tools/trey/import_hns.py music). After the phoneme songs so no id moves.\n" + hg + dp
    have = set(re.findall(r"#define\s+(MUS_\w+)", ids))
    if len([n for n in have if n.startswith(("MUS_HG_", "MUS_DP_"))]) != len(new):
        die(f"{len(new)} new midis but {len(have)} song ids")

    # song table rows: Heart & Soul's HGSS and DP blocks
    htable = read(os.path.join(hns, "sound/song_table.inc"))
    rows = between(htable, "\t@ HGSS Music\n", "\t@ Phoneme songs")
    table = f"\n\t@ {MUSIC_MARK}\n" + rows.rstrip() + "\n"
    if len(re.findall(r"^\s*song mus_(?:hg|dp)_", rows, re.M)) != len(new):
        die("song table rows don't match the midis")

    # voicegroups, key split tables, samples
    hvg = read(os.path.join(hns, "sound/voice_groups.inc"))
    vg_inc = f"\n@ {MUSIC_MARK}\n" + "".join(l + "\n" for l in hvg.splitlines() if re.search(r'voicegroups/voicegroup\d+\.inc"', l)
                                              and re.search(r"voicegroup\d+\.inc", l).group(0) in vgs)
    hks = read(os.path.join(hns, "sound/keysplit_tables.inc")).splitlines()
    ours_ks = read("sound/keysplit_tables.inc").splitlines()
    first = next(i for i, l in enumerate(hks) if l.startswith(".set KeySplitTable"))
    last = max(i for i, l in enumerate(hks) if l.startswith("keysplit french_horn"))   # a repeat of ours at the end
    ks = f"\n@ {MUSIC_MARK}\n" + "\n".join(hks[first:last]).rstrip() + "\n"
    hds = read(os.path.join(hns, "sound/direct_sound_data.inc"))
    ours_ds = read("sound/direct_sound_data.inc")
    ours_labels = set(re.findall(r"^(DirectSoundWaveData_\w+)::", ours_ds, re.M))
    samples, ds = [], [f"\n@ {MUSIC_MARK}\n"]
    for m in re.finditer(r'^(\s*\.align 2\s*\n)?(DirectSoundWaveData_\w+)::\s*\n\s*\.incbin "([^"]+)"\s*\n', hds, re.M):
        if m.group(2) in ours_labels:
            continue
        samples.append(m.group(3))
        ds.append(f"\t.align 2\n{m.group(2)}::\n\t.incbin \"{m.group(3)}\"\n")
    ds = "".join(ds)

    # every symbol the new voicegroups use must now exist
    vg_text = "".join(read(os.path.join(hns, "sound/voicegroups", f)) for f in vgs)
    defined = (set(re.findall(r"^(\w+)::", ours_ds + ds + read("sound/programmable_wave_data.inc"), re.M))
               | set(re.findall(r"^\.set (\w+),", ks, re.M))
               | {"keysplit_" + n for n in re.findall(r"^keysplit (\w+),", "\n".join(ours_ks), re.M)}
               | {f[:-4] for f in vgs} | set(re.findall(r"^(\w+)::", hvg + read("sound/voice_groups.inc"), re.M)))
    for f in os.listdir("sound/voicegroups"):
        if f.endswith(".inc"):
            defined |= set(re.findall(r"^(\w+)::", read(os.path.join("sound/voicegroups", f)), re.M))
    for d in ("drumsets", "keysplits"):
        for f in os.listdir(os.path.join("sound/voicegroups", d)):
            defined |= set(re.findall(r"^(\w+)::", read(os.path.join("sound/voicegroups", d, f)), re.M))
    used = set(re.findall(r"\b((?:DirectSoundWaveData|ProgrammableWaveData|KeySplitTable|voicegroup|keysplit)_?\w+)", vg_text))
    missing = sorted(u for u in used if u not in defined)
    if missing:
        die("voicegroups use undefined symbols: " + ", ".join(missing[:40]))
    wavs = [p[:-4] + ".wav" for p in samples]
    for w in wavs:
        if not os.path.exists(os.path.join(hns, w)):
            die(f"missing sample {w}")

    print(f"import_hns.py music: {len(new)} songs, {len(vgs)} voicegroups, {len(samples)} samples")
    if dry:
        return
    for f in new:
        shutil.copy2(os.path.join(hmid, f), os.path.join(mid, f))
    for f in vgs:
        shutil.copy2(os.path.join(hns, "sound/voicegroups", f), os.path.join("sound/voicegroups", f))
    for w in wavs:
        shutil.copy2(os.path.join(hns, w), w)
    with open(os.path.join(mid, "midi.cfg"), "a", encoding="utf-8", newline="\n") as f:
        f.write("".join(cfg[n] + "\n" for n in new))
    splice_once("include/constants/songs.h", "#define PH_NURSE_SOLO               609\n", ids)
    splice_once("sound/song_table.inc", "\tsong ph_nurse_solo, MUSIC_PLAYER_SE2, 2\n", table)
    splice_once("sound/keysplit_tables.inc", read("sound/keysplit_tables.inc").rstrip("\n") + "\n", ks)
    with open("sound/direct_sound_data.inc", "a", encoding="utf-8", newline="\n") as f:
        f.write(ds)
    s = read("sound/voice_groups.inc")
    if MUSIC_MARK not in s:
        with open("sound/voice_groups.inc", "a", encoding="utf-8", newline="\n") as f:
            f.write(vg_inc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["tilesets", "sprites", "music"])
    ap.add_argument("--hns", default="../pokehns-expansion")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not os.path.exists("Makefile"):
        die("run from the project's root folder")
    if a.step == "tilesets":
        step_tilesets(a.hns, a.dry_run)
    elif a.step == "sprites":
        step_sprites(a.hns, a.dry_run)
    elif a.step == "music":
        step_music(a.hns, a.dry_run)


if __name__ == "__main__":
    main()
