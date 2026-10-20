"""TREY (6a-5, TREY_PLAN.md D31/D32): the "maps" step of tools/trey/import_hns.py.

Copies Heart & Soul's Johto and Sinjoh Ruins maps into TREY, like tools/trey/import_frlg.py did for Kanto:

  names     the _hns suffix is dropped (MAP_NEW_BARK_TOWN_HNS -> MAP_NEW_BARK_TOWN); Heart & Soul's Rocket
            Hideout becomes MahoganyHideout_* (FRLG's Rocket Hideout keeps its name).
  layouts   copied and marked "frlg" (Heart & Soul's "hns" layouts are FRLG-sized with FRLG borders; their
            tilesets were converted by the "tilesets" step).
  groups    gMapGroup_Johto_<Type>[_<Place>] (TREY_PLAN.md 4a).
  events    harmless ones kept (signs, talk-only NPCs, nurses, clerks, item balls, hidden items, HM obstacles);
            trainers, triggers and story scripts dropped (import_frlg.py's rules). Item flags move into the
            TREY Johto item flag block (FLAG_JOHTO_*, include/constants/trey_johto_flags.h).
  skipped   Heart & Soul's own Indigo Plateau, Victory Road and Elite Four (Johto shares FRLG's, D32), its fan
            places (New Sinjoh, Routes 49/50, Snowswept Cavern, Trainer Hill) and test/unused maps. Warps into
            skipped maps are removed (other warp numbers are shifted to match).
  Kanto     Route 22 -> Pokemon League Reception Gate -> FRLG's Route 22 gate -> Route 23 (D32).

Story scripts for Johto are written by hand later; after that, don't re-run this step over edited maps.
"""
import collections
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_frlg  # noqa: E402

ITEM_FLAG_SLOTS = 512   # TREY_FLAG_JOHTO_ITEMS_COUNT in include/constants/flags.h

SKIP = set("""
IndigoPlateau_hns IndigoPlateau_PokemonCenter_hns PokemonLeague_WillsRoom_hns PokemonLeague_KogasRoom_hns
PokemonLeague_BrunosRoom_hns PokemonLeague_KarensRoom_hns PokemonLeague_ChampionsRoom_hns PokemonLeague_HallOfFame_hns
Route23_hns VictoryRoadKanto_1F_hns VictoryRoadKanto_B1F_hns VictoryRoadKanto_B2F_hns
NewSinjoh_HotSprings_hns NewSinjoh_House1_hns NewSinjoh_House2_hns NewSinjoh_House3_hns NewSinjoh_House4_hns
NewSinjoh_KimonoHideout_hns NewSinjoh_PokemonCenter_hns NewSinjoh_hns Route49_hns Route50_hns SnowsweptCavern_hns
TrainerHill_Courtyard_hns Saffron_Temp_hns Trees_hns TestMap1_hns TestMap2_hns
SafariZone1_hns SafariZone2_hns SafariZone3_hns SafariZoneIndoor_hns
""".split())

RENAME = {
    "Mahoganytown_hns": "MahoganyTown",
    "RocketHideout_B1F_hns": "MahoganyHideout_B1F",
    "RocketHideout_B2F_hns": "MahoganyHideout_B2F",
    "RocketHideout_B3F_hns": "MahoganyHideout_B3F",
}

MAPSEC = {
    "MAPSEC_ROCKET_HIDEOUT_HNS": "MAPSEC_MAHOGANY_HIDEOUT",
    "MAPSEC_VICTORY_ROAD_HNS": "MAPSEC_ROUTE_26",   # the Reception Gate, at the top of Route 26
}
WEATHER = {"WEATHER_LEAVES": "WEATHER_NONE"}

GROUPS = {
    "gMapGroup_TownsAndRoutes_Hns": "gMapGroup_Johto_Outdoor",
    "gMapGroup_Sinjoh_Hns": "gMapGroup_Johto_Outdoor",
    "gMapGroup_Dungeons_Hns": "gMapGroup_Johto_Dungeon",
    "gMapGroup_IndoorJohtoRoutes_Hns": "gMapGroup_Johto_Indoor_Routes",
    "gMapGroup_IndoorKantoRoutes_Hns": "gMapGroup_Johto_Indoor_Routes",
}

