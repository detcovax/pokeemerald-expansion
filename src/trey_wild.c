// TREY: wild encounters by season, time of day and weather (TREY_PLAN.md 5.11, D22; 4b-2).
// See include/trey_wild.h.

#include "global.h"
#include "field_weather.h"
#include "overworld.h"
#include "trey_seasons.h"
#include "trey_wild.h"
#include "wild_encounter.h"
#include "constants/weather.h"

#include "data/trey/wild_encounters_trey.h"

// Rebuilt on each call; callers use the result straight away.
static EWRAM_DATA struct WildEncounterTypes sMerged = {0};

u32 TreyWild_GetWeatherGroup(u32 weather)
{
    switch (weather)
    {
    case WEATHER_RAIN:
    case WEATHER_RAIN_THUNDERSTORM:
    case WEATHER_DOWNPOUR:
        return TREY_WEATHER_RAIN;
    case WEATHER_SNOW:
        return TREY_WEATHER_SNOW;
    case WEATHER_SANDSTORM:
        return TREY_WEATHER_SANDSTORM;
    case WEATHER_FOG_HORIZONTAL:
    case WEATHER_FOG_DIAGONAL:
    case WEATHER_FOG:
        return TREY_WEATHER_FOG;
    case WEATHER_DROUGHT:
        return TREY_WEATHER_SUN;
    default:
        return TREY_WEATHER_CLEAR;
    }
}

u32 TreyWild_GetCurrentWeatherGroup(void)
{
    return TreyWild_GetWeatherGroup(GetCurrentWeather());
}

u16 TreyWild_FindMap(u8 mapGroup, u8 mapNum)
{
    u32 i;
    for (i = 0; i < gTreyWildMapCount; i++)
    {
        if (gTreyWildMaps[i].mapGroup == mapGroup && gTreyWildMaps[i].mapNum == mapNum)
            return i;
    }
    return 0xFFFF;
}

static void MergeArea(const struct WildPokemonInfo **dst, const struct WildPokemonInfo *src)
{
    if (src != NULL)
        *dst = src;
}

const struct WildEncounterTypes *TreyWild_GetTypesFor(u32 headerId, u32 timeOfDay, u32 season, u32 weatherGroup)
{
    u16 trey;
    u32 i;

    if (timeOfDay >= TIMES_OF_DAY_COUNT)
        timeOfDay = 0;
    memset(&sMerged, 0, sizeof(sMerged));
    if (headerId >= TREY_WILD_HEADER_BASE)
    {
        trey = headerId - TREY_WILD_HEADER_BASE;
        if (trey >= gTreyWildMapCount)
            return &sMerged;
    }
    else
    {
        // Emerald-style tables: every season and weather for this time of day.
        sMerged = gWildMonHeaders[headerId].encounterTypes[timeOfDay];
        trey = TreyWild_FindMap(gWildMonHeaders[headerId].mapGroup, gWildMonHeaders[headerId].mapNum);
        if (trey == 0xFFFF)
            return &sMerged;
    }
    for (i = 0; i < gTreyWildMaps[trey].entryCount; i++)
    {
        const struct TreyWildEntry *e = &gTreyWildMaps[trey].entries[i];
        if (!(e->seasons & (1 << season)) || !(e->times & (1 << timeOfDay)) || !(e->weathers & (1 << weatherGroup)))
            continue;
        MergeArea(&sMerged.landMonsInfo, e->types->landMonsInfo);
        MergeArea(&sMerged.waterMonsInfo, e->types->waterMonsInfo);
        MergeArea(&sMerged.rockSmashMonsInfo, e->types->rockSmashMonsInfo);
        MergeArea(&sMerged.fishingMonsInfo, e->types->fishingMonsInfo);
        MergeArea(&sMerged.hiddenMonsInfo, e->types->hiddenMonsInfo);
        MergeArea(&sMerged.skyMonsInfo, e->types->skyMonsInfo);
    }
    return &sMerged;
}

const struct WildEncounterTypes *TreyWild_GetTypes(u32 headerId, u32 timeOfDay)
{
    return TreyWild_GetTypesFor(headerId, timeOfDay, TreySeason_Get(), TreyWild_GetCurrentWeatherGroup());
}
