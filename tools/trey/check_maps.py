#!/usr/bin/env python3
"""TREY: map data checks (TREY_PLAN.md 3.1, 5.2, 5.5).

Run automatically by the build (see map_data_rules.mk) whenever map data changes,
or by hand from the repo root:  python3 tools/trey/check_maps.py

Checks:
  - map groups: at most 126 groups, at most 126 maps per group (WarpData stores them as s8,
    and 0x7F is reserved for MAP_DYNAMIC).
  - trey_layer_links: valid type, target map exists, source rectangle fits this map,
    destination rectangle fits the target map.
  - trey_season_layouts: valid season names, layout exists, same size as the map's normal layout
    (warps and events are shared between seasons, so the size must not change).
  - wild encounters (TREY_PLAN.md 5.8, D10): Hisuian forms only in Sinnoh, Paldean forms only in Kitakami.
  - sky_mons tables (3e) only on Sky maps.
"""
import json
import os
import re
import sys

MAX_GROUPS = 126
MAX_MAPS_PER_GROUP = 126
SEASONS = ("spring", "summer", "autumn", "winter")

errors = []


def error(msg):
    errors.append(msg)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_layer_types():
    path = "include/constants/trey_layers.h"
    with open(path, encoding="utf-8") as f:
        names = re.findall(r"#define\s+(LAYER_LINK_\w+)\s+\d+", f.read())
    return {n for n in names if n not in ("LAYER_LINK_NONE", "LAYER_LINK_TYPES_COUNT")}


# Region of each MAPSEC, mirroring TreyGetRegionOfMapsec() in src/trey_regions.c:
# an explicit "trey_region" on the section wins; otherwise FRLG Kanto sections are Kanto and the rest Hoenn.
def load_mapsec_regions():
    sections = load_json("src/data/region_map/region_map_sections.json")["map_sections"]
    ids = [s["id"] for s in sections]
    kanto_start = ids.index("MAPSEC_PALLET_TOWN") if "MAPSEC_PALLET_TOWN" in ids else None
    kanto_end = ids.index("MAPSEC_SPECIAL_AREA") if "MAPSEC_SPECIAL_AREA" in ids else None
    regions = {}
    for i, sec in enumerate(sections):
        if "trey_region" in sec:
            regions[sec["id"]] = sec["trey_region"]
        elif kanto_start is not None and kanto_end is not None and kanto_start <= i <= kanto_end:
            regions[sec["id"]] = "REGION_KANTO"
        else:
            regions[sec["id"]] = "REGION_HOENN"
    return regions


def regional_form_region(species):
    if species.endswith("_HISUI") or "_HISUI_" in species or species == "SPECIES_BASCULIN_WHITE_STRIPED":
        return "REGION_SINNOH"
    if "_PALDEA" in species:
        return "REGION_KITAKAMI"
    return None


def as_int(value, where, field):
    try:
        return int(value)
    except (TypeError, ValueError):
        error(f"{where}: '{field}' must be a number, got {value!r}")
        return None