NURSE_SCRIPTS = {"OldaleTown_PokemonCenter_1F_EventScript_Nurse"}
ITEM_GFX = {"OBJ_EVENT_GFX_ITEM_BALL", "OBJ_EVENT_GFX_ITEM_BALL_HNS", "OBJ_EVENT_GFX_POKE_BALL", "OBJ_EVENT_GFX_FOSSIL_HNS"}

# D32: the Reception Gate sits between FRLG's Route 22 and Route 22's league gate.
RECEPTION_WARPS = {   # Reception Gate warp index -> (dest map, dest warp)
    1: ("MAP_ROUTE22_NORTH_ENTRANCE", "2"),
    2: ("MAP_ROUTE22_NORTH_ENTRANCE", "2"),
    4: ("MAP_ROUTE22", "0"),
}
KANTO_EDITS = {       # FRLG map folder -> {warp index: (dest map, dest warp)}
    "Route22_Frlg": {0: ("MAP_RECEPTION_GATE", "4"), 1: ("MAP_RECEPTION_GATE", "4")},
    "Route22_NorthEntrance_Frlg": {1: ("MAP_RECEPTION_GATE", "1"), 2: ("MAP_RECEPTION_GATE", "1"), 3: ("MAP_RECEPTION_GATE", "1")},
}


def die(msg):
    sys.exit(f"import_hns.py maps: {msg}")


