#ifndef GUARD_TREY_SEASONS_H
#define GUARD_TREY_SEASONS_H

// TREY: seasons, Gen 5 rules (TREY_PLAN.md 5.5, D6; Phase 4 chunk 4b).
// Season = (in-game calendar month - 1) % 4: Jan/May/Sep spring, Feb/Jun/Oct summer, Mar/Jul/Nov autumn,
// Apr/Aug/Dec winter. It is worked out on every map load and stays the same until the next one.

#include "constants/trey_seasons.h"

struct Tileset;

u8 TreySeason_Get(void);              // the season locked by the last map load
void TreySeason_LockForMapLoad(void); // called by the overworld right before a map's header is used
const u8 *TreySeason_GetName(u8 season);

// Debug: force a season (SEASON_* ), or TREY_SEASON_NOT_FORCED to follow the calendar again.
#define TREY_SEASON_NOT_FORCED 0xFF
void TreySeason_DebugForce(u8 season);
u8 TreySeason_DebugGetForced(void);

// Seasonal tileset graphics (E16): the current season's tiles/palettes, or the base ones.
const u32 *TreySeason_TilesetTiles(const struct Tileset *tileset);
const u16 (*TreySeason_TilesetPalettes(const struct Tileset *tileset))[16];

// Per-map seasonal overrides from map.json ("trey_season_layouts", "trey_season_weather"):
// apply them to gMapHeader for the locked season.
void TreySeason_ApplyMapOverrides(bool32 changeLayout);

#endif // GUARD_TREY_SEASONS_H
