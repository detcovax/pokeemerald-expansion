// TREY (6b-3, rule from David 2026-10-26): the debug menu has a warp to every region's starting town.
// Included by src/debug.c (Utilities -> "TREY: region starts..."). tools/trey/check_maps.py fails the build when a
// region that has maps has no entry here, or when an entry's map is missing or in another region.
// One line per region: [REGION_X] = { MAP_*, x, y }, plus a menu line below.

struct TreyDebugWarp
{
    u16 map;   // MAP_* (group << 8 | num)
    s16 x, y;
};

static const struct TreyDebugWarp sTreyRegionStarts[REGIONS_COUNT] =
{
    [REGION_KANTO] = { MAP_PALLET_TOWN, 6, 8 },        // in front of the player's house (5a)
    [REGION_JOHTO] = { MAP_NEW_BARK_TOWN, 20, 12 },    // at its heal location (6a-5)
    [REGION_HOENN] = { MAP_LITTLEROOT_TOWN, 5, 9 },    // in front of the player's house
    [REGION_SINNOH] = { MAP_TWINLEAF_TOWN, 16, 19 },   // in front of the DPPt player's house (6b-4)
};

static void Debug_DestroyMenu_Full(u8 taskId);

static void DebugAction_Util_TreyWarpRegionStart(u8 taskId, const void *params)
{
    const struct TreyDebugWarp *warp = params;

    SetWarpDestination(MAP_GROUP(warp->map), MAP_NUM(warp->map), WARP_ID_NONE, warp->x, warp->y);
    Debug_DestroyMenu_Full(taskId);
    DoWarp();
    ResetInitialPlayerAvatarState();
}

static const struct DebugMenuOption sDebugMenu_Actions_TreyRegionStarts[] =
{
    { COMPOUND_STRING("Kanto: Pallet Town"),   DebugAction_Util_TreyWarpRegionStart, &sTreyRegionStarts[REGION_KANTO] },
    { COMPOUND_STRING("Johto: New Bark Town"), DebugAction_Util_TreyWarpRegionStart, &sTreyRegionStarts[REGION_JOHTO] },
    { COMPOUND_STRING("Hoenn: Littleroot"),    DebugAction_Util_TreyWarpRegionStart, &sTreyRegionStarts[REGION_HOENN] },
    { COMPOUND_STRING("Sinnoh: Twinleaf Town"), DebugAction_Util_TreyWarpRegionStart, &sTreyRegionStarts[REGION_SINNOH] },
    { NULL }
};