def jload(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def jsave(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def const_name(name):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).upper()


def strip_hns(s):
    return re.sub(r"_HNS$", "", s)


class JohtoImport(import_frlg.MapImport):
    """import_frlg's rules, with Heart & Soul's item balls (finditem scripts) and nurse script."""

    def decide_object(self, o, kept_ids, required, final=False):
        script = o.get("script", "0x0")
        if o.get("graphics_id") in ITEM_GFX and script in self.blocks:
            b = [c for c in import_frlg.body(self.blocks[script]) if c != "end"]
            if len(b) == 1 and b[0].startswith("finditem "):
                self.root(script)
                self.notes["item ball"] += 1
                return "same"
        if script in NURSE_SCRIPTS or (script in self.blocks and
                                       self.reaches_cmd(script, "call", "Common_EventScript_PkmnCenterNurse") is not None):
            lid = o.get("local_id")
            if not lid:
                lid = f"LOCALID_{const_name(self.name)}_NURSE"
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


class JohtoCtx(import_frlg.Ctx):
    def item_flag(self, flag):
        if flag.startswith("FLAG_JOHTO_"):
            return flag
        new = "FLAG_JOHTO_" + flag[len("FLAG_"):]
        if new not in self.flags:
            self.flags[new] = len(self.flags)
        return new


def trey_items():
    """Every ITEM_* TREY has (items.h, plus the ITEM_TM_*/ITEM_HM_* names made from tms_hms.h)."""
    text = open("include/constants/items.h", encoding="utf-8").read()
    items = set(re.findall(r"^\s*(ITEM_\w+)\s*=", text, re.M)) | set(re.findall(r"#define\s+(ITEM_\w+)", text))
    tm = open("include/constants/tms_hms.h", encoding="utf-8").read()
    for kind in ("TM", "HM"):
        m = re.search(r"#define FOREACH_" + kind + r"\(F\)(.*?)\n\n", tm, re.S)
        if m:
            items |= {f"ITEM_{kind}_{x}" for x in re.findall(r"F\((\w+)\)", m.group(1))}
    return items


def drop_missing_items(d, scripts, items, notes):
    """Heart & Soul items TREY doesn't have (its own key items, TMs outside TREY's list): their item balls,
    hidden items and mart entries are removed."""
    def missing(tok):
        return tok.startswith("ITEM_") and tok not in items
    _, blocks = import_frlg.parse_blocks(scripts)
    keep = []
    for o in d.get("object_events", []):
        b = blocks.get(o.get("script", ""))
        code = [c for c in import_frlg.body(b)] if b else []
        if any(c.startswith("finditem ") and missing(c.split()[1].rstrip(",")) for c in code):
            notes["item ball dropped (item not in TREY)"] += 1
            continue
        keep.append(o)
    d["object_events"] = keep
    bgs = []
    for b in d.get("bg_events", []):
        if b.get("type") == "hidden_item" and missing(b.get("item", "")):
            notes["hidden item dropped (item not in TREY)"] += 1
            continue
        bgs.append(b)
    d["bg_events"] = bgs
    out = []
    for line in scripts.split("\n"):
        m = re.match(r"\s*\.2byte\s+(ITEM_\w+)\s*(?:@.*)?$", line)
        if m and missing(m.group(1)):
            notes["mart item dropped (item not in TREY)"] += 1
            continue
        out.append(line)
    return "\n".join(out)


def undo_previous(dry):
    """Re-running the step replaces its earlier output: the gMapGroup_Johto_* maps, their layouts and heal
    locations are removed first. (Don't re-run once Johto maps have been edited by hand.)"""
    groups = jload("data/maps/map_groups.json")
    johto = [g for g in groups["group_order"] if g.startswith("gMapGroup_Johto_")]
    if not johto:
        return False
    names = [m for g in johto for m in groups[g]]
    ids, lids = set(), set()
    for m in names:
        p = os.path.join("data/maps", m, "map.json")
        if os.path.exists(p):
            d = jload(p)
            ids.add(d["id"])
            lids.add(d["layout"])
    print(f"import_hns.py maps: replacing the previous import ({len(names)} maps)")
    if dry:
        return True
    for m in names:
        shutil.rmtree(os.path.join("data/maps", m), ignore_errors=True)
    for g in johto:
        del groups[g]
        groups["group_order"].remove(g)
    jsave("data/maps/map_groups.json", groups)
    layouts = jload("data/layouts/layouts.json")
    keep = []
    for l in layouts["layouts"]:
        if l and l["id"] in lids:
            shutil.rmtree(os.path.dirname(l["blockdata_filepath"]), ignore_errors=True)
            continue
        keep.append(l)
    layouts["layouts"] = keep
    jsave("data/layouts/layouts.json", layouts)
    heal = jload("src/data/heal_locations.json")
    heal["heal_locations"] = [h for h in heal["heal_locations"] if h["map"] not in ids]
    jsave("src/data/heal_locations.json", heal)
    return True


def step_maps(hns, dry):
    if not os.path.exists("pokeemerald.map"):
        die("build the ROM once first (pokeemerald.map lists the labels TREY has)")
    if undo_previous(dry) and dry:
        die("--dry-run after an earlier import isn't supported (the earlier maps would clash); run without it")
    hgroups = jload(os.path.join(hns, "data/maps/map_groups.json"))
    hlayouts = {l["id"]: l for l in jload(os.path.join(hns, "data/layouts/layouts.json"))["layouts"] if l}
    groups = jload("data/maps/map_groups.json")
    layouts = jload("data/layouts/layouts.json")
    ours_maps = set(os.listdir("data/maps"))
    our_ids, our_layouts = set(), {l["id"] for l in layouts["layouts"] if l}
    for g in groups["group_order"]:
        for m in groups[g]:
            p = os.path.join("data/maps", m, "map.json")
            if os.path.exists(p):
                our_ids.add(jload(p)["id"])

    # 1. which maps, and their new names
    maps = collections.OrderedDict()   # old name -> (hns group, map json)
    for g in hgroups["group_order"]:
        for m in hgroups[g]:
            if m in SKIP or (m in ours_maps and not m.endswith("_hns")):
                continue
            p = os.path.join(hns, "data/maps", m, "map.json")
            if not os.path.exists(p):
                continue
            d = jload(p)
            if d.get("region") in ("REGION_JOHTO", "REGION_HISUI"):
                maps[m] = (g, d)
    new_name = {m: RENAME.get(m, m[:-4] if m.endswith("_hns") else m) for m in maps}
    id_map = {d["id"]: "MAP_" + const_name(new_name[m]) if m in RENAME else strip_hns(d["id"]) for m, (_, d) in maps.items()}
    layout_map = {}
    for m, (_, d) in maps.items():
        layout_map[d["layout"]] = "LAYOUT_" + const_name(new_name[m]) if m in RENAME else strip_hns(d["layout"])
    for n in new_name.values():
        if n in ours_maps:
            die(f"{n} already exists in data/maps")
    for i in id_map.values():
        if i in our_ids:
            die(f"{i} already exists")
    for i in layout_map.values():
        if i in our_layouts:
            die(f"{i} already exists in layouts.json")

    # 2. tokens to rename in map JSON and scripts
    def ren_token(tok):
        if tok in id_map:
            return id_map[tok]
        if tok in layout_map:
            return layout_map[tok]
        if tok.startswith("HEAL_LOCATION_") and tok.endswith("_HNS"):
            return strip_hns(tok)
        return tok
    label_prefix = {m: new_name[m] for m in maps}

    def ren_text(text):
        def sub(mt):
            tok = mt.group(0)
            i = tok.find("_hns")
            if i > 0 and tok[:i + 4] in label_prefix and (len(tok) == i + 4 or tok[i + 4] == "_"):
                return label_prefix[tok[:i + 4]] + tok[i + 4:]
            return ren_token(tok)
        return re.sub(r"\b[A-Za-z_]\w*\b", sub, text)

    # 3. heal locations (renamed; respawn NPC = the nurse kept on the respawn map)
    hheal = [h for h in jload(os.path.join(hns, "src/data/heal_locations.json"))["heal_locations"] if h["map"] in id_map]
    heal_json = jload("src/data/heal_locations.json")
    our_heal_ids = {h["id"] for h in heal_json["heal_locations"]}
    new_heal = []
    for h in hheal:
        h = dict(h)
        h["id"] = strip_hns(h["id"])
        h["map"] = id_map[h["map"]]
        if h.get("respawn_map") in id_map:
            h["respawn_map"] = id_map[h["respawn_map"]]
        else:
            h.pop("respawn_map", None)
        h.pop("respawn_npc", None)
        if h["id"] in our_heal_ids:
            die(f"{h['id']} already exists in heal_locations.json")
        new_heal.append(h)

    items = trey_items()
    movement_types = set(re.findall(r"#define\s+(MOVEMENT_TYPE_\w+)", open("include/constants/event_object_movement.h", encoding="utf-8").read()))

    # 4. global context (labels TREY has, local IDs the engine needs)
    global_labels = import_frlg.load_global_labels("pokeemerald.map")
    global_labels |= {"EventScript_Whirlpool"}   # data/scripts/trey_whirlpool.inc (6a-5)
    required = set()
    for h in heal_json["heal_locations"]:
        if h.get("respawn_npc"):
            required.add(h["respawn_npc"])
    ctx = JohtoCtx(global_labels, set(), our_heal_ids | {h["id"] for h in new_heal}, required)

    # 5. warps into skipped maps are removed: per map, old index -> new index
    keep_warp = {}
    for m, (_, d) in maps.items():
        idx, k = {}, 0
        for i, w in enumerate(d.get("warp_events", [])):
            dest = w["dest_map"]
            if (m == "ReceptionGate_hns" and i in RECEPTION_WARPS) or dest in id_map or dest == "MAP_DYNAMIC":
                idx[i] = k
                k += 1
        keep_warp[d["id"]] = idx

    out_maps, report, totals = collections.OrderedDict(), [], collections.Counter()
    new_layouts = collections.OrderedDict()
    for m, (g, d) in maps.items():
        name = new_name[m]
        notes = collections.Counter()
        d = json.loads(json.dumps(d))
        d["id"], d["name"], d["layout"] = id_map[d["id"]], name, layout_map[d["layout"]]
        d.pop("game_version", None)
        d["region"] = "REGION_JOHTO"
        d["region_map_section"] = MAPSEC.get(d["region_map_section"], d["region_map_section"])
        d["weather"] = WEATHER.get(d["weather"], d["weather"])
        if d.get("battle_scene", "").endswith("_HNS"):
            d["battle_scene"] = "MAP_BATTLE_SCENE_NORMAL"
        d.setdefault("floor_number", 0)
        conns = []
        for c in d.get("connections") or []:
            if c["map"] in id_map:
                conns.append(dict(c, map=id_map[c["map"]]))
            else:
                notes["connection dropped"] += 1
        d["connections"] = conns or None
        warps = []
        for i, w in enumerate(d.get("warp_events", [])):
            if m == "ReceptionGate_hns" and i in RECEPTION_WARPS:
                dm, dw = RECEPTION_WARPS[i]
                warps.append(dict(w, dest_map=dm, dest_warp_id=dw))
            elif w["dest_map"] == "MAP_DYNAMIC":
                warps.append(w)
            elif w["dest_map"] in id_map:
                old = int(w["dest_warp_id"])
                new = keep_warp[w["dest_map"]].get(old)
                if new is None:   # Heart & Soul points at a warp that doesn't exist (or was removed): use its first
                    new = 0
                    notes["warp to missing warp id fixed"] += 1
                warps.append(dict(w, dest_map=id_map[w["dest_map"]], dest_warp_id=str(new)))
            else:
                notes["warp removed"] += 1
        d["warp_events"] = warps
        # unique local IDs (Heart & Soul repeats names like LOCALID_NURSE across maps)
        lids = {}
        objs = []
        for o in d.get("object_events", []):
            if str(o.get("trainer_sight_or_berry_tree_id", "")).startswith("BERRY_TREE_") or o.get("script") == "BerryTreeScript":
                notes["berry tree dropped (Johto berry trees come later)"] += 1   # Heart & Soul's own BERRY_TREE_* ids
                continue
            if o.get("movement_type") not in movement_types:
                notes[f"movement {o.get('movement_type')} -> NONE"] += 1
                o["movement_type"] = "MOVEMENT_TYPE_NONE"
            objs.append(o)
        d["object_events"] = objs
        for o in d.get("object_events", []):
            gfx = o.get("graphics_id", "")
            mm = re.fullmatch(r"OBJ_EVENT_GFX_MON_BASE\s*\+\s*SPECIES_(\w+)", gfx)
            if mm:
                o["graphics_id"] = f"OBJ_EVENT_GFX_SPECIES({mm.group(1)})"
            if o.get("local_id"):
                old = o["local_id"]
                new = f"LOCALID_{const_name(name)}_{old[len('LOCALID_'):]}"
                lids[old] = new
                o["local_id"] = new
        sp = os.path.join(hns, "data/maps", m, "scripts.inc")
        scripts = open(sp, encoding="utf-8").read() if os.path.exists(sp) else f"{m}_MapScripts::\n\t.byte 0\n"
        scripts = re.sub(r"\bLOCALID_\w+\b", lambda t: lids.get(t.group(0), t.group(0)), scripts)
        scripts = drop_missing_items(d, scripts, items, notes)
        scripts = ren_text(scripts)
        for key in ("object_events", "bg_events"):
            for e in d.get(key, []):
                if e.get("script"):
                    e["script"] = ren_text(e["script"])
        imp = JohtoImport(name, d, scripts, ctx)
        text = imp.run()
        text = text.replace("generated by tools/trey/import_frlg.py from upstream's", "generated by tools/trey/import_hns.py (maps) from Heart & Soul's")
        text = text.replace("FRLG story scripts", "Heart & Soul story scripts")
        text = text.replace("@ TREY (5a): generated by tools/trey/import_hns.py", "@ TREY (6a-5): generated by tools/trey/import_hns.py")
        notes.update(imp.notes)
        totals.update(notes)
        report.append(f"{name}: " + ", ".join(f"{k} {v}" for k, v in sorted(notes.items())))
        group = GROUPS.get(g) or re.sub(r"^gMapGroup_Indoor(\w+)_Hns$", r"gMapGroup_Johto_Indoor_\1", g)
        if g == "gMapGroup_SpecialArea_Hns":
            group = "gMapGroup_Johto_Indoor_SSAqua" if name.startswith("SSAqua") else "gMapGroup_Johto_Outdoor_Safari"
        if not group.startswith("gMapGroup_Johto_"):
            die(f"{m}: no TREY group for {g}")
        out_maps[name] = (group, imp.j, text, m)
        hl = hlayouts[maps[m][1]["layout"]]
        lid = layout_map[hl["id"]]
        if lid not in new_layouts:
            folder = os.path.basename(os.path.dirname(hl["blockdata_filepath"]))
            folder = RENAME.get(folder, folder[:-4] if folder.endswith("_hns") else folder)
            if os.path.exists(os.path.join("data/layouts", folder)) or folder in [f for _, f in new_layouts.values()]:
                die(f"layout folder {folder} already exists")
            new_layouts[lid] = (hl, folder)

    # whiteout: the nurse on the respawn map greets the player
    for h in new_heal:
        rm = next((v for v in out_maps.values() if v[1]["id"] == h.get("respawn_map")), None)
        if rm:
            nurse = next((o for o in rm[1].get("object_events", []) if "TreyEventScript_Nurse" in str(o.get("script"))), None)
            if nurse:
                h["respawn_npc"] = nurse["local_id"]

    if len(ctx.flags) > ITEM_FLAG_SLOTS:
        die(f"{len(ctx.flags)} item flags, but only {ITEM_FLAG_SLOTS} slots")

    # checks against TREY's constants
    songs = open("include/constants/songs.h", encoding="utf-8").read()
    secs = {s["id"] for s in jload("src/data/region_map/region_map_sections.json")["map_sections"]}
    weathers = open("include/constants/weather.h", encoding="utf-8").read()
    gfx = open("include/constants/event_objects.h", encoding="utf-8").read()
    for name, (_, d, _, _) in out_maps.items():
        if not re.search(r"#define\s+" + d["music"] + r"\b", songs):
            die(f"{name}: unknown music {d['music']}")
        if d["region_map_section"] not in secs:
            die(f"{name}: unknown location {d['region_map_section']}")
        if not re.search(r"\b" + d["weather"] + r"\b", weathers):
            die(f"{name}: unknown weather {d['weather']}")
        for o in d.get("object_events", []):
            gid = o.get("graphics_id", "")
            if not gid.startswith("OBJ_EVENT_GFX_SPECIES(") and not re.search(r"\b" + re.escape(gid) + r"\b", gfx):
                die(f"{name}: unknown graphics {gid}")

    print(f"import_hns.py maps: {len(out_maps)} maps, {len(new_layouts)} layouts, {len(new_heal)} heal locations, "
          f"{len(ctx.flags)} item flags. " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())))
    if dry:
        print("\n".join(report))
        return

    # write maps and layouts
    for name, (group, d, text, old) in out_maps.items():
        os.makedirs(os.path.join("data/maps", name), exist_ok=True)
        jsave(os.path.join("data/maps", name, "map.json"), d)
        with open(os.path.join("data/maps", name, "scripts.inc"), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    for lid, (hl, folder) in new_layouts.items():
        dst = os.path.join("data/layouts", folder)
        os.makedirs(dst, exist_ok=True)
        shutil.copy2(os.path.join(hns, hl["border_filepath"]), os.path.join(dst, "border.bin"))
        shutil.copy2(os.path.join(hns, hl["blockdata_filepath"]), os.path.join(dst, "map.bin"))
        layouts["layouts"].append({
            "id": lid, "name": f"{folder}_Layout", "width": hl["width"], "height": hl["height"],
            "border_width": 2, "border_height": 2,
            "primary_tileset": hl["primary_tileset"], "secondary_tileset": hl["secondary_tileset"],
            "border_filepath": f"{dst}/border.bin", "blockdata_filepath": f"{dst}/map.bin",
            "layout_version": "frlg"})
    jsave("data/layouts/layouts.json", layouts)
    for name, (group, _, _, _) in out_maps.items():
        if group not in groups:
            groups[group] = []
            groups["group_order"].append(group)
        if name not in groups[group]:
            groups[group].append(name)
    jsave("data/maps/map_groups.json", groups)
    heal_json["heal_locations"] += new_heal
    jsave("src/data/heal_locations.json", heal_json)

    # Kanto side of the Reception Gate (D32)
    for folder, edits in KANTO_EDITS.items():
        p = os.path.join("data/maps", folder, "map.json")
        d = jload(p)
        for i, (dm, dw) in edits.items():
            d["warp_events"][i]["dest_map"], d["warp_events"][i]["dest_warp_id"] = dm, dw
        jsave(p, d)

    with open("data/scripts/trey_hns_maps.inc", "w", encoding="utf-8", newline="\n") as f:
        f.write("@ TREY (6a-5): generated by tools/trey/import_hns.py (maps). Script files of the Johto/Sinjoh maps.\n\n")
        for name in out_maps:
            f.write(f"\t.include \"data/maps/{name}/scripts.inc\"\n")
    with open("include/constants/trey_johto_flags.h", "w", encoding="utf-8", newline="\n") as f:
        f.write("// TREY (6a-5): generated by tools/trey/import_hns.py (maps). Item ball and hidden item flags of the\n")
        f.write("// Johto maps, renamed FLAG_JOHTO_* and moved into TREY's flag space. Never reorder: saves use them.\n")
        f.write("#ifndef GUARD_CONSTANTS_TREY_JOHTO_FLAGS_H\n#define GUARD_CONSTANTS_TREY_JOHTO_FLAGS_H\n\n")
        for flag, n in ctx.flags.items():
            f.write(f"#define {flag:<56} (TREY_FLAG_JOHTO_ITEMS_START + {n})\n")
        f.write(f"\n#define TREY_JOHTO_ITEM_FLAGS_USED {len(ctx.flags)}\n\n#endif // GUARD_CONSTANTS_TREY_JOHTO_FLAGS_H\n")
    os.makedirs("docs/trey", exist_ok=True)
    with open("docs/trey/johto_import_report.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write("TREY (6a-5): what tools/trey/import_hns.py (maps) kept and removed on each Johto map.\n\n")
        f.write("\n".join(report) + "\n\nTOTAL: " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())) + "\n")


