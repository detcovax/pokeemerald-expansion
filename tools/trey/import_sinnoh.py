#!/usr/bin/env python3
"""TREY (6b, TREY_PLAN.md D33): import Sinnoh from the Sinnoh repo (../Sinnoh-pokeemerald-expansion).

The Sinnoh repo is pokeemerald-expansion 1.17.0 with Emerald-format maps. It repainted Hoenn's own tilesets in place
(the General primary and about ten secondaries) and added new ones, so every Sinnoh tileset is imported under a
Sinnoh name (TILESETS below: repo name -> TREY name). Its behaviour numbers are expansion's, the same as TREY's
except for slots that are unused upstream and taken by TREY, which no Sinnoh metatile uses (checked), so the
attribute files are copied unchanged.

How each tileset comes in (decided per file, by comparing with TREY's Hoenn copy):
  full     new folder with tiles, palettes, metatiles, attributes (repainted or new tilesets)
  meta     new folder with metatiles + attributes only; tiles and palettes are TREY's Hoenn ones (unchanged)
  pal      new folder with palettes only; tiles, metatiles and attributes are TREY's Hoenn ones
  shared   identical to TREY's Hoenn tileset: the Sinnoh maps use the Hoenn tileset itself
Animations: every animated Sinnoh tileset uses Hoenn's animation frames unchanged, so the Hoenn callbacks are reused.

Steps (run from the project root; --sinnoh points at a Sinnoh repo checkout or a copy of the needed files):
  tilesets   copy the Sinnoh tilesets, write src/data/tilesets/trey_sinnoh.h (included at the end of src/tilesets.c)
  music      DPPt songs TREY lacks (36), the sinnoh_gm voicegroup, song ids and table rows (D34)
  preview    render maps from the repo's layouts with the imported tilesets: --maps Twinleaf,... --out DIR
"""
import argparse
import filecmp
import json
import os
import re
import shutil
import struct
import sys

# Repo tileset -> TREY tileset (D33: Sinnoh + the area where it's used). Tilesets not listed here are shared.
TILESETS = {
    "gTileset_General": "gTileset_SinnohGeneral",            # primary of every outdoor/cave map
    "gTileset_Building": "gTileset_SinnohBuilding",          # primary of every indoor map
    "gTileset_Petalburg": "gTileset_SinnohTwinleaf",         # Twinleaf, Sandgem, Routes 201/202/219-221, Verity
    "gTileset_Rustboro": "gTileset_SinnohJubilife",          # Jubilife, Routes 203/204
    "gTileset_Jubilife": "gTileset_SinnohOreburgh",          # Oreburgh, Eterna, Routes 205N/207/211W/218, mine
    "gTileset_Mauville": "gTileset_SinnohFloaroma",          # Floaroma, Routes 205S/208/228, Valley Windworks
    "gTileset_Lilycove": "gTileset_SinnohPastoria",          # Pastoria, Route 212
    "gTileset_EverGrande": "gTileset_SinnohLeague",          # Pokemon League, Route 224
    "gTileset_Lavaridge": "gTileset_SinnohStark",            # Route 227 (toward Stark Mountain)
    "gTileset_LilycoveMuseum": "gTileset_SinnohOldChateau",  # Old Chateau entrance
    "gTileset_Cave": "gTileset_SinnohCave",                  # Oreburgh Gate/Mine, Ravaged Path, Mt. Coronet
    "gTileset_GenericBuilding": "gTileset_SinnohGenericBuilding",
    "gTileset_Shop": "gTileset_SinnohShop",
    "gTileset_BikeShop": "gTileset_SinnohCycleShop",         # Eterna Cycle Shop, Valley Windworks inside
    "gTileset_Canalave": "gTileset_SinnohCanalave",
    "gTileset_Celestic": "gTileset_SinnohCelestic",          # Solaceon, Celestic, Routes 209/210/211E/215
    "gTileset_Hearthome": "gTileset_SinnohHearthome",
    "gTileset_Pasos": "gTileset_SinnohGate",                 # route gates, Hotel Grand Lake
    "gTileset_Snowpoint": "gTileset_SinnohSnowpoint",        # Snowpoint, Routes 216/217, Acuity
    "gTileset_Sunnyshore": "gTileset_SinnohSunyshore",       # Sunyshore, Routes 206/223
    "gTileset_Valor": "gTileset_SinnohValor",                # Routes 213/214/222/225/226/229/230, Valor, Battle Zone
    "gTileset_Veilstone": "gTileset_SinnohVeilstone",
}
SINNOH_GROUPS = 10  # the first ten groups of the repo's map_groups.json are Sinnoh's (159 maps)
NUM_PALS_IN_PRIMARY = 6
NUM_PALS_TOTAL = 13


