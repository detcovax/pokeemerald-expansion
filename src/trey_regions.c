// TREY: regions and badges (TREY_PLAN.md E6, E7, 5.9).

#include "global.h"
#include "event_data.h"
#include "region_map.h"
#include "trey_regions.h"
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
