#ifndef GUARD_CONSTANTS_TREY_DEX_H
#define GUARD_CONSTANTS_TREY_DEX_H

// TREY (TREY_PLAN.md E13, Phase 4 chunk 4d): regional Pokédexes. #defines only (read by scripts too).
// Order = the Pokédex region menu order (same as the region map pages).
#define TREY_DEX_NATIONAL   0 // always available
#define TREY_DEX_KANTO      1
#define TREY_DEX_ORANGE     2
#define TREY_DEX_JOHTO      3
#define TREY_DEX_HOENN      4
#define TREY_DEX_SINNOH     5
#define TREY_DEX_KITAKAMI   6
#define TREY_DEX_COUNT      7

#define TREY_DEX_BIT(dex)   (1 << (dex))

// Discovery order (4d): every Pokémon gets the next number the first time it is SEEN. The list of
// National numbers in that order lives at the end of the PC storage block, 10 bits per entry.
// Must hold every Pokémon in the roster (checked at build time by tools/trey/dex_lists.py). 10 bits: National numbers up to 1023.
#define TREY_DEX_ORDER_MAX      768
#define TREY_DEX_ORDER_BYTES    ((TREY_DEX_ORDER_MAX * 10 + 7) / 8 + 1) // +1: entries are read 2 bytes at a time

#endif // GUARD_CONSTANTS_TREY_DEX_H
