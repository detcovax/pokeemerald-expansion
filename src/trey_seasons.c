// TREY: seasons (TREY_PLAN.md 5.5, Phase 4 chunk 4b). See include/trey_seasons.h.

#include "global.h"
#include "fieldmap.h"
#include "overworld.h"
#include "rtc.h"
#include "trey_seasons.h"

static EWRAM_DATA u8 sSeason = 0;
static EWRAM_DATA u8 sForcedSeasonPlus1 = 0; // 0 = follow the calendar (EWRAM can only start at zero)

static const u8 sText_Spring[] = _("SPRING");
static const u8 sText_Summer[] = _("SUMMER");
static const u8 sText_Autumn[] = _("AUTUMN");
static const u8 sText_Winter[] = _("WINTER");
static const u8 *const sSeasonNames[TREY_SEASONS_COUNT] = {sText_Spring, sText_Summer, sText_Autumn, sText_Winter};

u8 TreySeason_Get(void)
{
    return sSeason < TREY_SEASONS_COUNT ? sSeason : SEASON_SUMMER;
}

const u8 *TreySeason_GetName(u8 season)
{
    return sSeasonNames[season < TREY_SEASONS_COUNT ? season : SEASON_SUMMER];
}

void TreySeason_LockForMapLoad(void)
{
    u32 month;

    if (sForcedSeasonPlus1 != 0)
    {
        sSeason = sForcedSeasonPlus1 - 1;
        return;
    }
    month = GetMonth(); // in-game calendar, MONTH_JAN = 1
    if (month < MONTH_JAN || month > MONTH_DEC)
        month = MONTH_JUN;
    sSeason = (month - MONTH_JAN) % TREY_SEASONS_COUNT;
}

void TreySeason_DebugForce(u8 season)
{
    sForcedSeasonPlus1 = season < TREY_SEASONS_COUNT ? season + 1 : 0;
}

u8 TreySeason_DebugGetForced(void)
{
    return sForcedSeasonPlus1 == 0 ? TREY_SEASON_NOT_FORCED : sForcedSeasonPlus1 - 1;
}

const u32 *TreySeason_TilesetTiles(const struct Tileset *tileset)
{
    if (tileset->seasonal != NULL && tileset->seasonal[TreySeason_Get()].tiles != NULL)
        return tileset->seasonal[TreySeason_Get()].tiles;
    return tileset->tiles;
}

const u16 (*TreySeason_TilesetPalettes(const struct Tileset *tileset))[16]
{
    if (tileset->seasonal != NULL && tileset->seasonal[TreySeason_Get()].palettes != NULL)
        return tileset->seasonal[TreySeason_Get()].palettes;
    return tileset->palettes;
}

// Layouts: only on a fresh map load (warp or connection). Reloading a saved game keeps the saved layout,
// so a map never changes under the player's feet.
void TreySeason_ApplyMapOverrides(bool32 changeLayout)
{
    const struct MapHeaderTrey *trey = gMapHeader.trey;
    u32 season = TreySeason_Get();

    if (trey == NULL)
        return;
    if (trey->seasonWeather[season] != 0)
        gMapHeader.weather = trey->seasonWeather[season];
    if (changeLayout && trey->seasonLayoutIds[season] != 0)
    {
        gMapHeader.mapLayoutId = trey->seasonLayoutIds[season];
        gMapHeader.mapLayout = GetMapLayout(gMapHeader.mapLayoutId);
    }
}