def main():
    if not os.path.exists("Makefile"):
        print("check_maps.py: run from the project's root folder.")
        return 1

    groups = load_json("data/maps/map_groups.json")
    layouts = {l["id"]: l for l in load_json("data/layouts/layouts.json")["layouts"] if "id" in l}
    layer_types = load_layer_types()
    with open("include/constants/songs.h", encoding="utf-8") as f:
        songs = set(re.findall(r"#define\s+(MUS_\w+|SE_\w+|PH_\w+)\b", f.read()))

    # Map groups
    group_order = groups["group_order"]
    if len(group_order) > MAX_GROUPS:
        error(f"map_groups.json has {len(group_order)} groups; the limit is {MAX_GROUPS}.")
    map_folders = []
    for group in group_order:
        maps = groups[group]
        if len(maps) > MAX_MAPS_PER_GROUP:
            error(f"map group {group} has {len(maps)} maps; the limit is {MAX_MAPS_PER_GROUP}. Split it into two groups.")
        map_folders.extend(maps)

    # Load every map once
    maps_by_id = {}
    for folder in map_folders:
        path = f"data/maps/{folder}/map.json"
        if not os.path.exists(path):
            error(f"{path} is listed in map_groups.json but does not exist.")
            continue
        data = load_json(path)
        maps_by_id[data["id"]] = (folder, data)

    def layout_size(map_data):
        layout = layouts.get(map_data.get("layout"))
        if layout is None:
            return None
        return layout.get("width"), layout.get("height")

    for map_id, (folder, data) in maps_by_id.items():
        where = f"data/maps/{folder}/map.json"
        size = layout_size(data)

        music = data.get("music")
        if music and songs and music not in songs:
            error(f"{where}: music {music!r} is not defined in include/constants/songs.h.")
        if data.get("layout") not in layouts:
            error(f"{where}: layout {data.get('layout')!r} does not exist.")

        # Layer links
        links = data.get("trey_layer_links", [])
        if not isinstance(links, list):
            error(f"{where}: trey_layer_links must be a list.")
            links = []
        if len(links) > 255:
            error(f"{where}: more than 255 trey_layer_links.")
        for i, link in enumerate(links):
            lw = f"{where}: trey_layer_links[{i}]"
            if link.get("type") not in layer_types:
                error(f"{lw}: unknown type {link.get('type')!r}; expected one of {sorted(layer_types)}.")
            target = maps_by_id.get(link.get("map"))
            if target is None:
                error(f"{lw}: target map {link.get('map')!r} does not exist.")
            vals = {k: as_int(link.get(k), lw, k) for k in ("x", "y", "width", "height", "dest_x", "dest_y")}
            if None in vals.values():
                continue
            if vals["width"] <= 0 or vals["height"] <= 0:
                error(f"{lw}: width and height must be at least 1.")
                continue
            if size and None not in size:
                w, h = size
                if vals["x"] < 0 or vals["y"] < 0 or vals["x"] + vals["width"] > w or vals["y"] + vals["height"] > h:
                    error(f"{lw}: source rectangle ({vals['x']},{vals['y']} {vals['width']}x{vals['height']}) is outside this map ({w}x{h}).")
            if target is not None:
                tsize = layout_size(target[1])
                if tsize and None not in tsize:
                    tw, th = tsize
                    if vals["dest_x"] < 0 or vals["dest_y"] < 0 or vals["dest_x"] + vals["width"] > tw or vals["dest_y"] + vals["height"] > th:
                        error(f"{lw}: destination rectangle ({vals['dest_x']},{vals['dest_y']} {vals['width']}x{vals['height']}) is outside {link.get('map')} ({tw}x{th}).")

        # Seasonal layouts
        seasons = data.get("trey_season_layouts", {})
        if not isinstance(seasons, dict):
            error(f"{where}: trey_season_layouts must be an object.")
            seasons = {}
        for season, layout_id in seasons.items():
            if season not in SEASONS:
                error(f"{where}: trey_season_layouts has unknown season {season!r}; expected {SEASONS}.")
                continue
            if not layout_id:
                continue
            layout = layouts.get(layout_id)
            if layout is None:
                error(f"{where}: {season} layout {layout_id!r} does not exist.")
                continue
            if size and (layout.get("width"), layout.get("height")) != size:
                error(f"{where}: {season} layout {layout_id} is {layout.get('width')}x{layout.get('height')}, but the map's layout is {size[0]}x{size[1]}. Seasonal layouts must be the same size.")

    # Regional forms in wild encounter tables
    mapsec_regions = load_mapsec_regions()
    encounters = load_json("src/data/wild_encounters.json")
    for group in encounters["wild_encounter_groups"]:
        if not group.get("for_maps"):
            continue
        for enc in group["encounters"]:
            map_id = enc.get("map")
            entry = maps_by_id.get(map_id)
            if entry is None:
                continue
            region = mapsec_regions.get(entry[1].get("region_map_section"), "REGION_HOENN")
            if "sky_mons" in enc and entry[1].get("map_type") != "MAP_TYPE_SKY":
                error(f"wild_encounters.json {enc.get('base_label')}: sky_mons are only allowed on Sky maps (MAP_TYPE_SKY), but {map_id} is {entry[1].get('map_type')}.")
            for field, table in enc.items():
                if not isinstance(table, dict) or "mons" not in table:
                    continue
                for mon in table["mons"]:
                    species = mon.get("species", "")
                    needed = regional_form_region(species)
                    if needed and needed != region:
                        error(f"wild_encounters.json {enc.get('base_label')} ({field}): {species} may only appear in {needed}, but {map_id} is in {region}.")

    if errors:
        print("TREY map check failed:")
        for e in errors:
            print("  - " + e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
