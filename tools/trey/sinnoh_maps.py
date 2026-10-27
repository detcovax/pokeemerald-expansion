"""TREY (6b-4, TREY_PLAN.md D33/D36/D37): the "maps" step of tools/trey/import_sinnoh.py.

Copies the Sinnoh repo's 159 maps into TREY, with import_frlg.py's event rules (as Johto did):

  names     a few repo typos fixed (RENAME); local IDs get a map prefix (they are global constants).
  layouts   copied (Emerald format); tilesets renamed to the Sinnoh tilesets of 6b-1.
  groups    compact (D36): Sinnoh_Outdoor, _Dungeon, _Indoor_Routes, _Indoor_South/North/East.
  events    kept: signs, talk-only NPCs, nurses, clerks, item balls, hidden items. Dropped: trainers, triggers,
            story objects and scripts, Twinleaf's Mom (D37). The repo REUSES Hoenn's item flags, so every item
            ball and hidden item gets its own FLAG_SINNOH_* flag (include/constants/trey_sinnoh_flags.h).
  shells    towns without interiors get a Pokemon Center (nurse) and a Mart (full DPPt stock, D37), using the
            repo's Jubilife layouts, wired to the doors drawn on the town, plus a heal location (D33).
  closed    every door, ladder or stair tile with no warp (missing interiors, the three doors into Hoenn maps,
            entrances to places not built yet) becomes impassable and says "(Not built yet.)" (D37).
  music     DPPt songs per map (MUSIC), night versions for Snowpoint, Routes 216/217, Acuity (D34).
  ferry     Canalave's ferry sailor (TRANSIT_STOP_CANALAVE, D33).

Run through tools/trey/import_sinnoh.py maps (needs pokeemerald.map: build the ROM once first).
Story is written by hand later; after that, don't re-run this step over edited maps.
"""
import collections
import json
import os
import re
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_frlg  # noqa: E402

SINNOH_GROUPS = 10
ITEM_FLAG_SLOTS = 512   # TREY_FLAG_SINNOH_ITEMS_COUNT in include/constants/flags.h
NOT_BUILT = "TreySinnoh_EventScript_NotBuiltYet"

RENAME = {
    "PokmonLeague": "SinnohPokemonLeague",
    "FloaromaTwon_PokemonCenter_2F": "FloaromaTown_PokemonCenter_2F",
    "TwinleafTown_Haouse1": "TwinleafTown_House1",
    "Twinleaf_Town_RivalsHouse_F1": "TwinleafTown_RivalsHouse_1F",
    "Twinleaf_Town_RivalsHouse_F2": "TwinleafTown_RivalsHouse_2F",
    "ValleyWindoworks_Indoor": "ValleyWindworks_Inside",
}
MAPSEC = {"MAPSEC_POKEMON_LEAGUE": "MAPSEC_SINNOH_POKEMON_LEAGUE", "MAPSEC_LITTLEROOT_TOWN": "MAPSEC_TWINLEAF_TOWN"}
MAP_TYPE = {"SinnohPokemonLeague": "MAP_TYPE_TOWN", "FloaromaMeadow": "MAP_TYPE_ROUTE"}   # other MAP_TYPE_NONE -> INDOOR
DROP_OBJECTS = {"TwinleafTown_MainHouse_1F_EventScript_Mom"}   # D37

GROUP_OF_REPO_GROUP = {
    "gMapGroup_SinnohTownsRoutes": "gMapGroup_Sinnoh_Outdoor",
    "gMapGroup_SpecialAreasSinnoh": "gMapGroup_Sinnoh_Outdoor",
    "gMapGroup_DungeonsSinnoh": "gMapGroup_Sinnoh_Dungeon",
    "gMapGroup_IndoorSinnoh": "gMapGroup_Sinnoh_Indoor_Routes",
    "gMapGroup_IndoorTwinleaf": "gMapGroup_Sinnoh_Indoor_South",
    "gMapGroup_IndoorSandgem": "gMapGroup_Sinnoh_Indoor_South",
    "gMapGroup_IndoorJubilife": "gMapGroup_Sinnoh_Indoor_South",
    "gMapGroup_IndoorOreburgh": "gMapGroup_Sinnoh_Indoor_South",
    "gMapGroup_IndoorFloaroma": "gMapGroup_Sinnoh_Indoor_South",
    "gMapGroup_IndoorEterna": "gMapGroup_Sinnoh_Indoor_North",
}
GROUP_ORDER = ["gMapGroup_Sinnoh_Outdoor", "gMapGroup_Sinnoh_Dungeon", "gMapGroup_Sinnoh_Indoor_Routes",
               "gMapGroup_Sinnoh_Indoor_South", "gMapGroup_Sinnoh_Indoor_North", "gMapGroup_Sinnoh_Indoor_East"]

