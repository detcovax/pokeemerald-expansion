#!/usr/bin/env python3
"""TREY: apply the species roster (TREY_PLAN.md 5.8).

Run from the repo root:  python3 tools/trey/apply_roster.py

Reads docs/trey/species_roster.csv and rewrites the Gen 5-9 family switches in
include/config/species_enabled.h: listed families -> TRUE, every other Gen 5-9 family -> FALSE.
Gen 1-4 families are never touched. P_GEN_5..9_POKEMON stay TRUE on purpose: NATIONAL_DEX_COUNT
depends on them, and Gen 9 roster species (Ogerpon, #1017) need the full National Dex.
Safe to run again after editing the CSV.
"""
import csv
import os
import re
import sys

CONFIG = "include/config/species_enabled.h"
ROSTER = "docs/trey/species_roster.csv"

LINE = re.compile(r"^(#define P_FAMILY_(\w+)\s+)(P_GEN_([5-9])_POKEMON|TRUE|FALSE)(\s*//\s*TREY.*)?$")


def main():
    if not os.path.exists("Makefile"):
        print("apply_roster.py: run from the project's root folder.")
        return 1

    roster = {}
    with open(ROSTER, encoding="utf-8") as f:
        rows = [r for r in f if r.strip() and not r.lstrip().startswith("#")]
    for row in csv.DictReader(rows):
        roster[row["family"].strip()] = row["source"].strip()

    with open(CONFIG, encoding="utf-8") as f:
        lines = f.read().split("\n")

    seen = set()
    on = off = 0
    out = []
    for line in lines:
        m = LINE.match(line)
        if not m:
            out.append(line)
            continue
        prefix, family, value, gen = m.group(1), m.group(2), m.group(3), m.group(4)
        # Only touch Gen 5-9 families: either still the original P_GEN_n value, or a value this script wrote.
        if gen is None and m.group(5) is None:
            out.append(line)
            continue
        if family in roster:
            out.append(f"{prefix}TRUE  // TREY roster: {roster[family]}")
            seen.add(family)
            on += 1
        else:
            out.append(f"{prefix}FALSE // TREY: not in roster")
            off += 1

    missing = sorted(set(roster) - seen)
    if missing:
        print("apply_roster.py: these roster families were not found in species_enabled.h: " + ", ".join(missing))
        return 1

    with open(CONFIG, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"apply_roster.py: {on} Gen 5-9 families on, {off} off.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
