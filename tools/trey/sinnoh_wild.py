"""TREY (6b-5, TREY_PLAN.md D38): the "wild" step of tools/trey/import_sinnoh.py.

Writes Platinum's wild tables for the Sinnoh maps into src/data/wild_encounters.json. Source: pret/pokeplatinum's
res/field/encounters/encounters_<name>.json, saved as <name>.json in the --plat folder.

  times     Platinum's base table = Morning; Day = base with slots 2-3 replaced by Platinum's day species;
            Evening and Night = the night species (D33).
  land      12 slots (Gen 3 and 4 rates match); Platinum's one level per slot -> min = max.
  surf      5 slots as given.
  fishing   TREY's 10 slots = Old Rod 0-1, Good Rod 0-2, Super Rod 0-4 (Gen 3 and 4 Super Rod rates match).
  skipped   swarms, Poke Radar, dual-slot (GBA), honey trees, Feebas tiles.
  forms     Hisuian forms alongside the normal form (D38: rarest slot of the species, or the table's rarest
            other slot if it fills only one); Shellos/Gastrodon East Sea form east of Mt. Coronet, West Sea form west.
Re-running replaces the Sinnoh tables. Sinnoh maps without a Platinum table have none (D22).
"""
import collections
import json
import os
import sys

PLAT_FILES = {   # Platinum file -> TREY map(s)
    **{f"route_{n}": [f"Route{n}"] for n in list(range(201, 204)) + list(range(206, 210)) + list(range(213, 231))},
    "route_204_south": ["Route204"],   # the repo has one Route 204; Platinum's south half (next to Jubilife)
    "route_205_south": ["Route205_South"], "route_205_north": ["Route205_North"],
    "route_210_south": ["Route210_South"], "route_210_north": ["Route210_North"],
    "route_211_west": ["Route211_West"], "route_211_east": ["Route211_East"],
    "route_212_north": ["Route212_North"], "route_212_south": ["Route212_South"],
    "twinleaf_town": ["TwinleafTown"], "celestic_town": ["CelesticTown"], "canalave_city": ["CanalaveCity"],
    "eterna_city": ["EternaCity"], "pastoria_city": ["PastoriaCity"], "sunyshore_city": ["SunyshoreCity"],
    "pokemon_league": ["SinnohPokemonLeague"], "resort_area": ["ResortArea"],
    "oreburgh_mine_b1f": ["OreburghMine_B1F"], "oreburgh_mine_b2f": ["OreburghMine_B2F"],
    "oreburgh_gate_1f": ["OreburghGate_1F"], "ravaged_path": ["RavagedPath"],
    "valley_windworks_outside": ["ValleyWindworks"], "eterna_forest": ["EternaForest"],
    "mt_coronet_1f_south": ["MtCoronet_1F_South"], "mt_coronet_b1f": ["MtCoronet_B1F"],
    "mt_coronet_1f_north_room_1": ["MtCoronet_1F_North_Room1"], "mt_coronet_1f_north_room_2": ["MtCoronet_1F_North_Room2"],
    "old_chateau": ["OldChateau_Entrance"], "old_chateau_dining_area": ["OldChateau_DiningRoom"],
    "old_chateau_side_rooms": ["OldChateau_SideRoom_1", "OldChateau_SideRoom_2"], "old_chateau_corridor": ["OldChateau_2F"],
    "lake_verity": ["LakeVerity"], "lake_valor": ["LakeValor"], "lake_acuity": ["LakeAcuity"],
    "valor_lakefront": ["ValorLakefront"], "acuity_lakefront": ["AcuityLakefront"],
}
LAND_RATES = [20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1]
WATER_RATES = [60, 30, 5, 4, 1]
FISH_BLOCKS = [("old", [0, 1], [70, 30]), ("good", [0, 1, 2], [60, 20, 20]), ("super", [0, 1, 2, 3, 4], [40, 40, 15, 4, 1])]
HISUI = {"SPECIES_SNEASEL": "SPECIES_SNEASEL_HISUI", "SPECIES_QWILFISH": "SPECIES_QWILFISH_HISUI",
         "SPECIES_VOLTORB": "SPECIES_VOLTORB_HISUI", "SPECIES_GROWLITHE": "SPECIES_GROWLITHE_HISUI"}
EAST_SEA = {"Route213", "Route214", "Route215", "Route222", "Route223", "Route224", "Route225", "Route226", "Route227",
            "Route228", "Route229", "Route230", "PastoriaCity", "SunyshoreCity", "SinnohPokemonLeague", "ValorLakefront",
            "LakeValor", "ResortArea"}
