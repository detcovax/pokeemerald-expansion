// TREY (6b-3, TREY_PLAN.md D34): regional battle music and day/night map music. See include/trey_music.h.

#include "global.h"
#include "rtc.h"
#include "trey_music.h"
#include "trey_regions.h"
#include "constants/regions.h"
#include "constants/songs.h"

struct RegionalSong
{
    u16 emerald;
    u16 regional;
};

static const struct RegionalSong sJohtoSongs[] =
{
    { MUS_VS_WILD,            MUS_HG_VS_WILD },
    { MUS_VS_TRAINER,         MUS_HG_VS_TRAINER },
    { MUS_VS_GYM_LEADER,      MUS_HG_VS_GYM_LEADER },
    { MUS_VS_RIVAL,           MUS_HG_VS_RIVAL },
    { MUS_VS_CHAMPION,        MUS_HG_VS_CHAMPION },
    { MUS_VICTORY_WILD,       MUS_HG_VICTORY_WILD },
    { MUS_VICTORY_TRAINER,    MUS_HG_VICTORY_TRAINER },
    { MUS_VICTORY_GYM_LEADER, MUS_HG_VICTORY_GYM_LEADER },
};

// Sinnoh: only wild battles for now. The repo has no DPPt trainer or gym leader theme (D34).
static const struct RegionalSong sSinnohSongs[] =
{
    { MUS_VS_WILD,      MUS_DPP_VS_WILD },
    { MUS_VICTORY_WILD, MUS_DPP_VICTORY_WILD },
};

static u16 Lookup(const struct RegionalSong *table, u32 count, u16 song)
{
    u32 i;

    for (i = 0; i < count; i++)
    {
        if (table[i].emerald == song)
            return table[i].regional;
    }
    return song;
}

u16 TreyMusic_Regional(u16 song)
{
    switch (TreyGetCurrentRegion())
    {
    case REGION_JOHTO:
        return Lookup(sJohtoSongs, ARRAY_COUNT(sJohtoSongs), song);
    case REGION_SINNOH:
        return Lookup(sSinnohSongs, ARRAY_COUNT(sSinnohSongs), song);
    default:
        return song;
    }
}

u16 TreyMusic_MapMusic(const struct MapHeader *header)
{
    if (header->trey != NULL && header->trey->nightMusic != 0)
    {
        enum TimeOfDay time = GetTimeOfDay();
        if (time == TIME_EVENING || time == TIME_NIGHT)
            return header->trey->nightMusic;
    }
    return header->music;
}