# Shell towns (D33): (town map, PC door, Mart door or None, indoor group). Doors found by the PC/Mart door
# metatiles of the shared primary (0x61 / 0x41) and checked on the placement preview; Snowpoint's PC uses the
# Mart door tile, so its doors are given by hand.
SHELLS = [
    ("HearthomeCity",       (14, 19), (27, 30), "gMapGroup_Sinnoh_Indoor_North"),
    ("SolaceonTown",        (24, 24), (29, 33), "gMapGroup_Sinnoh_Indoor_North"),
    ("CelesticTown",        (27, 27), None,     "gMapGroup_Sinnoh_Indoor_North"),
    ("SnowpointCity",       (29, 45), (3, 44),  "gMapGroup_Sinnoh_Indoor_North"),
    ("CanalaveCity",        (28, 22), (24, 39), "gMapGroup_Sinnoh_Indoor_South"),
    ("VeilstoneCity",       (41, 36), None,     "gMapGroup_Sinnoh_Indoor_East"),   # its Mart is the Department Store (locked)
    ("PastoriaCity",        (26, 14), (27, 43), "gMapGroup_Sinnoh_Indoor_East"),
    ("SunyshoreCity",       (32, 42), (25, 30), "gMapGroup_Sinnoh_Indoor_East"),
    ("SinnohPokemonLeague", (11, 58), None,     "gMapGroup_Sinnoh_Indoor_East"),
    ("FightArea",           (39, 14), (55, 23), "gMapGroup_Sinnoh_Indoor_East"),
    ("SurvivalArea",        (17, 18), (23, 18), "gMapGroup_Sinnoh_Indoor_East"),
    ("ResortArea",          (9, 10),  None,     "gMapGroup_Sinnoh_Indoor_East"),
]
PC_TEMPLATE, MART_TEMPLATE = "JubilifeCity_PokemonCenter_1F", "JubilifeCity_Mart"
FULL_STOCK = ["ITEM_POKE_BALL", "ITEM_GREAT_BALL", "ITEM_ULTRA_BALL", "ITEM_POTION", "ITEM_SUPER_POTION",
              "ITEM_HYPER_POTION", "ITEM_MAX_POTION", "ITEM_FULL_RESTORE", "ITEM_REVIVE", "ITEM_ANTIDOTE",
              "ITEM_PARALYZE_HEAL", "ITEM_AWAKENING", "ITEM_BURN_HEAL", "ITEM_ICE_HEAL", "ITEM_FULL_HEAL",
              "ITEM_ESCAPE_ROPE", "ITEM_REPEL", "ITEM_SUPER_REPEL", "ITEM_MAX_REPEL"]

# Canalave ferry (D33): the sailor stands on the canal pier; arriving passengers step off beside it.
FERRY = {"map": "CanalaveCity", "sailor": (14, 46), "facing": "MOVEMENT_TYPE_FACE_LEFT", "arrive": (13, 46)}
TWINLEAF_START = ("TwinleafTown", "MAP_TWINLEAF_TOWN_MAIN_HOUSE_1F")   # debug warp: in front of this door

# DPPt music (D34). Maps not listed keep the repo's song; repo songs TREY took from Heart & Soul are renamed.
MUSIC_RENAME = {"MUS_DPP_ROUTE216": "MUS_DP_ROUTE216_DAY", "MUS_DPP_SNOWPOINT": "MUS_DP_SNOWPOINT_DAY",
                "MUS_DPP_MT_CORONET": "MUS_DP_MT_CORONET", "MUS_POKE_MART": "MUS_HG_POKE_MART", "MUS_GYM": "MUS_HG_GYM",
                "MUS_POKE_CENTER": None, "MUS_RG_POKE_CENTER": None, "MUS_LITTLEROOT_TEST": "MUS_DPP_TWINLEAF"}
MUSIC = {   # nearest DPPt song TREY has (approximations are listed in docs/trey/sinnoh_import_report.txt)
    "Route206": "MUS_DPP_ROUTE205", "Route207": "MUS_DPP_ROUTE205", "Route208": "MUS_DPP_ROUTE205",
    "Route209": "MUS_DPP_ROUTE205", "Route212_North": "MUS_DPP_ROUTE210", "Route212_South": "MUS_DPP_ROUTE210",
    "Route219": "MUS_DPP_ROUTE210", "Route220": "MUS_DPP_ROUTE210", "Route221": "MUS_DPP_ROUTE210",
    "Route222": "MUS_DPP_ROUTE210", "Route225": "MUS_DPP_ROUTE210", "Route226": "MUS_DPP_ROUTE213",
    "Route227": "MUS_DPP_ROUTE210", "Route228": "MUS_DPP_ROUTE210", "Route229": "MUS_DPP_ROUTE213",
    "Route230": "MUS_DPP_ROUTE213", "AcuityLakefront": "MUS_DP_ROUTE216_DAY", "ValorLakefront": "MUS_DPP_ROUTE213",
    "CelesticTown": "MUS_DPP_ETERNA", "FightArea": "MUS_DPP_SUNYSHORE", "SurvivalArea": "MUS_DPP_SUNYSHORE",
    "ResortArea": "MUS_DPP_SUNYSHORE", "OreburghGate_1F": "MUS_DP_MT_CORONET", "OreburghMine_B1F": "MUS_DP_MT_CORONET",
    "OreburghMine_B2F": "MUS_DP_MT_CORONET", "RavagedPath": "MUS_DP_MT_CORONET", "HotelGrandLake": "MUS_DPP_ROUTE213",
    "ValleyWindworks_Inside": "MUS_DPP_ROUTE205",
}
NIGHT_MUSIC = {"SnowpointCity": "MUS_DP_SNOWPOINT_NIGHT", "Route216": "MUS_DP_ROUTE216_NIGHT",
               "Route217": "MUS_DP_ROUTE216_NIGHT", "AcuityLakefront": "MUS_DP_ROUTE216_NIGHT"}
