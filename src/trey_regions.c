// TREY: regions and badges (TREY_PLAN.md E6, E7, 5.9).

#include "global.h"
#include "event_data.h"
#include "region_map.h"
#include "trey_regions.h"
#include "trey_dex.h"
#include "constants/flags.h"
#include "constants/region_map_sections.h"

// ---------------------------------------------------------------------------
// Regions
// ---------------------------------------------------------------------------

// The region and region map page of every location come from region_map_sections.json (4a).
// Phase 4 (4a): every location carries its region in region_map_sections.json ("trey_region").
enum Region TreyGetRegionOfMapsec(u16 mapSec)
{
    if (mapSec >= MAPSEC_NONE)
        return REGION_HOENN; // MAPSEC_NONE and the special met-location IDs
    return gRegionMapEntries[mapSec].region;
}

// On every map load (warp or walking across a connection): the page this map is drawn on counts as
// visited, so the map screens can flip to it.
static void TreyRegions_SetWorldMapFlag(void);

void TreyRegions_OnMapEnter(void)
{
    u32 page = TreyRegionMap_GetPlayerPage();
    if (page < TREY_REGION_MAP_COUNT)
        FlagSet(FLAG_TREY_VISITED_MAP_PAGE_START + page);
    if (TREY_DEBUG_ALL_REGION_MAPS)
    {
        for (page = 0; page < TREY_REGION_MAP_COUNT; page++)
            FlagSet(FLAG_TREY_VISITED_MAP_PAGE_START + page);
    }
    TreyDex_OnMapEnter(); // 4d: first arrival in a region
    TreyRegions_SetWorldMapFlag(); // 5e: Kanto/Sevii fly and Teleport destinations
}

#include "data/trey/frlg_world_map_flags.h"
#include "constants/trey_johto_fly.h"

// 6a-7: Johto's towns, the same way (include/constants/trey_johto_fly.h).
#define TREY_JOHTO_WORLD_MAP_FLAG(sec, map, heal) {MAP_##map, FLAG_WORLD_MAP_JOHTO_##sec},
static const u16 sTreyJohtoWorldMapFlags[][2] = { TREY_JOHTO_FLY(TREY_JOHTO_WORLD_MAP_FLAG) };
#undef TREY_JOHTO_WORLD_MAP_FLAG

// 5e: entering an FRLG town (or landmark) marks it visited for Fly/Teleport, as FRLG's setworldmapflag did.
static void TreyRegions_SetWorldMapFlag(void)
{
    u32 i;
    u16 map = (gSaveBlock1Ptr->location.mapGroup << 8) | gSaveBlock1Ptr->location.mapNum;
    for (i = 0; i < ARRAY_COUNT(sTreyWorldMapFlags); i++)
    {
        if (sTreyWorldMapFlags[i][0] == map)
        {
            FlagSet(sTreyWorldMapFlags[i][1]);
            return;
        }
    }
    for (i = 0; i < ARRAY_COUNT(sTreyJohtoWorldMapFlags); i++)
    {
        if (sTreyJohtoWorldMapFlags[i][0] == map)
        {
            FlagSet(sTreyJohtoWorldMapFlags[i][1]);
            return;
        }
    }
}

u32 TreyGetRegionMapPageOfMapsec(u16 mapSec)
{
    if (mapSec >= MAPSEC_NONE)
        return TREY_REGION_MAP_HOENN;
    return gRegionMapEntries[mapSec].page;
}

enum Region TreyGetCurrentRegion(void)
{
    return TreyGetRegionOfMapsec(gMapHeader.regionMapSectionId);
}

// ---------------------------------------------------------------------------
// Badges
// ---------------------------------------------------------------------------

struct TreyRegionBadges
{
    u16 firstFlag;
    u8 count;
};

static const struct TreyRegionBadges sTreyRegionBadges[REGIONS_COUNT] =
{
    [REGION_KANTO]  = { TREY_FLAG_BADGES_KANTO_START,  8 },
    [REGION_ORANGE] = { TREY_FLAG_BADGES_ORANGE_START, 5 }, // 4 badges + Winner's Trophy
    [REGION_JOHTO]  = { TREY_FLAG_BADGES_JOHTO_START,  8 },
    [REGION_HOENN]  = { FLAG_BADGE01_GET,              NUM_BADGES }, // existing Emerald badge flags
    [REGION_SINNOH] = { TREY_FLAG_BADGES_SINNOH_START, 8 },
};

STATIC_ASSERT(NUM_BADGES == TREY_MAX_BADGES_PER_REGION, TreyHoennBadgeCountChanged);

u32 TreyBadges_GetCount(enum Region region)
{
    if (region >= REGIONS_COUNT)
        return 0;
    return sTreyRegionBadges[region].count;
}

u16 TreyBadges_GetFlag(enum Region region, u32 badgeIndex)
{
    if (badgeIndex >= TreyBadges_GetCount(region))
        return 0;
    return sTreyRegionBadges[region].firstFlag + badgeIndex;
}

bool32 TreyBadges_Has(enum Region region, u32 badgeIndex)
{
    u16 flag = TreyBadges_GetFlag(region, badgeIndex);
    return flag != 0 && FlagGet(flag);
}

u32 TreyBadges_CountOwned(enum Region region)
{
    u32 i, owned = 0;
    for (i = 0; i < TreyBadges_GetCount(region); i++)
    {
        if (TreyBadges_Has(region, i))
            owned++;
    }
    return owned;
}

u32 TreyBadges_CountOwnedTotal(void)
{
    u32 region, owned = 0;
    for (region = 0; region < REGIONS_COUNT; region++)
        owned += TreyBadges_CountOwned(region);
    return owned;
}

// ---------------------------------------------------------------------------
// Leagues (4e, TREY_PLAN.md 5.9): admission needs that region's league badges only, in any order.
// Orange: the 4 badges open the Supreme Cup (the Winner's Trophy, badge slot 5, is won there).
// ---------------------------------------------------------------------------

u32 TreyBadges_GetLeagueCount(enum Region region)
{
    if (region == REGION_ORANGE)
        return 4;
    return TreyBadges_GetCount(region);
}

bool32 TreyLeague_HasAdmission(enum Region region)
{
    u32 i, count = TreyBadges_GetLeagueCount(region);
    if (count == 0)
        return FALSE;
    for (i = 0; i < count; i++)
    {
        if (!TreyBadges_Has(region, i))
            return FALSE;
    }
    return TRUE;
}

// special: VAR_0x8004 = the region as its TREY_DEX_* id (scripts can't see enum Region). VAR_RESULT = TRUE/FALSE.
void TreyLeague_CheckAdmission(void)
{
    gSpecialVar_Result = TreyLeague_HasAdmission(TreyDex_GetRegionOfDex(gSpecialVar_0x8004));
}
