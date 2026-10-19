// TREY: ships and trains (TREY_PLAN.md 5.4, Phase 4 chunk 4c). See include/trey_transit.h.

#include "global.h"
#include "event_data.h"
#include "field_screen_effect.h"
#include "item.h"
#include "list_menu.h"
#include "overworld.h"
#include "script_menu.h"
#include "string_util.h"
#include "trey_transit.h"
#include "constants/heal_locations.h"
#include "constants/items.h"
#include "constants/map_groups.h"
#include "constants/maps.h"
#include "constants/region_map_sections.h"

struct TreyTransitStop
{
    const u8 *name;
    u8 mode;          // TRANSIT_SHIP / TRANSIT_TRAIN
    u8 healLocation;  // respawn point after arriving (0 = keep the old one)
    u16 map;          // where you arrive (MAP_UNDEFINED until the map exists)
    s8 x, y;
};

static const u8 sText_Slateport[] = _("SLATEPORT CITY");
static const u8 sText_Lilycove[] = _("LILYCOVE CITY");
static const u8 sText_BattleFrontier[] = _("BATTLE FRONTIER");
static const u8 sText_Vermilion[] = _("VERMILION CITY");
static const u8 sText_Olivine[] = _("OLIVINE CITY");
static const u8 sText_Valencia[] = _("VALENCIA ISLAND");
static const u8 sText_OneIsland[] = _("ONE ISLAND");
static const u8 sText_Canalave[] = _("CANALAVE CITY");
static const u8 sText_Mossui[] = _("MOSSUI TOWN");
static const u8 sText_Goldenrod[] = _("GOLDENROD CITY");
static const u8 sText_Saffron[] = _("SAFFRON CITY");
static const u8 sText_Jubilife[] = _("JUBILIFE CITY");

static const struct TreyTransitStop sStops[TRANSIT_STOP_COUNT] =
{
    [TRANSIT_STOP_SLATEPORT]       = {sText_Slateport,      TRANSIT_SHIP,  HEAL_LOCATION_SLATEPORT_CITY, MAP_SLATEPORT_CITY_HARBOR, 8, 11},
    [TRANSIT_STOP_LILYCOVE]        = {sText_Lilycove,       TRANSIT_SHIP,  HEAL_LOCATION_LILYCOVE_CITY,  MAP_LILYCOVE_CITY_HARBOR,  8, 11},
    [TRANSIT_STOP_BATTLE_FRONTIER] = {sText_BattleFrontier, TRANSIT_SHIP,  0,                            MAP_BATTLE_FRONTIER_OUTSIDE_WEST, 19, 67},
    // Other regions: filled in as their harbours and stations are built (Phase 5/6).
    [TRANSIT_STOP_VERMILION]       = {sText_Vermilion,      TRANSIT_SHIP,  HEAL_LOCATION_VERMILION_CITY, MAP_VERMILION_CITY, 23, 33}, // 5e: the S.S. Anne dock
    [TRANSIT_STOP_OLIVINE]         = {sText_Olivine,        TRANSIT_SHIP,  0, MAP_UNDEFINED, 0, 0},
    [TRANSIT_STOP_VALENCIA]        = {sText_Valencia,       TRANSIT_SHIP,  0, MAP_UNDEFINED, 0, 0},
    [TRANSIT_STOP_ONE_ISLAND]      = {sText_OneIsland,      TRANSIT_SHIP,  0, MAP_UNDEFINED, 0, 0},
    [TRANSIT_STOP_CANALAVE]        = {sText_Canalave,       TRANSIT_SHIP,  0, MAP_UNDEFINED, 0, 0},
    [TRANSIT_STOP_MOSSUI]          = {sText_Mossui,         TRANSIT_SHIP,  0, MAP_UNDEFINED, 0, 0},
    [TRANSIT_STOP_GOLDENROD]       = {sText_Goldenrod,      TRANSIT_TRAIN, 0, MAP_UNDEFINED, 0, 0},
    [TRANSIT_STOP_SAFFRON]         = {sText_Saffron,        TRANSIT_TRAIN, 0, MAP_UNDEFINED, 0, 0},
    [TRANSIT_STOP_JUBILIFE]        = {sText_Jubilife,       TRANSIT_TRAIN, 0, MAP_UNDEFINED, 0, 0},
};

#define TRIP_FROM(trip) (((trip) >> 8) - 1)
#define TRIP_TO(trip)   (((trip) & 0xFF) - 1)

static bool32 IsStopVisited(u32 stop)
{
    return TREY_DEBUG_ALL_TRANSIT || FlagGet(TREY_FLAG_TRANSIT_STOP_START + stop);
}

static bool32 IsOnBoard(void)
{
    u16 map = (gSaveBlock1Ptr->location.mapGroup << 8) | gSaveBlock1Ptr->location.mapNum;
    return map == MAP_SS_TIDAL_CORRIDOR || map == MAP_SS_TIDAL_ROOMS || map == MAP_SS_TIDAL_LOWER_DECK;
}