CLOSED_BEHAVIOURS = re.compile(r"^MB_(?!INDOOR_ENCOUNTER).*DOOR$|^MB_LADDER$|^MB_\w*STAIR_WARP$")


def die(msg):
    sys.exit(f"import_sinnoh.py maps: {msg}")


def jload(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def jsave(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def const_name(name):
    """TwinleafTown_MainHouse_1F -> TWINLEAF_TOWN_MAIN_HOUSE_1F (no split inside "1F", "Route201")."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", name).upper()


class SinnohImport(import_frlg.MapImport):
    """import_frlg's rules with Emerald's nurse script (the repo is Emerald-format)."""

    def decide_object(self, o, kept_ids, required, final=False):
        script = o.get("script", "0x0")
        if script in DROP_OBJECTS:
            self.notes["dropped (D37)"] += 1
            return False
        if script in self.blocks and self.reaches_cmd(script, "call", "Common_EventScript_PkmnCenterNurse") is not None:
            lid = o.get("local_id") or f"LOCALID_{const_name(self.name)}_NURSE"
            o["local_id"] = lid
            self.notes["nurse"] += 1
            return self.nurse_script(lid)
        return super().decide_object(o, kept_ids, required, final)

    def new_label(self, base):
        lab = f"{self.name}_TreyEventScript_{base}"
        n = 2
        while lab in self.blocks or lab in self.ctx.used_new:
            lab = f"{self.name}_TreyEventScript_{base}{n}"
            n += 1
        self.ctx.used_new.add(lab)
        return lab


class SinnohCtx(import_frlg.Ctx):
    def item_flag(self, flag):
        if not flag.startswith("FLAG_SINNOH_"):
            die(f"item flag {flag} was not renamed")
        if flag not in self.flags:
            self.flags[flag] = len(self.flags)
        return flag


# ---------------------------------------------------------------------------------------------------
# Tiles: door behaviours of a layout (for closed doors)
# ---------------------------------------------------------------------------------------------------
def behaviour_table():
    text = open("include/constants/metatile_behaviors.h", encoding="utf-8").read()
    return re.findall(r"^\s*(MB_\w+)", text[text.index("enum"):], re.M)


def tileset_attrs(name, cache):
    """Behaviour byte of every metatile of a TREY tileset (Emerald 16-bit attributes)."""
    if name in cache:
        return cache[name]
    text = "".join(open(f, encoding="utf-8").read() for f in
                   ("src/data/tilesets/headers.h", "src/data/tilesets/trey_sinnoh.h", "src/data/tilesets/metatiles.h"))
    body = re.search(r"const struct Tileset " + name + r"\s*=\s*\{(.*?)\};", text, re.S).group(1)
    sym = re.search(r"\.metatileAttributes\s*=\s*(\w+)", body).group(1)
    path = re.search(re.escape(sym) + r"\[\]\s*=\s*INCBIN_U16\(\"([^\"]+)\"", text).group(1)
    cache[name] = [a & 0xFF for (a,) in struct.iter_unpack("<H", open(path, "rb").read())]
    return cache[name]


# ---------------------------------------------------------------------------------------------------
# Main step
# ---------------------------------------------------------------------------------------------------
def step_maps(src, dry, tilesets_map):
    if not os.path.exists("pokeemerald.map"):
        die("build the ROM once first (pokeemerald.map lists the labels TREY has)")
    sgroups = jload(os.path.join(src, "data/maps/map_groups.json"))
    slayouts = {l["id"]: l for l in jload(os.path.join(src, "data/layouts/layouts.json"))["layouts"] if l and "id" in l}
    groups = jload("data/maps/map_groups.json")
    if any(g.startswith("gMapGroup_Sinnoh_") for g in groups["group_order"]):
        die("Sinnoh maps are already imported (remove the gMapGroup_Sinnoh_* groups to re-import)")
    layouts = jload("data/layouts/layouts.json")
    our_layout_ids = {l["id"] for l in layouts["layouts"] if l}
    our_maps = set(os.listdir("data/maps"))
    behaviours = behaviour_table()
    attr_cache = {}

    # 1. maps, new names, ids
    maps = collections.OrderedDict()
    for g in sgroups["group_order"][:SINNOH_GROUPS]:
        for m in sgroups[g]:
            maps[m] = (g, jload(os.path.join(src, "data/maps", m, "map.json")))
    new_name = {m: RENAME.get(m, m) for m in maps}
    id_map = {d["id"]: "MAP_" + const_name(new_name[m]) for m, (_, d) in maps.items()}
    layout_map = {d["layout"]: "LAYOUT_" + const_name(new_name[m]) for m, (_, d) in maps.items()}
    for n in new_name.values():
        if n in our_maps:
            die(f"{n} already exists in data/maps")
    for lid in layout_map.values():
        if lid in our_layout_ids:
            die(f"{lid} already exists in layouts.json")
    shell_maps = {}
    for town, pc, mart, grp in SHELLS:
        shell_maps[f"{town}_PokemonCenter_1F"] = (town, "pc", pc, grp)
        if mart:
            shell_maps[f"{town}_Mart"] = (town, "mart", mart, grp)
    for n in shell_maps:
        if n in our_maps or n in new_name.values():
            die(f"{n} already exists")
        id_map["MAP_" + const_name(n)] = "MAP_" + const_name(n)

    label_prefix = {m: new_name[m] for m in maps if m != new_name[m]}

    def ren_text(text, lids):
        def sub(mt):
            tok = mt.group(0)
            if tok in id_map:
                return id_map[tok]
            if tok in layout_map:
                return layout_map[tok]
            if tok in lids:
                return lids[tok]
            for old, new in label_prefix.items():
                if tok.startswith(old + "_"):
                    return new + tok[len(old):]
            return tok
        return re.sub(r"\b[A-Za-z_]\w*\b", sub, text)

    items = set(re.findall(r"^\s*(ITEM_\w+)\s*=", open("include/constants/items.h", encoding="utf-8").read(), re.M))
    tm = open("include/constants/tms_hms.h", encoding="utf-8").read()
    for kind in ("TM", "HM"):
        mm = re.search(r"#define FOREACH_" + kind + r"\(F\)(.*?)\n\n", tm, re.S)
        if mm:
            items |= {f"ITEM_{kind}_{x}" for x in re.findall(r"F\((\w+)\)", mm.group(1))}

    # 2. heal locations: the repo's (Sandgem..Eterna) + one per shell town PC
    heal_json = jload("src/data/heal_locations.json")
    our_heal_ids = {h["id"] for h in heal_json["heal_locations"]}
    new_heal = []
    for h in jload(os.path.join(src, "src/data/heal_locations.json"))["heal_locations"]:
        if h["map"] in id_map and h["map"] in {d["id"] for _, d in maps.values()}:
            h = dict(h, map=id_map[h["map"]])
            if h.get("respawn_map") in id_map:
                h["respawn_map"] = id_map[h["respawn_map"]]
            h.pop("respawn_npc", None)   # filled in below from the kept nurse
            new_heal.append(h)
    shell_heal = {}
    for town, pc, mart, grp in SHELLS:
        hid = "HEAL_LOCATION_" + const_name(town)
        shell_heal[town] = hid
        new_heal.append({"id": hid, "map": "MAP_" + const_name(town), "x": pc[0], "y": pc[1] + 1,
                         "respawn_map": "MAP_" + const_name(f"{town}_PokemonCenter_1F"),
                         "respawn_npc": f"LOCALID_{const_name(town + '_PokemonCenter_1F')}_NURSE"})
    for h in new_heal:
        if h["id"] in our_heal_ids:
            die(f"{h['id']} already exists in heal_locations.json")

    global_labels = import_frlg.load_global_labels("pokeemerald.map")
    ctx = SinnohCtx(global_labels, {"Common_EventScript_FindItem"}, our_heal_ids | {h["id"] for h in new_heal}, set())

    # 3. warps into maps that aren't imported (the three Hoenn doors) are removed; keep the others' indices right
    keep_warp = {}
    for m, (_, d) in maps.items():
        idx, k = {}, 0
        for i, w in enumerate(d.get("warp_events") or []):
            if w["dest_map"] in id_map or w["dest_map"] == "MAP_DYNAMIC":
                idx[i] = k
                k += 1
        keep_warp[d["id"]] = idx

    out_maps, report, totals = collections.OrderedDict(), [], collections.Counter()
    new_layouts = collections.OrderedDict()
    item_names = collections.Counter()
    for m, (g, d) in maps.items():
        name = new_name[m]
        cname = const_name(name)
        notes = collections.Counter()
        d = json.loads(json.dumps(d))
        old_id = d["id"]
        d["id"], d["name"], d["layout"] = id_map[old_id], name, layout_map[d["layout"]]
        d["region"] = "REGION_SINNOH"
        d["region_map_section"] = MAPSEC.get(d["region_map_section"], d["region_map_section"])
        if d["map_type"] == "MAP_TYPE_NONE":
            d["map_type"] = MAP_TYPE.get(name, "MAP_TYPE_INDOOR")
            notes[f"map type -> {d['map_type']}"] += 1
        music = MUSIC.get(name)
        if music is None:
            music = MUSIC_RENAME.get(d["music"], d["music"])
            if music is None:   # gates and other borrowed Pokemon Center songs: the route's song (set below)
                music = "ROUTE"
        d["music"] = music
        if name in NIGHT_MUSIC:
            d["trey_night_music"] = NIGHT_MUSIC[name]
        d.setdefault("floor_number", 0)
        conns = [dict(c, map=id_map[c["map"]]) for c in d.get("connections") or [] if c["map"] in id_map]
        d["connections"] = conns or None
        warps = []
        for i, w in enumerate(d.get("warp_events") or []):
            if w["dest_map"] == "MAP_DYNAMIC":
                warps.append(w)
            elif w["dest_map"] in id_map:
                new = keep_warp[w["dest_map"]].get(int(w["dest_warp_id"]), 0)
                warps.append(dict(w, dest_map=id_map[w["dest_map"]], dest_warp_id=str(new)))
            else:
                notes["warp into Hoenn removed (door closed)"] += 1
        d["warp_events"] = warps
        # local ids become map-prefixed constants; item flags become FLAG_SINNOH_*
        lids = {}
        for o in d.get("object_events") or []:
            if o.get("local_id"):
                old = o["local_id"]
                lids[old] = f"LOCALID_{cname}_{old[len('LOCALID_'):]}"
                o["local_id"] = lids[old]
            if o.get("graphics_id") == "OBJ_EVENT_GFX_ITEM_BALL" and o.get("script") == "Common_EventScript_FindItem":
                it = str(o.get("trainer_sight_or_berry_tree_id"))
                base = f"FLAG_SINNOH_ITEM_{cname}_{it[len('ITEM_'):]}"
                item_names[base] += 1
                o["flag"] = base if item_names[base] == 1 else f"{base}_{item_names[base]}"
        objs = []
        for o in d.get("object_events") or []:
            it = str(o.get("trainer_sight_or_berry_tree_id"))
            if o.get("graphics_id") == "OBJ_EVENT_GFX_ITEM_BALL" and it.startswith("ITEM_") and it not in items:
                notes[f"item ball dropped ({it} not in TREY)"] += 1
                continue
            objs.append(o)
        d["object_events"] = objs
        bgs = []
        for b in d.get("bg_events") or []:
            if b.get("type") == "hidden_item":
                if b["item"] not in items:
                    notes[f"hidden item dropped ({b['item']} not in TREY)"] += 1
                    continue
                base = f"FLAG_SINNOH_HIDDEN_{cname}_{b['item'][len('ITEM_'):]}"
                item_names[base] += 1
                b["flag"] = base if item_names[base] == 1 else f"{base}_{item_names[base]}"
            bgs.append(b)
        d["bg_events"] = bgs
        sp = os.path.join(src, "data/maps", m, "scripts.inc")
        scripts = open(sp, encoding="utf-8").read() if os.path.exists(sp) else f"{m}_MapScripts::\n\t.byte 0\n"
        scripts = ren_text(scripts, lids)
        for key in ("object_events", "bg_events"):
            for e in d.get(key) or []:
                if e.get("script"):
                    e["script"] = ren_text(e["script"], lids)
        imp = SinnohImport(name, d, scripts, ctx)
        text = imp.run()
        text = text.replace("@ TREY (5a): generated by tools/trey/import_frlg.py from upstream's",
                            "@ TREY (6b-4): generated by tools/trey/import_sinnoh.py (maps) from the Sinnoh repo's")
        text = text.replace("FRLG story scripts", "Sinnoh repo story scripts")
        notes.update(imp.notes)
        group = GROUP_OF_REPO_GROUP[g]
        out_maps[name] = [group, imp.j, text, m]
        report.append((name, notes))
        sl = slayouts[maps[m][1]["layout"]]
        lid = layout_map[sl["id"]]
        if lid not in new_layouts:
            new_layouts[lid] = (sl, name)

    # 4. gates and other maps that borrowed a Pokemon Center song: play their route's song
    def route_music(name):
        mm = re.match(r"Route(\d+)", name)
        if mm:
            for cand in (f"Route{mm.group(1)}", f"Route{mm.group(1)}_South", f"Route{mm.group(1)}_North",
                         f"Route{mm.group(1)}_West", f"Route{mm.group(1)}_East"):
                if cand in out_maps and out_maps[cand][1]["music"] != "ROUTE":
                    return out_maps[cand][1]["music"]
        return "MUS_DPP_POKECENTER"
    for name, v in out_maps.items():
        if v[1]["music"] == "ROUTE":
            v[1]["music"] = route_music(name)

    # 5. shell towns: Pokemon Center + Mart, door warps, heal locations
    tmpl = {k: jload(os.path.join(src, "data/maps", k, "map.json")) for k in (PC_TEMPLATE, MART_TEMPLATE)}
    for town, pc, mart, grp in SHELLS:
        t = out_maps[town][1]
        for kind, door in (("pc", pc), ("mart", mart)):
            if door is None:
                continue
            iname = f"{town}_PokemonCenter_1F" if kind == "pc" else f"{town}_Mart"
            icname = const_name(iname)
            src_map = tmpl[PC_TEMPLATE if kind == "pc" else MART_TEMPLATE]
            town_warp = len(t["warp_events"])
            t["warp_events"].append({"x": door[0], "y": door[1], "elevation": 0,
                                     "dest_map": "MAP_" + icname, "dest_warp_id": "0"})
            j = {"id": "MAP_" + icname, "name": iname, "layout": layout_map[src_map["layout"]],
                 "music": "MUS_DPP_POKECENTER" if kind == "pc" else "MUS_HG_POKE_MART",
                 "region_map_section": t["region_map_section"], "requires_flash": False, "weather": "WEATHER_NONE",
                 "map_type": "MAP_TYPE_INDOOR", "allow_cycling": False, "allow_escaping": False, "allow_running": False,
                 "show_map_name": False, "floor_number": 0, "battle_scene": "MAP_BATTLE_SCENE_NORMAL",
                 "region": "REGION_SINNOH", "connections": None, "coord_events": [], "bg_events": [],
                 "warp_events": [dict(w, dest_map="MAP_" + const_name(town), dest_warp_id=str(town_warp))
                                 for w in src_map["warp_events"] if w["dest_map"] == "MAP_JUBILIFE_CITY"]}
            if kind == "pc":
                nurse = next(o for o in src_map["object_events"] if o["graphics_id"] == "OBJ_EVENT_GFX_NURSE")
                lid = f"LOCALID_{icname}_NURSE"
                j["object_events"] = [dict(nurse, local_id=lid, script=f"{iname}_TreyEventScript_Nurse")]
                stairs = next(w for w in src_map["warp_events"] if w["dest_map"] != "MAP_JUBILIFE_CITY")
                j["bg_events"] = [{"type": "sign", "x": stairs["x"], "y": stairs["y"], "elevation": 0,
                                   "player_facing_dir": "BG_EVENT_PLAYER_FACING_ANY", "script": NOT_BUILT}]
                text = (f"@ TREY (6b-4, D33): generated by tools/trey/import_sinnoh.py (maps). {town}'s Pokemon Center\n"
                        f"@ (the repo has no interior here; Jubilife's layout). The upstairs isn't built.\n\n"
                        f"{iname}_MapScripts::\n\tmap_script MAP_SCRIPT_ON_TRANSITION, {iname}_TreyOnTransition\n\t.byte 0\n\n"
                        f"{iname}_TreyOnTransition:\n\tsetrespawn {shell_heal[town]}\n\tend\n\n"
                        f"{iname}_TreyEventScript_Nurse::\n\tsetvar VAR_0x800B, {lid}\n\tcall Common_EventScript_PkmnCenterNurse\n"
                        f"\twaitmessage\n\twaitbuttonpress\n\trelease\n\tend\n")
            else:
                clerk = next(o for o in src_map["object_events"] if o["graphics_id"] == "OBJ_EVENT_GFX_MART_EMPLOYEE")
                j["object_events"] = [dict(clerk, script=f"{iname}_TreyEventScript_Clerk")]
                stock = "".join(f"\t.2byte {i}\n" for i in FULL_STOCK if i in items)
                text = (f"@ TREY (6b-4, D37): generated by tools/trey/import_sinnoh.py (maps). {town}'s Poke Mart, full\n"
                        f"@ DPPt stock (to be reworked for every Mart in the story phase, 6-M). Jubilife's layout.\n\n"
                        f"{iname}_MapScripts::\n\t.byte 0\n\n"
                        f"{iname}_TreyEventScript_Clerk::\n\tlock\n\tfaceplayer\n\tmessage gText_HowMayIServeYou\n"
                        f"\twaitmessage\n\tpokemart {iname}_TreyMart_Items\n\tmsgbox gText_PleaseComeAgain, MSGBOX_DEFAULT\n"
                        f"\trelease\n\tend\n\n\t.align 2\n{iname}_TreyMart_Items:\n{stock}\tpokemartlistend\n")
            out_maps[iname] = [grp, j, text, None]
            report.append((iname, collections.Counter({"new (shell town)": 1})))

    # 6. Canalave ferry sailor (D33)
    c = out_maps[FERRY["map"]]
    c[1]["object_events"].append({"local_id": "LOCALID_CANALAVE_CITY_FERRY_SAILOR", "type": "object",
                                  "graphics_id": "OBJ_EVENT_GFX_SAILOR", "x": FERRY["sailor"][0], "y": FERRY["sailor"][1],
                                  "elevation": 3, "movement_type": FERRY["facing"], "movement_range_x": 0, "movement_range_y": 0,
                                  "trainer_type": "TRAINER_TYPE_NONE", "trainer_sight_or_berry_tree_id": "0",
                                  "script": "CanalaveCity_TreyEventScript_FerrySailor", "flag": "0"})
    c[2] += ("\n@ TREY (6b-4, D33): Canalave's transit stop (data/scripts/trey_transit.inc); the ship is the S.S. Tidal (D30).\n"
             "CanalaveCity_TreyEventScript_FerrySailor::\n\tlock\n\tfaceplayer\n\tsetvar VAR_0x8004, TRANSIT_SHIP\n"
             "\tsetvar VAR_0x8005, TRANSIT_STOP_CANALAVE\n\tsetvar VAR_0x8007, 0\n\tcall TreyTransit_EventScript_ChooseDestination\n"
             "\tgoto_if_eq VAR_0x8006, TRANSIT_STOP_NONE, CanalaveCity_TreyEventScript_FerryEnd\n\tspecial TreyTransit_Board\n"
             "\tmsgbox CanalaveCity_TreyText_AllAboard, MSGBOX_DEFAULT\n\tclosemessage\n"
             "\tplayse SE_EXIT\n\tfadescreen FADE_TO_BLACK\n\twarp MAP_SS_TIDAL_CORRIDOR, 1, 10\n\twaitstate\n\trelease\n\tend\n\n"
             "CanalaveCity_TreyEventScript_FerryEnd:\n\trelease\n\tend\n\n"
             "CanalaveCity_TreyText_AllAboard:\n\t.string \"All aboard! Please head to your\\n\"\n"
             "\t.string \"cabin and enjoy the voyage.$\"\n")

    # 7. closed doors (D37): door/ladder/stair tiles with no warp become impassable + "(Not built yet.)"
    blocks_out = {}
    closed_total = 0
    for name, (grp, d, text, old) in out_maps.items():
        if old is None:
            continue
        sl = new_layouts[d["layout"]][0]
        w, h = sl["width"], sl["height"]
        blocks = list(struct.unpack(f"<{w * h}H", open(os.path.join(src, sl["blockdata_filepath"]), "rb").read()[:w * h * 2]))
        pa = tileset_attrs(tilesets_map.get(sl["primary_tileset"], sl["primary_tileset"]), attr_cache)
        sa = tileset_attrs(tilesets_map.get(sl["secondary_tileset"], sl["secondary_tileset"]), attr_cache)
        warps = {(x["x"], x["y"]) for x in d.get("warp_events") or []}
        signs = {(b["x"], b["y"]) for b in d.get("bg_events") or []}
        n = 0
        for i, b in enumerate(blocks):
            mid = b & 0x3FF
            a = pa[mid] if mid < 512 else (sa[mid - 512] if mid - 512 < len(sa) else 0)
            beh = behaviours[a] if a < len(behaviours) else ""
            pos = (i % w, i // w)
            if CLOSED_BEHAVIOURS.match(beh) and pos not in warps:
                blocks[i] = (b & ~0x0C00) | 0x0400
                if pos not in signs:
                    d.setdefault("bg_events", []).append({"type": "sign", "x": pos[0], "y": pos[1], "elevation": 0,
                                                          "player_facing_dir": "BG_EVENT_PLAYER_FACING_ANY",
                                                          "script": NOT_BUILT})
                n += 1
        if n:
            for rn, notes in report:
                if rn == name:
                    notes["closed door/ladder (Not built yet)"] = n
            closed_total += n
        blocks_out[d["layout"]] = blocks

    # 8. respawn NPCs of the repo's heal locations: the nurse kept on the respawn map
    for h in new_heal:
        if h.get("respawn_npc"):
            continue
        rm = next((v for v in out_maps.values() if v[1]["id"] == h.get("respawn_map")), None)
        nurse = rm and next((o for o in rm[1]["object_events"] if "TreyEventScript_Nurse" in str(o.get("script"))), None)
        if nurse:
            h["respawn_npc"] = nurse["local_id"]
        else:
            h.pop("respawn_map", None)

    if len(ctx.flags) > ITEM_FLAG_SLOTS:
        die(f"{len(ctx.flags)} item flags, but only {ITEM_FLAG_SLOTS} slots")

    # 9. checks against TREY's constants
    songs = open("include/constants/songs.h", encoding="utf-8").read()
    secs = {s["id"] for s in jload("src/data/region_map/region_map_sections.json")["map_sections"]}
    gfx = open("include/constants/event_objects.h", encoding="utf-8").read()
    for name, (_, d, _, _) in out_maps.items():
        for key in ("music", "trey_night_music"):
            if key in d and not re.search(r"#define\s+" + d[key] + r"\b", songs):
                die(f"{name}: unknown {key} {d[key]}")
        if d["region_map_section"] not in secs:
            die(f"{name}: unknown location {d['region_map_section']}")
        for o in d.get("object_events") or []:
            gid = o.get("graphics_id", "")
            if not gid.startswith("OBJ_EVENT_GFX_SPECIES(") and not re.search(r"\b" + re.escape(gid) + r"\b", gfx):
                die(f"{name}: unknown graphics {gid}")

    totals = collections.Counter()
    for _, notes in report:
        totals.update(notes)
    print(f"import_sinnoh.py maps: {len(out_maps)} maps ({len(maps)} from the repo + {len(shell_maps)} shell-town interiors), "
          f"{len(new_layouts)} layouts, {len(new_heal)} heal locations, {len(ctx.flags)} item flags, "
          f"{closed_total} closed doors. " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())))
    if dry:
        return out_maps, new_heal

    # 10. write maps, layouts, groups, heal locations, includes, flags, report
    for name, (grp, d, text, old) in out_maps.items():
        os.makedirs(os.path.join("data/maps", name), exist_ok=True)
        jsave(os.path.join("data/maps", name, "map.json"), d)
        with open(os.path.join("data/maps", name, "scripts.inc"), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    for lid, (sl, folder) in new_layouts.items():
        dst = os.path.join("data/layouts", folder)
        os.makedirs(dst, exist_ok=True)
        shutil.copy2(os.path.join(src, sl["border_filepath"]), os.path.join(dst, "border.bin"))
        with open(os.path.join(dst, "map.bin"), "wb") as f:
            f.write(struct.pack(f"<{len(blocks_out[lid])}H", *blocks_out[lid]))
        layouts["layouts"].append({
            "id": lid, "name": f"{folder}_Layout", "width": sl["width"], "height": sl["height"],
            "border_width": sl.get("border_width", 2), "border_height": sl.get("border_height", 2),
            "primary_tileset": tilesets_map.get(sl["primary_tileset"], sl["primary_tileset"]),
            "secondary_tileset": tilesets_map.get(sl["secondary_tileset"], sl["secondary_tileset"]),
            "border_filepath": f"{dst}/border.bin", "blockdata_filepath": f"{dst}/map.bin",
            "layout_version": "emerald"})
    jsave("data/layouts/layouts.json", layouts)
    for gname in GROUP_ORDER:
        groups["group_order"].append(gname)
        groups[gname] = [n for n, v in out_maps.items() if v[0] == gname]
    jsave("data/maps/map_groups.json", groups)
    heal_json["heal_locations"] += new_heal
    jsave("src/data/heal_locations.json", heal_json)
    with open("data/scripts/trey_sinnoh_maps.inc", "w", encoding="utf-8", newline="\n") as f:
        f.write("@ TREY (6b-4): generated by tools/trey/import_sinnoh.py (maps). Script files of the Sinnoh maps.\n\n"
                f"@ D37: doors and entrances that have no interior yet.\n{NOT_BUILT}::\n"
                "\tmsgbox TreySinnoh_Text_NotBuiltYet, MSGBOX_SIGN\n\tend\n\n"
                "TreySinnoh_Text_NotBuiltYet:\n\t.string \"(Not built yet.)$\"\n\n")
        for name in out_maps:
            f.write(f"\t.include \"data/maps/{name}/scripts.inc\"\n")
    with open("include/constants/trey_sinnoh_flags.h", "w", encoding="utf-8", newline="\n") as f:
        f.write("// TREY (6b-4): generated by tools/trey/import_sinnoh.py (maps). Item ball and hidden item flags of the\n"
                "// Sinnoh maps (the repo reused Hoenn's flags), in TREY's flag space. Never reorder: saves use them.\n"
                "#ifndef GUARD_CONSTANTS_TREY_SINNOH_FLAGS_H\n#define GUARD_CONSTANTS_TREY_SINNOH_FLAGS_H\n\n")
        for flag, n in ctx.flags.items():
            f.write(f"#define {flag:<60} (TREY_FLAG_SINNOH_ITEMS_START + {n})\n")
        f.write(f"\n#define TREY_SINNOH_ITEM_FLAGS_USED {len(ctx.flags)}\n\n#endif // GUARD_CONSTANTS_TREY_SINNOH_FLAGS_H\n")
    os.makedirs("docs/trey", exist_ok=True)
    with open("docs/trey/sinnoh_import_report.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write("TREY (6b-4): what tools/trey/import_sinnoh.py (maps) kept, removed and added on each Sinnoh map.\n\n")
        for name, notes in report:
            f.write(f"{name}: " + ", ".join(f"{k} {v}" for k, v in sorted(notes.items())) + "\n")
        f.write("\nTOTAL: " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())) + "\n\n")
        f.write("Music (D34): nearest DPPt song TREY has, where the repo borrowed a Hoenn/FRLG song or DPPt has a song\n"
                "TREY lacks (Route 206, Celestic, Battle Zone, Oreburgh Gate/Mine, Hotel Grand Lake):\n")
        for name, song in MUSIC.items():
            f.write(f"  {name}: {song}\n")
        f.write("Night music: " + ", ".join(f"{k} {v}" for k, v in NIGHT_MUSIC.items()) + "\n")
    return out_maps, new_heal
