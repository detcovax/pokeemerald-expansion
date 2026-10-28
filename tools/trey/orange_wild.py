"""TREY (6c-5, TREY_PLAN.md D39/D44): the "wild" step of tools/trey/import_orange.py.

Writes the hack's wild tables for the Orange maps into src/data/wild_encounters.json, the same table for all four
times of day (D39). Read from the ROM: the hack's gWildMonHeaders (FireRed 1.0 code points at it from 0x82990),
entries {u8 group, u8 num, u16 pad, land*, water*, rock smash*, fishing*}, each info {u8 rate, pad, mons*},
mons {u8 min, u8 max, u16 species}; 12 / 5 / 5 / 10 slots (same slot layout and rates as TREY's).

  maps      matched by the hack's map number, recorded in each Orange scripts.inc header ("(map g.n)").
            The first table wins where the hack lists a map twice (FireRed does the same).
  empty     all-empty tables stay empty; maps without a table get none (D44).
  rock      the hack's empty Rock Smash tables get FRLG's Kanto list (Mt. Ember's, D44).
  extras    anime-canon additions (D44), each in the rarest slot of a species that appears at least twice in
            that table (the slot's levels are kept), so no native species is lost.
Re-running replaces the Orange tables.
"""
import collections
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orange_rom import Rom  # noqa: E402
import orange_maps  # noqa: E402

HEADERS_REF = 0x82990          # a FireRed 1.0 code literal that points at gWildMonHeaders
SLOTS = {"land_mons": 12, "water_mons": 5, "rock_smash_mons": 5, "fishing_mons": 10}
RATES = {"land_mons": [20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1], "water_mons": [60, 30, 5, 4, 1],
         "rock_smash_mons": [60, 30, 5, 4, 1], "fishing_mons": [70, 30, 60, 20, 20, 40, 40, 15, 4, 1]}
FISH_GROUPS = [[0, 1], [2, 3, 4], [5, 6, 7, 8, 9]]
TIMES = ["Morning", "Day", "Evening", "Night"]
ROCK_SMASH_SOURCE = "MAP_MT_EMBER_EXTERIOR"
# place (map name prefix) -> [(table, species)], applied in order (rarest slot first)
EXTRAS = {
    "GrapefruitIsles": [("land_mons", "SPECIES_SNORLAX")],                                  # EP094
    "FukuharaIsland": [("water_mons", "SPECIES_KABUTO"), ("fishing_mons", "SPECIES_KABUTO")],  # EP089
    "ShamoutiIsland": [("water_mons", "SPECIES_SLOWKING"), ("water_mons", "SPECIES_SLOWBRO"),
                       ("water_mons", "SPECIES_SLOWPOKE")],                                  # Movie 2
    "ValenciaPark": [("land_mons", "SPECIES_BUTTERFREE"), ("land_mons", "SPECIES_NIDORAN_F"),
                     ("land_mons", "SPECIES_NIDORAN_M")],                                    # EP083
    "PinkanIsland": [("land_mons", "SPECIES_PRIMEAPE"), ("land_mons", "SPECIES_EXEGGUTOR"),
                     ("land_mons", "SPECIES_RHYDON")],                                       # EP088
    "MurcottMeadows": [("land_mons", "SPECIES_PARAS")],                                     # EP097
    "TangeloIsland": [("water_mons", "SPECIES_LAPRAS")],                                    # EP084
    "OrangeSewers": [("land_mons", "SPECIES_BULBASAUR")],                                   # EP102
}


def die(msg):
    sys.exit(f"import_orange.py wild: {msg}")


def add_extra(mons, rates, species, groups=None, elsewhere=lambda sp: False, taken=None):
    """Put species in the rarest slot (within the Super Rod group for fishing) whose species is duplicated in this
    table or found on another Orange map, so no native species stops being catchable. Slots another extra took
    are skipped."""
    taken = taken if taken is not None else set()
    pools = groups or [list(range(len(mons)))]
    best = None
    for pool in pools:
        count = collections.Counter(mons[i]["species"] for i in pool)
        for i in pool:
            sp = mons[i]["species"]
            if i in taken or sp == species or not (count[sp] >= 2 or elsewhere(sp)):
                continue
            key = (rates[i], count[sp] < 2, -i)   # rarest; on a tie, a duplicated species first
            if best is None or key < best[0]:
                best = (key, i)
    if best is None:
        return False
    mons[best[1]] = dict(mons[best[1]], species=species)
    taken.add(best[1])
    return True


