#!/usr/bin/env python3
"""TREY (6-G, TREY_PLAN.md D36): compact map groups in every region.

Rewrites data/maps/map_groups.json so each region uses a few large groups instead of one per town (126 groups max;
92 were used before this). Maps keep their order inside each new group. Only group membership changes: map ids
(MAP_*) stay the same, so scripts and data that name maps are unaffected; map group/number VALUES change (old
saves are rejected through TREY_SAVE_VERSION).

Run from the project root:  python3 tools/trey/regroup_maps.py [--dry]
It is idempotent: groups already in the new scheme pass through. Re-run it after any import step that adds groups
in the old style (import_frlg.py / hns_maps.py create per-town groups).

Engine notes: Hoenn's outdoor group stays group 0 (Emerald's abnormal weather and legendary music check it);
the Pokédex area screen finds Hoenn's groups through MAP_GROUP(MAP_PETALBURG_CITY) etc., so it follows the maps.
"""
import json
import re
import sys

# Old group -> new group. Order of NEW_ORDER is the group order in the ROM.
HOENN_WEST = ["Littleroot", "Oldale", "Dewford", "Lavaridge", "Fallarbor", "Verdanturf", "Petalburg", "Slateport",
              "Mauville", "Rustboro", "Route104", "Route104Prototype", "Route109", "Route110", "Route111", "Route112",
              "Route113", "Route114", "Route116", "Route117"]
HOENN_EAST = ["Pacifidlog", "Fortree", "Lilycove", "Mossdeep", "Sootopolis", "EverGrande", "Route119", "Route121",
              "Route123", "Route124"]
JOHTO_WEST = ["NewBark", "Cherrygrove", "Violet", "Azalea", "Goldenrod", "Ecruteak", "Olivine", "Cianwood"]
JOHTO_EAST = ["Mahogany", "Blackthorn", "Routes", "Sinjoh", "SSAqua"]

NEW_ORDER = [
    "gMapGroup_Hoenn_Outdoor", "gMapGroup_Hoenn_Dungeon", "gMapGroup_Hoenn_Special", "gMapGroup_Hoenn_Indoor_Dynamic",
    "gMapGroup_Hoenn_Indoor_West", "gMapGroup_Hoenn_Indoor_East",
    "gMapGroup_Kanto_Outdoor", "gMapGroup_Kanto_Dungeon", "gMapGroup_Kanto_Special",
    "gMapGroup_Kanto_Indoor_Mainland", "gMapGroup_Kanto_Indoor_Sevii",
    "gMapGroup_Johto_Outdoor", "gMapGroup_Johto_Dungeon", "gMapGroup_Johto_Indoor_West", "gMapGroup_Johto_Indoor_East",
]


def new_group(old):
    if old in NEW_ORDER or old.startswith(("gMapGroup_Sinnoh_", "gMapGroup_Orange_", "gMapGroup_Kitakami_")) \
            or old == "gMapGroup_TreyTest":
        return old
    fixed = {"gMapGroup_TownsAndRoutes": "gMapGroup_Hoenn_Outdoor", "gMapGroup_Dungeons": "gMapGroup_Hoenn_Dungeon",
             "gMapGroup_SpecialArea": "gMapGroup_Hoenn_Special", "gMapGroup_IndoorDynamic": "gMapGroup_Hoenn_Indoor_Dynamic",
             "gMapGroup_TownsAndRoutes_Frlg": "gMapGroup_Kanto_Outdoor", "gMapGroup_Dungeons_Frlg": "gMapGroup_Kanto_Dungeon",
             "gMapGroup_SpecialArea_Frlg": "gMapGroup_Kanto_Special", "gMapGroup_Link_Frlg": "gMapGroup_Kanto_Special",
             "gMapGroup_Johto_Outdoor_Safari": "gMapGroup_Johto_Outdoor"}
    if old in fixed:
        return fixed[old]
    m = re.fullmatch(r"gMapGroup_Indoor(\w+?)_Frlg", old)
    if m:
        return "gMapGroup_Kanto_Indoor_Sevii" if "Island" in m.group(1) else "gMapGroup_Kanto_Indoor_Mainland"
    m = re.fullmatch(r"gMapGroup_Indoor(\w+)", old)
    if m and m.group(1) in HOENN_WEST:
        return "gMapGroup_Hoenn_Indoor_West"
    if m and m.group(1) in HOENN_EAST:
        return "gMapGroup_Hoenn_Indoor_East"
    m = re.fullmatch(r"gMapGroup_Johto_Indoor_(\w+)", old)
    if m and m.group(1) in JOHTO_WEST:
        return "gMapGroup_Johto_Indoor_West"
    if m and m.group(1) in JOHTO_EAST:
        return "gMapGroup_Johto_Indoor_East"
    sys.exit(f"regroup_maps.py: no rule for {old} (add it to the tables)")


def main():
    dry = "--dry" in sys.argv
    path = "data/maps/map_groups.json"
    data = json.load(open(path, encoding="utf-8"))
    out, order = {}, []
    for old in data["group_order"]:
        new = new_group(old)
        if new not in out:
            out[new] = []
        out[new].extend(data[old])
    # NEW_ORDER first (Hoenn_Outdoor = group 0), then anything else in its existing order (TreyTest, Sinnoh, ...)
    order = [g for g in NEW_ORDER if g in out] + [g for g in out if g not in NEW_ORDER]
    for g in order:
        if len(out[g]) > 126:
            sys.exit(f"regroup_maps.py: {g} would hold {len(out[g])} maps (max 126); split it")
    result = {"group_order": order}
    for g in order:
        result[g] = out[g]
    # keep any non-group keys map_groups.json may carry (connections_include_order, ...)
    for k, v in data.items():
        if k != "group_order" and k not in data["group_order"]:
            result[k] = v
    print(f"regroup_maps.py: {len(data['group_order'])} groups -> {len(order)}")
    for g in order:
        print(f"  {g:36} {len(out[g]):3} maps")
    if not dry:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            f.write("\n")


if __name__ == "__main__":
    main()