# ---------------------------------------------------------------------------------------------------
# Wild Pokémon (6a-6)
# ---------------------------------------------------------------------------------------------------
# Heart & Soul has Day and Night tables; TREY has four times of day (David, 2026-10-20).
TIME_SPLIT = {"Day": ("Morning", "Day"), "Night": ("Evening", "Night")}
# Heart & Soul puts its Headbutt tree Pokémon in the Rock Smash table. Only maps with breakable rocks keep
# a Rock Smash table; everywhere else it becomes the Headbutt table (5 slots spread over Headbutt's 6).
HEADBUTT_FROM_ROCK_SMASH = [0, 1, 1, 2, 3, 4]
# Rock Smash Pokémon HGSS has where Heart & Soul has none (Bulbapedia, "Breakable rock"); levels follow
# the same species in the map's land table.
EXTRA_ROCK_SMASH = {
    "MAP_DARK_CAVE_NORTH_SIDE": ["SPECIES_GEODUDE", "SPECIES_GEODUDE", "SPECIES_DUNSPARCE", "SPECIES_GEODUDE", "SPECIES_DUNSPARCE"],
    "MAP_DARK_CAVE_SOUTH_SIDE": ["SPECIES_GEODUDE", "SPECIES_GEODUDE", "SPECIES_DUNSPARCE", "SPECIES_GEODUDE", "SPECIES_DUNSPARCE"],
}