def die(msg):
    sys.exit(f"import_sinnoh.py: {msg}")


def read(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def snake(name):
    """gTileset_SinnohGeneral -> sinnoh_general"""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name[len("gTileset_"):]).lower()


def short(name):
    return name[len("gTileset_"):]


# ---------------------------------------------------------------------------------------------------
# Map selection
# ---------------------------------------------------------------------------------------------------
def sinnoh_maps(src):
    groups = json.load(open(os.path.join(src, "data/maps/map_groups.json"), encoding="utf-8"))
    return [(g, m) for g in groups["group_order"][:SINNOH_GROUPS] for m in groups[g]]


def repo_layouts(src):
    return {l["id"]: l for l in json.load(open(os.path.join(src, "data/layouts/layouts.json"), encoding="utf-8"))["layouts"] if l and "id" in l}


# ---------------------------------------------------------------------------------------------------
# Tilesets
# ---------------------------------------------------------------------------------------------------
def tileset_info(src_root, name):
    """Folder, tiles INCGFX arguments, secondary flag and callback of a tileset, read from a repo's C files."""
    hdr = read(os.path.join(src_root, "src/data/tilesets/headers.h"))
    gfx = read(os.path.join(src_root, "src/data/tilesets/graphics.h")) + read(os.path.join(src_root, "src/graphics.c"))
    m = re.search(r"const struct Tileset " + name + r"\s*=\s*\{(.*?)\};", hdr, re.S)
    if not m:
        return None
    body = m.group(1)
    field = lambda k: re.search(r"\." + k + r"\s*=\s*(\w+)", body).group(1)
    tiles = field("tiles")
    t = re.search(re.escape(tiles) + r"\[\]\s*=\s*INCGFX_U32\(\"([^\"]+)/tiles\.png\"((?:\s*,\s*\"[^\"]*\")*)\)", gfx)
    if not t:
        die(f"{name}: tiles {tiles} not found")
    return {"dir": t.group(1), "gfx_args": t.group(2), "secondary": field("isSecondary") == "TRUE",
            "callback": field("callback"), "seasonal": re.search(r"\.seasonal\s*=\s*(\w+)", body)}


def same(a, b):
    return os.path.exists(a) and os.path.exists(b) and filecmp.cmp(a, b, shallow=False)


def classify(src, name):
    """full / meta / pal / shared, by comparing the repo's files with TREY's tileset of the same name."""
    ri = tileset_info(src, name)
    ti = tileset_info(".", name)
    if ti is None or ti["dir"] != ri["dir"]:
        return "full", ri, ti
    s, t = os.path.join(src, ri["dir"]), ti["dir"]
    tiles = same(f"{s}/tiles.png", f"{t}/tiles.png")
    meta = same(f"{s}/metatiles.bin", f"{t}/metatiles.bin") and same(f"{s}/metatile_attributes.bin", f"{t}/metatile_attributes.bin")
    pals = all(same(f"{s}/palettes/{i:02d}.pal", f"{t}/palettes/{i:02d}.pal") for i in range(16))
    if tiles and meta and pals:
        return "shared", ri, ti
    if tiles and pals:
        return "meta", ri, ti
    if tiles and meta:
        return "pal", ri, ti
    return "full", ri, ti


def needed_tilesets(src):
    layouts = repo_layouts(src)
    need = set()
    for _, m in sinnoh_maps(src):
        d = json.load(open(os.path.join(src, "data/maps", m, "map.json"), encoding="utf-8"))
        l = layouts[d["layout"]]
        need.update((l["primary_tileset"], l["secondary_tileset"]))
    return sorted(need)


