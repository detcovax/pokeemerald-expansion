#!/usr/bin/env python3
"""TREY: wild encounters by season, time of day and weather (TREY_PLAN.md 5.11, D22; Phase 4 chunk 4b-2).

Reads docs/trey/wild_encounters.csv and writes src/data/trey/wild_encounters_trey.h (run by make).

One CSV row = one encounter table for one area of one map under some conditions:
    map       MAP_* id
    area      land, water, rock, fishing, hidden, sky
    seasons   all, or spring|summer|autumn|winter (any combination joined with |)
    times     all, or morning|day|evening|night
    weathers  all, or clear|rain|snow|sandstorm|fog|sun
    rate      the area's encounter rate (as encounter_rate in wild_encounters.json)
    slots     exact slots, separated by ';': "SPECIES_X 2-4" or "SPECIES_X 3". The count must match the
              area: land 12, water 5, rock 5, fishing 10 (old rod 0-1, good 2-4, super 5-9), hidden 3, sky 12.

Rules (checked here, the build fails on an error):
  - two rows for the same map and area must not cover the same season + time + weather;
  - a map that also has Emerald tables in wild_encounters.json: CSV rows override those (area by area) for
    the conditions they cover; everywhere else the Emerald tables apply ("every season, every weather").
  - a map only in this CSV is strict: no row for a condition = no encounters (D22).
"""
import csv
import json
import os
import re
import sys

CSV = "docs/trey/wild_encounters.csv"
OUT = "src/data/trey/wild_encounters_trey.h"
SEASONS = ["spring", "summer", "autumn", "winter"]
TIMES = ["morning", "day", "evening", "night"]   # enum TimeOfDay order
WEATHERS = ["clear", "rain", "snow", "sandstorm", "fog", "sun"]
AREAS = {"land": ("landMonsInfo", 12), "water": ("waterMonsInfo", 5), "rock": ("rockSmashMonsInfo", 5),
         "fishing": ("fishingMonsInfo", 10), "hidden": ("hiddenMonsInfo", 3), "sky": ("skyMonsInfo", 12)}


def mask(text, names, where):
    text = text.strip().lower()
    if text in ("all", "any", "*", ""):
        return (1 << len(names)) - 1
    m = 0
    for part in text.split("|"):
        part = part.strip()
        if part not in names:
            raise SystemExit(f"{where}: unknown value {part!r}; expected all or {'|'.join(names)}")
        m |= 1 << names.index(part)
    return m


def known_species():
    with open("include/constants/species.h", encoding="utf-8") as f:
        return set(re.findall(r"#define\s+(SPECIES_\w+)\b", f.read()))


def known_maps():
    groups = json.load(open("data/maps/map_groups.json", encoding="utf-8"))
    ids = set()
    for g in groups["group_order"]:
        for m in groups[g]:
            p = f"data/maps/{m}/map.json"
            if os.path.exists(p):
                ids.add(json.load(open(p, encoding="utf-8"))["id"])
    return ids