TIMES = {"Morning": None, "Day": "day", "Evening": "night", "Night": "night"}


def die(msg):
    sys.exit(f"import_sinnoh.py wild: {msg}")


def jload(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def add_hisuian(mons, rates, notes):
    order = sorted(range(len(mons)), key=lambda i: (rates[i], -i))   # rarest first; later slots first on ties
    for base, hisui in HISUI.items():
        slots = [i for i, m in enumerate(mons) if m["species"] == base]
        if not slots:
            continue
        if len(slots) >= 2:
            target = min(slots, key=lambda i: (rates[i], -i))
            mons[target] = dict(mons[target], species=hisui)
        else:
            target = next(i for i in order if i != slots[0])
            mons[target] = dict(mons[slots[0]], species=hisui)
        notes[f"{hisui[len('SPECIES_'):]} slot"] += 1
    return mons


def step_wild(plat, dry):
    groups = jload("data/maps/map_groups.json")
    sinnoh = {}
    for g in groups["group_order"]:
        if g.startswith("gMapGroup_Sinnoh_"):
            for m in groups[g]:
                sinnoh[m] = jload(os.path.join("data/maps", m, "map.json"))["id"]
    if not sinnoh:
        die("import the maps first (import_sinnoh.py maps)")
    wild = jload("src/data/wild_encounters.json")
    grp = wild["wild_encounter_groups"][0]
    ids = set(sinnoh.values())
    before = len(grp["encounters"])
    grp["encounters"] = [e for e in grp["encounters"] if e.get("map") not in ids]
    notes, new = collections.Counter(), []
    for fname, maps in PLAT_FILES.items():
        path = os.path.join(plat, fname + ".json")
        if not os.path.exists(path):
            die(f"missing {path}")
        p = jload(path)
        for m in maps:
            if m not in sinnoh:
                die(f"{fname}: TREY has no map {m}")
            east = m in EAST_SEA

            def form(sp):
                if sp in ("SPECIES_SHELLOS", "SPECIES_GASTRODON"):
                    notes["East Sea form" if east else "West Sea form"] += 1
                    return sp + ("_EAST" if east else "_WEST")
                return sp
            for t, swap in TIMES.items():
                out = {}
                land = [dict(min_level=s["level"], max_level=s["level"], species=s["species"]) for s in p["land_encounters"]]
                if p.get("land_rate") and any(s["species"] != "SPECIES_NONE" for s in land):
                    if swap:
                        land[2]["species"], land[3]["species"] = p[swap][0], p[swap][1]
                    for s in land:
                        s["species"] = form(s["species"])
                    out["land_mons"] = {"encounter_rate": p["land_rate"], "mons": add_hisuian(land, LAND_RATES, notes)}
                surf = [dict(min_level=s["level_min"], max_level=s["level_max"], species=form(s["species"]))
                        for s in p["surf_encounters"]]
                if p.get("surf_rate") and any(s["species"] != "SPECIES_NONE" for s in surf):
                    out["water_mons"] = {"encounter_rate": p["surf_rate"], "mons": add_hisuian(surf, WATER_RATES, notes)}
                if p.get("old_rod_rate") or p.get("good_rod_rate") or p.get("super_rod_rate"):
                    fish = []
                    for rod, idx, rates in FISH_BLOCKS:
                        enc = p[f"{rod}_rod_encounters"]
                        block = [dict(min_level=enc[i]["level_min"], max_level=enc[i]["level_max"],
                                      species=form(enc[i]["species"])) for i in idx]
                        fish += add_hisuian(block, rates, notes)
                    if all(s["species"] != "SPECIES_NONE" for s in fish):
                        out["fishing_mons"] = {"encounter_rate": 20, "mons": fish}
                    else:
                        notes["fishing table with empty rod slots dropped"] += 1
                if not out:
                    continue
                for area in out.values():
                    for s in area["mons"]:
                        if s["min_level"] > s["max_level"]:
                            s["min_level"], s["max_level"] = s["max_level"], s["min_level"]
                new.append(dict({"map": sinnoh[m], "base_label": f"g{m}_{t}"}, **out))
    grp["encounters"] += new
    print(f"import_sinnoh.py wild: {len(new)} tables for {len({e['map'] for e in new})} Sinnoh maps "
          f"({before} -> {len(grp['encounters'])} in wild_encounters.json). "
          + ", ".join(f"{k} {v}" for k, v in sorted(notes.items())))
    if not dry:
        with open("src/data/wild_encounters.json", "w", encoding="utf-8", newline="\n") as f:
            json.dump(wild, f, indent=2, ensure_ascii=False)
            f.write("\n")