def step_wild(a):
    rom = Rom(a.rom)
    d = rom.d
    consts = orange_maps.Consts(a.pokefirered)
    groups = json.load(open("data/maps/map_groups.json", encoding="utf-8"))
    orange = {}
    for g in groups["group_order"]:
        if g.startswith("gMapGroup_Orange_"):
            for m in groups[g]:
                head = open(f"data/maps/{m}/scripts.inc", encoding="utf-8").read(300)
                k = re.search(r"\(map (\d+)\.(\d+)\)", head)
                j = json.load(open(f"data/maps/{m}/map.json", encoding="utf-8"))
                orange[(int(k.group(1)), int(k.group(2)))] = (m, j["id"])
    if not orange:
        die("import the maps first (import_orange.py maps)")
    wild = json.load(open("src/data/wild_encounters.json", encoding="utf-8"))
    grp = wild["wild_encounter_groups"][0]
    ids = {v[1] for v in orange.values()}
    before = len(grp["encounters"])
    grp["encounters"] = [e for e in grp["encounters"] if e.get("map") not in ids]
    rock_src = next((e["rock_smash_mons"] for e in grp["encounters"]
                     if e.get("map") == ROCK_SMASH_SOURCE and "rock_smash_mons" in e), None)
    if rock_src is None:
        die(f"{ROCK_SMASH_SOURCE} has no Rock Smash table to copy")

    o = rom.off(rom.u32(HEADERS_REF))
    seen, new, notes, tables = set(), [], collections.Counter(), []
    while d[o] != 0xFF:
        key = (d[o], d[o + 1])
        ptrs = struct.unpack_from("<IIII", d, o + 4)
        o += 20
        if key not in orange or key in seen:
            if key in seen:
                notes["second table for a map ignored"] += 1
            continue
        seen.add(key)
        name, mid = orange[key]
        out = {}
        for (field, n), p in zip(SLOTS.items(), ptrs):
            if not p:
                continue
            q = rom.off(p)
            rate, mp = d[q], struct.unpack_from("<I", d, q + 4)[0]
            mons = []
            for i in range(n):
                mn, mx, sp = struct.unpack_from("<BBH", d, rom.off(mp) + 4 * i)
                mons.append({"min_level": min(mn, mx), "max_level": max(mn, mx),
                             "species": consts.fr_species.get(sp, "SPECIES_NONE")})
            if all(m["species"] == "SPECIES_NONE" for m in mons):
                if field == "rock_smash_mons":
                    out[field] = json.loads(json.dumps(rock_src))
                    notes["Rock Smash: Kanto list"] += 1
                else:
                    notes[f"empty {field} skipped"] += 1
                continue
            if any(m["species"] == "SPECIES_NONE" or m["species"] not in consts.species for m in mons):
                die(f"{name} {field}: a slot TREY can't use: {mons}")
            out[field] = {"encounter_rate": rate, "mons": mons}
        if out:
            tables.append((name, mid, out))
    # extras (D44); "elsewhere" = the species is in another Orange map's table
    where = collections.defaultdict(set)
    for name, _, out in tables:
        for area in out.values():
            for m in area["mons"]:
                where[m["species"]].add(name)
    for name, mid, out in tables:
        place = next((p for p in EXTRAS if name == p or name.startswith(p + "_") or re.fullmatch(p + r"\d+", name)), None)
        taken = collections.defaultdict(set)
        for field, sp in EXTRAS.get(place, []):
            if field in out:
                ok = add_extra(out[field]["mons"], RATES[field], sp, FISH_GROUPS[2:] if field == "fishing_mons" else None,
                               lambda x: bool(where[x] - {name}), taken[field])
                notes[f"extra {sp[len('SPECIES_'):]}" + ("" if ok else " (no slot)")] += 1
        for t in TIMES:
            new.append(dict({"map": mid, "base_label": f"g{name}_{t}"}, **json.loads(json.dumps(out))))
    grp["encounters"] += new
    print(f"import_orange.py wild: {len(new) // 4} Orange maps x 4 times ({before} -> {len(grp['encounters'])} "
          f"tables). " + ", ".join(f"{k} {v}" for k, v in sorted(notes.items())))
    if not a.dry:
        with open("src/data/wild_encounters.json", "w", encoding="utf-8", newline="\n") as f:
            json.dump(wild, f, indent=2, ensure_ascii=False)
            f.write("\n")