def table_time(label):
    """Day, Night or None (no time in the label). Heart & Soul names some night tables *Night_hns_Day."""
    if label.endswith("_Night") or "Night_" in label:
        return "Night"
    if label.endswith("_Day"):
        return "Day"
    return None


def step_wild(hns, dry):
    """Copy Heart & Soul's wild tables for the imported Johto maps into src/data/wild_encounters.json."""
    groups = jload("data/maps/map_groups.json")
    johto = {}
    for g in groups["group_order"]:
        if g.startswith("gMapGroup_Johto_"):
            for m in groups[g]:
                d = jload(os.path.join("data/maps", m, "map.json"))
                rocks = any(o.get("script") == "EventScript_RockSmash" for o in d.get("object_events", []))
                johto[d["id"]] = (m, rocks)
    if not johto:
        die("import the maps first (import_hns.py maps)")
    def our_id(hid):
        base = hid[:-4] if hid.endswith("_HNS") else hid
        alias = {"MAP_MAHOGANYTOWN": "MAP_MAHOGANY_TOWN", "MAP_ROCKET_HIDEOUT_B1F": "MAP_MAHOGANY_HIDEOUT_B1F",
                 "MAP_ROCKET_HIDEOUT_B2F": "MAP_MAHOGANY_HIDEOUT_B2F", "MAP_ROCKET_HIDEOUT_B3F": "MAP_MAHOGANY_HIDEOUT_B3F"}
        return alias.get(base, base)
    hwild = jload(os.path.join(hns, "src/data/wild_encounters.json"))["wild_encounter_groups"][0]["encounters"]
    wild = jload("src/data/wild_encounters.json")
    grp = wild["wild_encounter_groups"][0]
    before = len(grp["encounters"])
    grp["encounters"] = [e for e in grp["encounters"] if e.get("map") not in johto]   # re-running replaces
    notes = collections.Counter()
    new = []
    for e in hwild:
        mid = our_id(e.get("map", ""))
        if mid not in johto:
            continue
        name, rocks = johto[mid]
        times = TIME_SPLIT[table_time(e["base_label"])] if table_time(e["base_label"]) else None
        if "Unused" in e["base_label"]:
            continue
        others = {table_time(x["base_label"]) for x in hwild if our_id(x.get("map", "")) == mid and "Unused" not in x["base_label"]}
        if len(others) < 2:
            times = ("Morning", "Day", "Evening", "Night")   # only one table: use it all day
        elif times is None:
            times = TIME_SPLIT["Day"]
        out = {k: v for k, v in e.items() if k.endswith("_mons") and k != "rock_smash_mons"}
        rs = e.get("rock_smash_mons")
        if rs and rocks:
            out["rock_smash_mons"] = rs
            notes["rock smash"] += 1
        elif rs:
            out["headbutt_mons"] = {"encounter_rate": rs.get("encounter_rate", 20),
                                    "mons": [rs["mons"][i] for i in HEADBUTT_FROM_ROCK_SMASH]}
            notes["headbutt (from rock smash)"] += 1
        if mid in EXTRA_ROCK_SMASH and "rock_smash_mons" not in out:
            land = {m["species"]: m for m in out.get("land_mons", {}).get("mons", [])}
            mons = []
            for sp in EXTRA_ROCK_SMASH[mid]:
                ref = land.get(sp, {"min_level": 10, "max_level": 15})
                mons.append({"min_level": ref["min_level"], "max_level": ref["max_level"], "species": sp})
            out["rock_smash_mons"] = {"encounter_rate": 50, "mons": mons}
            notes["rock smash (HGSS, added)"] += 1
        for k in list(out):
            if all(m["species"] == "SPECIES_NONE" for m in out[k]["mons"]):
                del out[k]   # Heart & Soul placeholder tables
                notes["empty table dropped"] += 1
                continue
        if not out:
            continue
        for t in times:
            new.append(dict({"map": mid, "base_label": f"s{name}_{t}"}, **out))
    labels = [e["base_label"] for e in new]
    dup = [l for l, n in collections.Counter(labels).items() if n > 1]
    if dup:
        die("duplicate wild table labels: " + ", ".join(dup[:10]))
    grp["encounters"] += new
    maps_with = len({e["map"] for e in new})
    print(f"import_hns.py wild: {len(new)} tables for {maps_with} Johto maps "
          f"({before} -> {len(grp['encounters'])} in wild_encounters.json). " + ", ".join(f"{k} {v}" for k, v in sorted(notes.items())))
    if not dry:
        jsave("src/data/wild_encounters.json", wild)
