#!/usr/bin/env python3
"""TREY (5d, TREY_PLAN.md 5.7a, D24): check every TREY trainer's team against its tier.

Reads include/constants/opponents.h (TREY_TRAINERS_START and the TRAINER_* ids after it),
docs/trey/trainer_tiers.csv (trainer -> boss/gym/route), include/config/trey.h (TREY_TRAINER_LEVEL)
and src/data/trainers.party. Exits with an error listing every problem (make stops). Run from the root.
"""
import csv
import os
import re
import sys

PARTY = "src/data/trainers.party"
TIERS_CSV = "docs/trey/trainer_tiers.csv"

TIERS = {
    #        team size  IVs   EVs min..max   need nature/ability  held item  AI flags needed
    "boss":  ((6, 6),   31,   (500, 510),    True,                True,      [["Smart Trainer"], ["Prediction"], ["Ace Pokemon"]]),
    "gym":   ((2, 4),   15,   (0, 256),      True,                False,     [["Smart Trainer"]]),
    "route": ((1, 3),   None, (0, 0),        False,               False,     [["Basic Trainer", "Smart Trainer"], ["Energy Aware", "Smart Trainer"]]),
}
STATS = ("HP", "Atk", "Def", "SpA", "SpD", "Spe")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def strip_comments(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def parse_party(text):
    """trainer id -> {'header': {key: value}, 'mons': [ {fields} ]}"""
    trainers = {}
    for block in re.split(r"^=== ", strip_comments(text), flags=re.M)[1:]:
        head, _, rest = block.partition("\n")
        tid = head.strip().rstrip("=").strip()
        lines = rest.split("\n")
        header, i = {}, 0
        while i < len(lines) and lines[i].strip():
            k, _, v = lines[i].partition(":")
            header[k.strip()] = v.strip()
            i += 1
        mons, cur = [], None
        for line in lines[i:]:
            s = line.strip()
            if not s:
                cur = None
                continue
            if cur is None:
                cur = {"line": s, "item": "@" in s, "moves": 0}
                mons.append(cur)
                continue
            if s.startswith("- "):
                cur["moves"] += 1
            elif s.endswith(" Nature"):
                cur["Nature"] = s[:-len(" Nature")]
            else:
                k, _, v = s.partition(":")
                cur[k.strip()] = v.strip()
        trainers[tid] = {"header": header, "mons": mons}
    return trainers


def stat_spread(value, default):
    vals = dict.fromkeys(STATS, default)
    for part in value.split("/"):
        m = re.match(r"\s*(\d+)\s+(\w+)\s*$", part)
        if m and m.group(2) in vals:
            vals[m.group(2)] = int(m.group(1))
    return vals


def main():
    if not os.path.exists("Makefile"):
        sys.exit("check_trainers.py: run from the project's root folder.")
    opp = read("include/constants/opponents.h")
    start = int(re.search(r"#define\s+TREY_TRAINERS_START\s+(\d+)", opp).group(1))
    trey_ids = [n for n, v in re.findall(r"#define\s+(TRAINER_\w+)\s+(\d+)\b", opp) if int(v) >= start]
    level = int(re.search(r"#define\s+TREY_TRAINER_LEVEL\s+(\d+)", read("include/config/trey.h")).group(1))
    with open(TIERS_CSV, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(l for l in f if l.strip() and not l.startswith("#"))]
    tiers = {r["trainer"].strip(): r["tier"].strip() for r in rows}
    party = parse_party(read(PARTY))

    errors = []
    for tid in trey_ids:
        if tid not in tiers:
            errors.append(f"{tid}: no tier in {TIERS_CSV}")
    for tid, tier in tiers.items():
        where = tid
        if tid not in trey_ids:
            errors.append(f"{where}: in {TIERS_CSV} but not a TREY trainer id in opponents.h")
            continue
        if tier not in TIERS:
            errors.append(f"{where}: unknown tier {tier!r} (boss, gym, route)")
            continue
        if tid not in party:
            errors.append(f"{where}: no team in {PARTY}")
            continue
        (lo, hi), ivs, (ev_lo, ev_hi), need_set, need_item, ai_groups = TIERS[tier]
        t = party[tid]
        ai = [a.strip() for a in t["header"].get("AI", "").split("/") if a.strip()]
        for group in ai_groups:
            if not any(g in ai for g in group):
                errors.append(f"{where} ({tier}): AI needs {' or '.join(group)} (has: {', '.join(ai) or 'none'})")
        n = len(t["mons"])
        if not lo <= n <= hi:
            errors.append(f"{where} ({tier}): {n} Pokémon, tier needs {lo}-{hi}")
        for i, m in enumerate(t["mons"], 1):
            mw = f"{where} #{i} {m['line']}"
            if int(m.get("Level", "100")) != level:
                errors.append(f"{mw}: level {m.get('Level', '100')}, every TREY trainer is level {level} (TREY_TRAINER_LEVEL)")
            if ivs is not None:
                got = stat_spread(m.get("IVs", ""), 31)
                if any(v != ivs for v in got.values()):
                    errors.append(f"{mw}: IVs must all be {ivs}")
            ev_total = sum(stat_spread(m.get("EVs", ""), 0).values())
            if not ev_lo <= ev_total <= ev_hi:
                errors.append(f"{mw}: EV total {ev_total}, tier needs {ev_lo}-{ev_hi}")
            if need_set and "Nature" not in m:
                errors.append(f"{mw}: needs a nature")
            if need_set and "Ability" not in m:
                errors.append(f"{mw}: needs an ability")
            if need_item and not m["item"]:
                errors.append(f"{mw}: needs a held item")
            if m["moves"] == 0:
                errors.append(f"{mw}: no moves listed")

    if errors:
        print("TREY trainer tier check failed:")
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    print(f"check_trainers.py: {len(tiers)} TREY trainers OK (level {level})")


if __name__ == "__main__":
    main()
