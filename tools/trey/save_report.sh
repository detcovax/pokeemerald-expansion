#!/usr/bin/env bash
# TREY: prints how much of each save block is used.
# Run with:  make trey-save-report
# Arguments (passed by the Makefile): <gcc> <nm> <preprocessor flags...>
set -euo pipefail

CC="$1"
NM="$2"
shift 2

OUT_DIR="build/trey"
OUT="$OUT_DIR/save_report.o"
mkdir -p "$OUT_DIR"

"$CC" "$@" -mthumb -mabi=apcs-gnu -march=armv4t -fno-common -w -c tools/trey/save_report.c -o "$OUT"

"$NM" -S "$OUT" | awk '
    function hex(s,    i, c, v) {
        v = 0; s = tolower(s)
        for (i = 1; i <= length(s); i++) { c = index("0123456789abcdef", substr(s, i, 1)) - 1; v = v * 16 + c }
        return v
    }
    $4 ~ /^gTreyMeasure_/ {
        name = $4; sub(/^gTreyMeasure_/, "", name)
        size = hex($2)
        split(name, parts, "_")
        kind = parts[1]; what = substr(name, length(kind) + 2)
        if (kind == "Used")  used[what]  = size
        if (kind == "Limit") limit[what] = size
        if (kind == "Info")  info[what]  = size
    }
    END {
        n = split("SaveBlock1 SaveBlock2 SaveBlock3 PokemonStorage", blocks, " ")
        printf "\n%-16s %8s %8s %8s %7s\n", "Block", "Used", "Limit", "Free", "Used%"
        printf "%-16s %8s %8s %8s %7s\n", "-----", "----", "-----", "----", "-----"
        for (i = 1; i <= n; i++) {
            b = blocks[i]
            printf "%-16s %8d %8d %8d %6.1f%%\n", b, used[b], limit[b], limit[b] - used[b], 100 * used[b] / limit[b]
        }
        printf "\nflags[] %d B, vars[] %d B, BoxPokemon %d B, struct Time %d B\n\n", info["Flags"], info["Vars"], info["BoxPokemon"], info["Time"]
    }'