bool32 TreyTransit_IsTravelling(void)
{
    return VarGet(VAR_TREY_TRANSIT_TRIP) != 0 && VarGet(VAR_TREY_TRANSIT_STATE) != TRANSIT_STATE_NONE;
}

u16 TreyTransit_GetFromStopMapsec(void)
{
    u32 from = TRIP_FROM(VarGet(VAR_TREY_TRANSIT_TRIP));
    if (from >= TRANSIT_STOP_COUNT || sStops[from].map == MAP_UNDEFINED)
        return MAPSEC_NONE;
    return Overworld_GetMapHeaderByGroupAndId(MAP_GROUP(sStops[from].map), MAP_NUM(sStops[from].map))->regionMapSectionId;
}

void TreyTransit_CheckPass(void)
{
    // The ship needs the S.S. Ticket (Vermilion story). The Rail Pass arrives with the first station.
    if (TREY_DEBUG_ALL_TRANSIT)
        gSpecialVar_Result = TRUE;
    else if (gSpecialVar_0x8004 == TRANSIT_SHIP)
        gSpecialVar_Result = CheckBagHasItem(ITEM_SS_TICKET, 1);
    else
        gSpecialVar_Result = FALSE;
}

void TreyTransit_PushDestinations(void)
{
    u32 i, count = 0;
    u32 mode = gSpecialVar_0x8004, here = gSpecialVar_0x8005;

    if (here < TRANSIT_STOP_COUNT)
        FlagSet(TREY_FLAG_TRANSIT_STOP_START + here);
    for (i = 0; i < TRANSIT_STOP_COUNT; i++)
    {
        if (i == here || sStops[i].mode != mode || sStops[i].map == MAP_UNDEFINED || !IsStopVisited(i))
            continue;
        MultichoiceDynamic_PushElement((struct ListMenuItem){sStops[i].name, i});
        count++;
    }
    gSpecialVar_Result = count;
}

void TreyTransit_BufferStopName(void)
{
    u32 stop = gSpecialVar_0x8006;
    StringCopy(gStringVar1, stop < TRANSIT_STOP_COUNT ? sStops[stop].name : sText_Slateport);
}

void TreyTransit_Board(void)
{
    VarSet(VAR_TREY_TRANSIT_TRIP, ((gSpecialVar_0x8005 + 1) << 8) | (gSpecialVar_0x8006 + 1));
    VarSet(VAR_TREY_TRANSIT_STATE, TRANSIT_STATE_BOARDED);
    VarSet(VAR_TREY_TRANSIT_STEPS, 0);
}

void TreyTransit_BufferDestinationName(void)
{
    u32 to = TRIP_TO(VarGet(VAR_TREY_TRANSIT_TRIP));
    StringCopy(gStringVar1, to < TRANSIT_STOP_COUNT ? sStops[to].name : sText_Slateport);
}

void TreyTransit_Depart(void)
{
    VarSet(VAR_TREY_TRANSIT_STATE, TRANSIT_STATE_UNDERWAY);
    VarSet(VAR_TREY_TRANSIT_STEPS, 0);
    TreyTransit_BufferDestinationName();
}

bool32 TreyTransit_CountStep(void)
{
    u16 steps;

    if (VarGet(VAR_TREY_TRANSIT_STATE) != TRANSIT_STATE_UNDERWAY || !IsOnBoard())
        return FALSE;
    steps = VarGet(VAR_TREY_TRANSIT_STEPS) + 1;
    VarSet(VAR_TREY_TRANSIT_STEPS, steps);
    if (steps < TRANSIT_STEPS_PER_TRIP)
        return FALSE;
    VarSet(VAR_TREY_TRANSIT_STATE, TRANSIT_STATE_ARRIVED);
    TreyTransit_BufferDestinationName();
    return TRUE;
}

void TreyTransit_ArriveNow(void)
{
    gSpecialVar_Result = FALSE;
    if (VarGet(VAR_TREY_TRANSIT_STATE) == TRANSIT_STATE_UNDERWAY)
    {
        VarSet(VAR_TREY_TRANSIT_STATE, TRANSIT_STATE_ARRIVED);
        gSpecialVar_Result = TRUE;
    }
    TreyTransit_BufferDestinationName();
}

void TreyTransit_WarpToDestination(void)
{
    u32 to = TRIP_TO(VarGet(VAR_TREY_TRANSIT_TRIP));

    VarSet(VAR_TREY_TRANSIT_TRIP, 0);
    VarSet(VAR_TREY_TRANSIT_STATE, TRANSIT_STATE_NONE);
    VarSet(VAR_TREY_TRANSIT_STEPS, 0);
    if (to >= TRANSIT_STOP_COUNT || sStops[to].map == MAP_UNDEFINED)
        to = TRANSIT_STOP_SLATEPORT;
    FlagSet(TREY_FLAG_TRANSIT_STOP_START + to);
    if (sStops[to].healLocation != 0)
        SetLastHealLocationWarp(sStops[to].healLocation);
    SetWarpDestination(MAP_GROUP(sStops[to].map), MAP_NUM(sStops[to].map), WARP_ID_NONE, sStops[to].x, sStops[to].y);
    DoWarp();
    ResetInitialPlayerAvatarState();
}