def step_tilesets(src, dry):
    names = needed_tilesets(src)
    unknown = [n for n in names if n not in TILESETS and classify(src, n)[0] != "shared"]
    if unknown:
        die(f"changed or new tilesets without a TREY name (add them to TILESETS): {', '.join(unknown)}")
    gfx, mts, hdrs, report = [], [], [], []
    for n in names:
        kind, ri, ti = classify(src, n)
        if kind == "shared":
            report.append(f"  shared  {n}")
            continue
        new = TILESETS[n]
        base, tdir = short(new), f"data/tilesets/{'secondary' if ri['secondary'] else 'primary'}/{snake(new)}"
        sdir = os.path.join(src, ri["dir"])
        hoenn = short(n)
        if os.path.exists(tdir) and not dry:
            shutil.rmtree(tdir)
        if not dry:
            os.makedirs(tdir)
        if kind in ("full", "pal"):
            if not dry:
                shutil.copytree(os.path.join(sdir, "palettes"), f"{tdir}/palettes",
                                ignore=shutil.ignore_patterns("*.gbapal"))
            pal_names = sorted(p for p in os.listdir(os.path.join(sdir, "palettes")) if p.endswith(".pal"))
            if len(pal_names) < NUM_PALS_TOTAL:
                die(f"{n}: expected at least {NUM_PALS_TOTAL} palettes, found {len(pal_names)}")
            gfx.append(f"const u16 gTilesetPalettes_{base}[][16] =\n{{\n"
                       + "".join(f"    INCGFX_U16(\"{tdir}/palettes/{p}\", \".gbapal\"),\n" for p in pal_names) + "};\n\n")
            pals = f"gTilesetPalettes_{base}"
        else:
            pals = f"gTilesetPalettes_{hoenn}"
        if kind == "full":
            if not dry:
                shutil.copy(f"{sdir}/tiles.png", f"{tdir}/tiles.png")
            gfx.append(f"const u32 gTilesetTiles_{base}[] = INCGFX_U32(\"{tdir}/tiles.png\"{ri['gfx_args']});\n\n")
            tiles = f"gTilesetTiles_{base}"
        else:
            tiles = f"gTilesetTiles_{hoenn}"
        if kind in ("full", "meta"):
            if not dry:
                shutil.copy(f"{sdir}/metatiles.bin", f"{tdir}/metatiles.bin")
                shutil.copy(f"{sdir}/metatile_attributes.bin", f"{tdir}/metatile_attributes.bin")
            mts.append(f"const u16 gMetatiles_{base}[] = INCBIN_U16(\"{tdir}/metatiles.bin\");\n"
                       f"const u16 gMetatileAttributes_{base}[] = INCBIN_U16(\"{tdir}/metatile_attributes.bin\");\n")
            meta, attrs = f"gMetatiles_{base}", f"gMetatileAttributes_{base}"
        else:
            meta, attrs = f"gMetatiles_{hoenn}", f"gMetatileAttributes_{hoenn}"
        hdrs.append(f"const struct Tileset {new} =\n{{\n    .isCompressed = TRUE,\n"
                    f"    .isSecondary = {'TRUE' if ri['secondary'] else 'FALSE'},\n"
                    f"    .tiles = {tiles},\n    .palettes = {pals},\n"
                    f"    .metatiles = {meta},\n    .metatileAttributes = {attrs},\n"
                    f"    .callback = {ri['callback']},\n}};\n\n")
        report.append(f"  {kind:6}  {n} -> {new} ({tdir})")
    head = ("// TREY (6b): generated by tools/trey/import_sinnoh.py from the Sinnoh repo; do not edit by hand\n"
            "// (tools/trey/season_art.py adds the .seasonal lines). Included at the end of src/tilesets.c.\n"
            "// Animated tilesets reuse Hoenn's callbacks: their frames are unchanged in the Sinnoh repo.\n\n")
    text = head + "".join(gfx) + "".join(mts) + "\n" + "".join(hdrs)
    if not dry:
        with open("src/data/tilesets/trey_sinnoh.h", "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("  re-run tools/trey/season_art.py --write afterwards: it adds the .seasonal lines")
    print("\n".join(report))
    print(f"import_sinnoh.py tilesets: {sum(1 for r in report if 'shared' not in r)} Sinnoh tilesets, "
          f"{sum(1 for r in report if 'shared' in r)} shared with Hoenn")


# ---------------------------------------------------------------------------------------------------
# Music (6b-3, D34)
# ---------------------------------------------------------------------------------------------------
# Repo songs TREY already has from Heart & Soul (kept, D33/D34): repo song -> TREY song.
MUSIC_DUPLICATES = {"mus_dpp_mt_coronet": "MUS_DP_MT_CORONET", "mus_dpp_snowpoint": "MUS_DP_SNOWPOINT_DAY",
                    "mus_dpp_route216": "MUS_DP_ROUTE216_DAY"}
MUSIC_MARK = "TREY (6b-3): DPPt music from the Sinnoh repo"


def splice_after(path, anchor, text):
    body = read(path)
    if MUSIC_MARK in body:
        die(f"{path} already has the Sinnoh music (remove the block to re-import)")
    i = body.index(anchor) + len(anchor)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(body[:i] + text + body[i:])


def step_music(src, dry):
    """Copy the repo's mus_dpp_* songs TREY lacks: midis, midi.cfg lines, the sinnoh_gm voicegroup, song ids
    (a DPP block after DP_MUSIC_END, so no id moves) and song table rows (after mus_dp_stark_mountain).
    Every sample and keysplit table sinnoh_gm uses is already in TREY (checked 2026-10-26)."""
    smid, mid = os.path.join(src, "sound/songs/midi"), "sound/songs/midi"
    table = read(os.path.join(src, "sound/song_table.inc"))
    songs = [s for s in re.findall(r"^\s*song (mus_dpp_\w+),", table, re.M) if s not in MUSIC_DUPLICATES]
    have = [s for s in songs if os.path.exists(f"{mid}/{s}.mid")]
    if have:
        die(f"already imported: {', '.join(have)}")
    cfg = {l.split(":")[0]: l for l in read(os.path.join(smid, "midi.cfg")).splitlines() if ":" in l}
    missing = [s for s in songs if f"{s}.mid" not in cfg]
    if missing:
        die(f"no midi.cfg line for {', '.join(missing)}")
    rows = {m.group(1): m.group(0).strip() for m in re.finditer(r"^\s*song (mus_dpp_\w+),.*$", table, re.M)}
    width = max(len(s) for s in songs) + 2
    ids = (f"\n\n// {MUSIC_MARK} (tools/trey/import_sinnoh.py music). After the HGSS/DP blocks so no id moves.\n"
           f"#define DPP_MUSIC_START              (DP_MUSIC_END + 1)\n"
           + "".join(f"#define {s.upper():<{width + 2}} (DPP_MUSIC_START + 0x{i:02X})\n" for i, s in enumerate(songs))
           + f"#define DPP_MUSIC_END                {songs[-1].upper()}")
    rowtext = f"\n\t@ {MUSIC_MARK}\n" + "".join(f"\t{rows[s]}\n" for s in songs)
    cfgtext = "".join(cfg[f"{s}.mid"].rstrip() + "\n" for s in songs)
    if not dry:
        for s in songs:
            shutil.copy(f"{smid}/{s}.mid", f"{mid}/{s}.mid")
        shutil.copy(os.path.join(src, "sound/voicegroups/sinnoh_gm.inc"), "sound/voicegroups/sinnoh_gm.inc")
        with open(f"{mid}/midi.cfg", "a", encoding="utf-8", newline="\n") as f:
            f.write(cfgtext)
        splice_after("include/constants/songs.h", "#define DP_MUSIC_END                 MUS_DP_STARK_MOUNTAIN", ids)
        splice_after("sound/song_table.inc", "\tsong mus_dp_stark_mountain, MUSIC_PLAYER_BGM, 0\n", rowtext)
        vg = read("sound/voice_groups.inc").rstrip("\n").splitlines()
        last = max(i for i, l in enumerate(vg) if l.startswith(".include \"sound/voicegroups/"))
        vg.insert(last + 1, '.include "sound/voicegroups/sinnoh_gm.inc" @ TREY (6b-3)')
        with open("sound/voice_groups.inc", "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(vg) + "\n")
    print(f"import_sinnoh.py music: {len(songs)} songs (skipped, already in TREY: {', '.join(MUSIC_DUPLICATES)})")


# ---------------------------------------------------------------------------------------------------
# Preview: render maps from the repo's layouts with the imported (TREY-side) tilesets
# ---------------------------------------------------------------------------------------------------
def trey_tileset_files(name):
    """tiles.png, palettes dir, metatiles.bin of a TREY tileset, read from trey_sinnoh.h or the Hoenn files."""
    text = read("src/data/tilesets/trey_sinnoh.h") + read("src/data/tilesets/headers.h")
    body = re.search(r"const struct Tileset " + name + r"\s*=\s*\{(.*?)\};", text, re.S).group(1)
    field = lambda k: re.search(r"\." + k + r"\s*=\s*(\w+)", body).group(1)
    all_c = read("src/data/tilesets/trey_sinnoh.h") + read("src/data/tilesets/graphics.h") + read("src/graphics.c") + read("src/data/tilesets/metatiles.h")
    path = lambda sym, what: re.search(re.escape(sym) + r"\[\]\s*(?:\[16\])?\s*=\s*(?:\{\s*)?INC\w+\(\"([^\"]+)/" + what, all_c).group(1)
    return path(field("tiles"), "tiles.png"), path(field("palettes"), "palettes/"), path(field("metatiles"), "metatiles.bin")


def load_ts(name, season=None):
    from PIL import Image
    tdir, pdir, mdir = trey_tileset_files(name)
    im = Image.open(f"{tdir}/tiles.png")
    px, (w, h) = im.load(), im.size
    tiles = [[px[tx * 8 + x, ty * 8 + y] & 0xF for y in range(8) for x in range(8)] for ty in range(h // 8) for tx in range(w // 8)]
    def pal(i):
        p = f"{pdir}/seasons/{season}/{i:02d}.pal" if season and season != "summer" else f"{pdir}/palettes/{i:02d}.pal"
        if not os.path.exists(p):
            p = f"{pdir}/palettes/{i:02d}.pal"
        if not os.path.exists(p):
            return [(0, 0, 0)] * 16  # tilesets with only 13 palettes
        lines = [l.strip() for l in read(p).splitlines() if l.strip()]
        start = 3 if lines[0] == "JASC-PAL" else 4
        return [tuple((int(v) >> 3) << 3 for v in l.split()[:3]) for l in lines[start:start + 16]]
    data = open(f"{mdir}/metatiles.bin", "rb").read()
    return {"tiles": tiles, "pals": [pal(i) for i in range(16)],
            "metatiles": [struct.unpack_from("<8H", data, i * 16) for i in range(len(data) // 16)]}


def render(src, layout, season=None):
    from PIL import Image
    sec_name = TILESETS.get(layout["secondary_tileset"], layout["secondary_tileset"])
    if season and not os.path.isdir(f"{trey_tileset_files(sec_name)[1]}/seasons"):
        season = None  # src/trey_seasons.c: no seasonal secondary (Snowpoint) -> base art all over
    prim = load_ts(TILESETS.get(layout["primary_tileset"], layout["primary_tileset"]), season)
    sec = load_ts(sec_name, season)
    w, h = layout["width"], layout["height"]
    blocks = struct.unpack(f"<{w * h}H", open(os.path.join(src, layout["blockdata_filepath"]), "rb").read()[:w * h * 2])
    pals = prim["pals"][:NUM_PALS_IN_PRIMARY] + sec["pals"][NUM_PALS_IN_PRIMARY:NUM_PALS_TOTAL]
    img = Image.new("RGB", (w * 16, h * 16))
    out = img.load()
    for i, block in enumerate(blocks):
        mid = block & 0x3FF
        mtl = prim["metatiles"] if mid < 512 else sec["metatiles"]
        if mid % 512 >= len(mtl):
            continue
        mt = mtl[mid % 512]
        bx, by = (i % w) * 16, (i // w) * 16
        for layer in range(2):
            for k in range(4):
                e = mt[layer * 4 + k]
                t, hf, vf, p = e & 0x3FF, (e >> 10) & 1, (e >> 11) & 1, e >> 12
                tl = prim["tiles"] if t < 512 else sec["tiles"]
                tile = tl[t % 512] if t % 512 < len(tl) else [0] * 64
                ox, oy = bx + (k % 2) * 8, by + (k // 2) * 8
                for y in range(8):
                    for x in range(8):
                        c = tile[(7 - y if vf else y) * 8 + (7 - x if hf else x)]
                        if c == 0 and layer == 1:
                            continue
                        if p < len(pals):
                            out[ox + x, oy + y] = pals[p][c] if c else pals[0][0]
    return img


def step_preview(src, maps, outdir, seasons):
    layouts = repo_layouts(src)
    os.makedirs(outdir, exist_ok=True)
    for m in maps:
        d = json.load(open(os.path.join(src, "data/maps", m, "map.json"), encoding="utf-8"))
        lay = layouts[d["layout"]]
        for s in seasons:
            img = render(src, lay, s)
            p = f"{outdir}/{m}_{s}.png"
            img.save(p)
            print("preview:", p)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["tilesets", "music", "preview"])
    ap.add_argument("--sinnoh", default="../Sinnoh-pokeemerald-expansion")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--maps", default="TwinleafTown,JubilifeCity,HearthomeCity,SnowpointCity,Route210_South")
    ap.add_argument("--seasons", default="summer")
    ap.add_argument("--out", default="build/trey_preview")
    a = ap.parse_args()
    if not os.path.exists("Makefile"):
        die("run from the project's root folder")
    if a.step == "tilesets":
        step_tilesets(a.sinnoh, a.dry)
    elif a.step == "music":
        step_music(a.sinnoh, a.dry)
    else:
        step_preview(a.sinnoh, a.maps.split(","), a.out, a.seasons.split(","))


if __name__ == "__main__":
    main()