def main():
    errors = []
    rows = []
    species_ok = known_species()
    maps_ok = known_maps()
    if os.path.exists(CSV):
        with open(CSV, encoding="utf-8", newline="") as f:
            for n, row in enumerate(csv.DictReader(f), start=2):
                where = f"{CSV} line {n}"
                if not row.get("map") or row["map"].startswith("#"):
                    continue
                try:
                    area = row["area"].strip().lower()
                    if area not in AREAS:
                        raise SystemExit(f"{where}: unknown area {area!r}; expected one of {sorted(AREAS)}")
                    s = mask(row["seasons"], SEASONS, where)
                    t = mask(row["times"], TIMES, where)
                    w = mask(row["weathers"], WEATHERS, where)
                    slots = []
                    for part in [p.strip() for p in row["slots"].split(";") if p.strip()]:
                        m = re.fullmatch(r"(SPECIES_\w+)\s+(\d+)(?:\s*-\s*(\d+))?", part)
                        if not m:
                            raise SystemExit(f"{where}: bad slot {part!r}; expected 'SPECIES_X 2-4' or 'SPECIES_X 3'")
                        sp, lo, hi = m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))
                        if sp not in species_ok:
                            errors.append(f"{where}: unknown species {sp}")
                        if not (1 <= lo <= hi <= 100):
                            errors.append(f"{where}: bad levels {lo}-{hi}")
                        slots.append((sp, lo, hi))
                    if len(slots) != AREAS[area][1]:
                        errors.append(f"{where}: {area} needs {AREAS[area][1]} slots, found {len(slots)}")
                    if row["map"].strip() not in maps_ok:
                        errors.append(f"{where}: unknown map {row['map'].strip()}")
                    rows.append(dict(map=row["map"].strip(), area=area, s=s, t=t, w=w,
                                     rate=int(row["rate"]), slots=slots, where=where))
                except SystemExit as e:
                    errors.append(str(e))
    # overlaps
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a["map"] == b["map"] and a["area"] == b["area"] and a["s"] & b["s"] and a["t"] & b["t"] and a["w"] & b["w"]:
                errors.append(f"{b['where']}: overlaps {a['where']} ({a['map']} {a['area']}: same season, time and weather)")
    if errors:
        print("wild_csv.py failed:")
        for e in errors:
            print("  - " + e)
        sys.exit(1)

    # group rows with identical conditions into one entry per map
    out = ["// TREY (4b-2): generated by tools/trey/wild_csv.py from docs/trey/wild_encounters.csv; do not edit.", ""]
    maps = {}
    for r in rows:
        maps.setdefault(r["map"], {}).setdefault((r["s"], r["t"], r["w"]), []).append(r)
    tables = {}
    for mi, (mapid, entries) in enumerate(maps.items()):
        for ei, (cond, rs) in enumerate(entries.items()):
            for r in rs:
                key = (r["rate"], tuple(r["slots"]))
                if key not in tables:
                    k = len(tables)
                    tables[key] = k
                    out.append(f"static const struct WildPokemon sTreyWildMons_{k}[] =\n{{")
                    for sp, lo, hi in r["slots"]:
                        out.append(f"    {{{lo}, {hi}, {sp}}},")
                    out.append("};")
                    out.append(f"static const struct WildPokemonInfo sTreyWildInfo_{k} = {{{r['rate']}, sTreyWildMons_{k}}};")
            out.append(f"static const struct WildEncounterTypes sTreyWildTypes_{mi}_{ei} =\n{{")
            for r in rs:
                out.append(f"    .{AREAS[r['area']][0]} = &sTreyWildInfo_{tables[(r['rate'], tuple(r['slots']))]},")
            out.append("};")
        out.append(f"static const struct TreyWildEntry sTreyWildEntries_{mi}[] =\n{{")
        for ei, cond in enumerate(entries):
            out.append(f"    {{0x{cond[0]:02X}, 0x{cond[1]:02X}, 0x{cond[2]:02X}, 0, &sTreyWildTypes_{mi}_{ei}}},")
        out.append("};\n")
    out.append("const struct TreyWildMap gTreyWildMaps[] =\n{")
    for mi, (mapid, entries) in enumerate(maps.items()):
        out.append(f"    {{MAP_GROUP({mapid}), MAP_NUM({mapid}), {len(entries)}, 0, sTreyWildEntries_{mi}}},")
    if not maps:
        out.append("    {0, 0, 0, 0, NULL},")
    out.append("};")
    out.append(f"const u16 gTreyWildMapCount = {len(maps)};")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    text = "\n".join(out) + "\n"
    if not os.path.exists(OUT) or open(OUT, encoding="utf-8").read() != text:
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print(f"wild_csv.py: {len(rows)} tables on {len(maps)} maps")


if __name__ == "__main__":
    if not os.path.exists("Makefile"):
        print("Run from the project's root folder.")
        sys.exit(1)
    main()
