#!/usr/bin/env python3
"""TREY: regional Pokédex membership (TREY_PLAN.md E13, Phase 4 chunk 4d).

Reads docs/trey/dex/<region>.txt and writes src/data/trey/dex_regions.h (run by make).

Each list file: '#' comment lines, then one National Pokédex number per line in the canon regional order
(the order is kept in the file for reference only: TREY numbers every Pokémon by the order the player
discovers it, so the game only needs to know WHICH Pokémon belong to each regional dex).

    kanto.txt     FRLG Kanto dex (151)
    orange.txt    Orange Islands (optional: no canon list; filled from the Orange encounter tables in Phase 6)
    johto.txt     HGSS Johto dex (256)
    hoenn.txt     ORAS Hoenn dex (211)
    sinnoh.txt    Platinum Sinnoh dex (210)
    kitakami.txt  Teal Mask Kitakami dex (200)

Output: gTreyDexRegionMask[national number] = bit (1 << TREY_DEX_*) for every regional dex the Pokémon is in.
The National dex (TREY_DEX_NATIONAL, bit 0) is everything, so it is never stored.
"""
import os
import re
import sys

DEX_DIR = "docs/trey/dex"
OUT = "src/data/trey/dex_regions.h"
POKEDEX_H = "include/constants/pokedex.h"
TREY_DEX_H = "include/constants/trey_dex.h"
SPECIES_ENABLED = "include/config/species_enabled.h"
SPECIES_INFO = "src/data/pokemon/species_info/gen_{}_families.h"
# Must match include/constants/trey_dex.h
REGIONS = [("kanto", "TREY_DEX_KANTO", True), ("orange", "TREY_DEX_ORANGE", False), ("johto", "TREY_DEX_JOHTO", True),
           ("hoenn", "TREY_DEX_HOENN", True), ("sinnoh", "TREY_DEX_SINNOH", True), ("kitakami", "TREY_DEX_KITAKAMI", True)]


def national_names():
    with open(POKEDEX_H, encoding="utf-8") as f:
        text = f.read()
    start = text.index("NATIONAL_DEX_NONE")
    body = text[start:text.index("}", start)]
    names = re.findall(r"^\s*(NATIONAL_DEX_\w+)\s*,", body, re.M)
    return names  # index = national number


def roster_national_numbers(names):
    """National numbers of every species in the game's roster (families switched on in species_enabled.h).
    Conditions nested inside a family (cross-gen evolutions, forms) count as on, so this can only overcount."""
    defines = {}
    with open(SPECIES_ENABLED, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"#define\s+(P_\w+)\s+(\w+)", line)
            if m:
                defines[m.group(1)] = m.group(2)

    def on(name, depth=0):
        value = defines.get(name, "FALSE")
        if value in ("TRUE", "FALSE"):
            return value == "TRUE"
        return depth < 4 and on(value, depth + 1)

    index = {n: i for i, n in enumerate(names)}
    found = set()
    for gen in range(1, 10):
        family = None
        with open(SPECIES_INFO.format(gen), encoding="utf-8") as f:
            for line in f:
                m = re.match(r"#if\s+(P_FAMILY_\w+)\s*$", line)
                if m:
                    family = m.group(1)
                    continue
                if family and re.match(r"#endif\s*//\s*" + family + r"\b", line):
                    family = None
                    continue
                m = re.search(r"\.natDexNum\s*=\s*(NATIONAL_DEX_\w+)", line)
                if m and family and on(family) and m.group(1) in index:
                    found.add(index[m.group(1)])
    return found


def order_max():
    with open(TREY_DEX_H, encoding="utf-8") as f:
        return int(re.search(r"#define\s+TREY_DEX_ORDER_MAX\s+(\d+)", f.read()).group(1))


def main():
    if not os.path.exists("Makefile"):
        print("dex_lists.py: run from the project's root folder.")
        return 1
    names = national_names()
    errors = []
    masks = {}
    counts = {}
    for region, const, required in REGIONS:
        path = os.path.join(DEX_DIR, region + ".txt")
        if not os.path.exists(path):
            if required:
                errors.append(f"{path}: missing")
            counts[const] = 0
            continue
        seen = set()
        with open(path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue
                if not line.isdigit():
                    errors.append(f"{path}:{lineno}: '{line}' is not a National Pokédex number")
                    continue
                num = int(line)
                if num <= 0 or num >= len(names):
                    errors.append(f"{path}:{lineno}: {num} is out of range")
                    continue
                if num in seen:
                    errors.append(f"{path}:{lineno}: {num} is listed twice")
                    continue
                seen.add(num)
                masks.setdefault(num, []).append(const)
        counts[const] = len(seen)
    # The discovery list (10-bit National numbers, TREY_DEX_ORDER_MAX entries) must hold the whole roster.
    roster = roster_national_numbers(names)
    limit = order_max()
    if len(roster) > limit:
        errors.append(f"the roster has {len(roster)} Pokémon but TREY_DEX_ORDER_MAX is {limit}: raise it in {TREY_DEX_H}")
    too_big = sorted(n for n in roster if n > 1023)
    if too_big:
        errors.append("National numbers above 1023 don't fit the 10-bit discovery list: " + ", ".join(names[n] for n in too_big))
    if errors:
        for e in errors:
            print("dex_lists.py: error: " + e)
        return 1

    out = ["// Generated by tools/trey/dex_lists.py from docs/trey/dex/*.txt. Do not edit.", ""]
    for _, const, _ in REGIONS:
        out.append(f"// {const}: {counts[const]} Pokémon")
    out.append("")
    out.append("const u8 gTreyDexRegionMask[NATIONAL_DEX_COUNT + 1] =")
    out.append("{")
    for num in sorted(masks):
        bits = " | ".join(f"TREY_DEX_BIT({c})" for c in masks[num])
        out.append(f"    [{names[num]}] = {bits},")
    out.append("};")
    out.append("")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    text = "\n".join(out)
    if not os.path.exists(OUT) or open(OUT, encoding="utf-8").read() != text:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(text)
    print(f"dex_lists.py: {len(masks)} Pokémon in regional dexes, roster {len(roster)}/{limit} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
