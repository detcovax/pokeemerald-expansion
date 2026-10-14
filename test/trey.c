// TREY: tests for TREY systems. Run with `make check`.
#include "global.h"
#include "test/test.h"
#include "trey_battle.h"
#include "move.h"
#include "pokemon.h"
#include "trey_energy.h"

// Phase 2b: effective level (TREY_PLAN.md 5.7)
TEST("TREY: effective level with floor 50")
{
    EXPECT_EQ(TreyGetStatLevelWithFloor(1, 50), 50);
    EXPECT_EQ(TreyGetStatLevelWithFloor(10, 50), 55);
    EXPECT_EQ(TreyGetStatLevelWithFloor(50, 50), 75);
    EXPECT_EQ(TreyGetStatLevelWithFloor(100, 50), 100);
}

TEST("TREY: floor 0 is the vanilla level")
{
    u32 level;
    for (level = 1; level <= 100; level++)
        EXPECT_EQ(TreyGetStatLevelWithFloor(level, 0), level);
}

TEST("TREY: effective level never decreases as level rises")
{
    u32 level;
    for (level = 2; level <= 100; level++)
        EXPECT_GE(TreyGetStatLevelWithFloor(level, TREY_STAT_LEVEL_FLOOR), TreyGetStatLevelWithFloor(level - 1, TREY_STAT_LEVEL_FLOOR));
}

TEST("TREY: a level 10 vs level 50 gap is much smaller than vanilla")
{
    // Vanilla: 10/50 = 20%. TREY floor 50: 55/75 = 73%.
    EXPECT_GE(TreyGetStatLevelWithFloor(10, 50) * 100 / TreyGetStatLevelWithFloor(50, 50), 70);
}

// Energy E1 (TREY_PLAN.md 5.6)
TEST("TREY Energy: current Energy, IV and EV survive a save round trip")
{
    struct Pokemon mon;
    u16 energy;
    u8 iv, ev;
    CreateMon(&mon, SPECIES_WOBBUFFET, 50, 0, FALSE, 0, OT_ID_PRESET, 0);
    energy = 1023; SetMonData(&mon, MON_DATA_ENERGY, &energy);
    EXPECT_EQ(GetMonData(&mon, MON_DATA_ENERGY), 1023);
    energy = 600; SetMonData(&mon, MON_DATA_ENERGY, &energy);
    EXPECT_EQ(GetMonData(&mon, MON_DATA_ENERGY), 600);
    energy = 2000; SetMonData(&mon, MON_DATA_ENERGY, &energy);
    EXPECT_EQ(GetMonData(&mon, MON_DATA_ENERGY), TREY_ENERGY_MAX_VALUE);
    iv = 31; SetMonData(&mon, MON_DATA_ENERGY_IV, &iv);
    EXPECT_EQ(GetMonData(&mon, MON_DATA_ENERGY_IV), 31);
    ev = 252; SetMonData(&mon, MON_DATA_ENERGY_EV, &ev);
    EXPECT_EQ(GetMonData(&mon, MON_DATA_ENERGY_EV), 252);
    // Neighbouring hyper-training bits are untouched.
    EXPECT_EQ(GetMonData(&mon, MON_DATA_HYPER_TRAINED_DEF), 0);
    EXPECT_EQ(GetMonData(&mon, MON_DATA_HYPER_TRAINED_SPEED), 0);
}

TEST("TREY Energy: new Pokemon start with full Energy")
{
    struct Pokemon mon;
    CreateMon(&mon, SPECIES_WOBBUFFET, 50, 31, FALSE, 0, OT_ID_PRESET, 0);
    EXPECT_EQ(GetMonData(&mon, MON_DATA_ENERGY_IV), 31);
    EXPECT_EQ(GetMonData(&mon, MON_DATA_ENERGY), TreyEnergy_GetMonMax(&mon));
    EXPECT_GT(TreyEnergy_GetMonMax(&mon), 0);
}

TEST("TREY Energy: max Energy formula")
{
    // (2 x base + IV + EV/4) x level / 100 + 5. TESTING builds use the real level.
    u32 base = TreyEnergy_GetBase(SPECIES_WOBBUFFET);
    EXPECT_EQ(TreyEnergy_CalcMax(SPECIES_WOBBUFFET, 100, 31, 252), min((2 * base + 31 + 63) + 5, TREY_ENERGY_MAX_VALUE));
    EXPECT_EQ(TreyEnergy_CalcMax(SPECIES_NONE, 100, 31, 252), 0);
}

TEST("TREY Energy: PP always reads full and cannot be spent")
{
    struct Pokemon mon;
    u8 pp = 0;
    CreateMon(&mon, SPECIES_WOBBUFFET, 50, 0, FALSE, 0, OT_ID_PRESET, 0);
    SetMonData(&mon, MON_DATA_PP1, &pp);
    EXPECT_EQ(GetMonData(&mon, MON_DATA_PP1), GetMovePP(GetMonData(&mon, MON_DATA_MOVE1)));
    EXPECT_EQ(GetMonData(&mon, MON_DATA_PP_BONUSES), 0);
}

TEST("TREY Energy: example move costs")
{
    EXPECT_EQ(TreyEnergy_GetMoveCost(MOVE_THUNDER_SHOCK), 3);
    EXPECT_EQ(TreyEnergy_GetMoveCost(MOVE_FLAMETHROWER), 7);
    EXPECT_EQ(TreyEnergy_GetMoveCost(MOVE_HYDRO_PUMP), 20);
    EXPECT_EQ(TreyEnergy_GetMoveCost(MOVE_SWORDS_DANCE), 4);
    EXPECT_EQ(TreyEnergy_GetMoveCost(MOVE_NONE), 0);
}

TEST("TREY Energy: Energy EVs count toward the EV total")
{
    struct Pokemon mon;
    u8 ev = 100;
    CreateMon(&mon, SPECIES_WOBBUFFET, 50, 0, FALSE, 0, OT_ID_PRESET, 0);
    SetMonData(&mon, MON_DATA_ENERGY_EV, &ev);
    EXPECT_EQ(GetMonEVCount(&mon), 100);
}

// Sky HMs (3f)
#include "trey_hm.h"
#include "metatile_behavior.h"
#include "constants/metatile_behaviors.h"

TEST("TREY Sky HMs: every Sky Battle eligible species can learn Gust, Whirlwind and Updraft")
{
    EXPECT(TreyHM_SpeciesCanLearn(SPECIES_PIDGEY, MOVE_UPDRAFT));
    EXPECT(TreyHM_SpeciesCanLearn(SPECIES_PIDGEY, MOVE_WHIRLWIND));
    EXPECT(TreyHM_SpeciesCanLearn(SPECIES_GASTLY, MOVE_GUST));      // Levitate
    EXPECT(!TreyHM_SpeciesCanLearn(SPECIES_WOBBUFFET, MOVE_UPDRAFT));
    EXPECT(TreyHM_IsHM(MOVE_GUST) && TreyHM_IsHM(MOVE_WHIRLWIND) && TreyHM_IsHM(MOVE_UPDRAFT));
}

TEST("TREY Sky HMs: relearner lists the sky HMs for a flyer")
{
    u16 known[MAX_MON_MOVES] = {MOVE_GUST, MOVE_NONE, MOVE_NONE, MOVE_NONE};
    u16 moves[32];
    u32 i, n = TreyHM_AppendRelearnableMoves(SPECIES_PIDGEY, known, moves, 0, ARRAY_COUNT(moves));
    bool32 hasUpdraft = FALSE, hasGust = FALSE;
    for (i = 0; i < n; i++)
    {
        hasUpdraft |= (moves[i] == MOVE_UPDRAFT);
        hasGust |= (moves[i] == MOVE_GUST);
    }
    EXPECT(hasUpdraft);
    EXPECT(!hasGust); // already known
}

TEST("TREY Sky HMs: cyclone, updraft and landing spot behaviours")
{
    EXPECT(MetatileBehavior_IsSkyCyclone(MB_SKY_CYCLONE));
    EXPECT(!MetatileBehavior_IsSkyCyclone(MB_SKY_UPDRAFT));
    EXPECT(MetatileBehavior_IsSkyUpdraft(MB_SKY_UPDRAFT));
    EXPECT(!MetatileBehavior_IsSkyUpdraft(MB_SKY_CLOUD));
    EXPECT(MetatileBehavior_IsSkyLanding(MB_SKY_LANDING));
    EXPECT(!MetatileBehavior_IsSkyLanding(MB_SKY_CLOUD));
}

// Regions and region maps (4a)
#include "event_data.h"
#include "region_map.h"
#include "trey_regions.h"
#include "constants/region_map_sections.h"

TEST("TREY Regions: every location knows its region and region map page")
{
    EXPECT_EQ(TreyGetRegionOfMapsec(MAPSEC_LITTLEROOT_TOWN), REGION_HOENN);
    EXPECT_EQ(TreyGetRegionOfMapsec(MAPSEC_PALLET_TOWN), REGION_KANTO);
    EXPECT_EQ(TreyGetRegionOfMapsec(MAPSEC_ONE_ISLAND), REGION_KANTO);        // Sevii is Kanto for gameplay
    EXPECT_EQ(TreyGetRegionMapPageOfMapsec(MAPSEC_ONE_ISLAND), TREY_REGION_MAP_SEVII_123);
    EXPECT_EQ(TreyGetRegionMapPageOfMapsec(MAPSEC_SEVEN_ISLAND), TREY_REGION_MAP_SEVII_67);
    EXPECT_EQ(TreyGetRegionOfMapsec(MAPSEC_NEW_BARK_TOWN), REGION_JOHTO);
    EXPECT_EQ(TreyGetRegionOfMapsec(MAPSEC_TWINLEAF_TOWN), REGION_SINNOH);
    EXPECT_EQ(TreyGetRegionOfMapsec(MAPSEC_PUMMELO_ISLAND), REGION_ORANGE);
    EXPECT_EQ(TreyGetRegionMapPageOfMapsec(MAPSEC_MOSSUI_TOWN), TREY_REGION_MAP_KITAKAMI);
    EXPECT_EQ(TreyGetRegionOfMapsec(MAPSEC_NONE), REGION_HOENN);
}

TEST("TREY Regions: L/R only flips to visited region map pages")
{
    u32 i;
    for (i = 0; i < TREY_REGION_MAP_COUNT; i++)
        FlagClear(FLAG_TREY_VISITED_MAP_PAGE_START + i);
    EXPECT_EQ(TreyRegionMap_NextVisitedPage(TREY_REGION_MAP_HOENN, 1), TREY_REGION_MAP_HOENN);
    FlagSet(FLAG_TREY_VISITED_MAP_PAGE_START + TREY_REGION_MAP_HOENN);
    FlagSet(FLAG_TREY_VISITED_MAP_PAGE_START + TREY_REGION_MAP_KANTO);
    FlagSet(FLAG_TREY_VISITED_MAP_PAGE_START + TREY_REGION_MAP_SINNOH);
    EXPECT_EQ(TreyRegionMap_NextVisitedPage(TREY_REGION_MAP_HOENN, 1), TREY_REGION_MAP_SINNOH);
    EXPECT_EQ(TreyRegionMap_NextVisitedPage(TREY_REGION_MAP_SINNOH, 1), TREY_REGION_MAP_KANTO); // wraps
    EXPECT_EQ(TreyRegionMap_NextVisitedPage(TREY_REGION_MAP_KANTO, -1), TREY_REGION_MAP_SINNOH);
}

// Seasons (4b)
#include "trey_seasons.h"

TEST("TREY Seasons: a forced season is locked on the next map load, and the calendar takes over again")
{
    TreySeason_DebugForce(SEASON_WINTER);
    TreySeason_LockForMapLoad();
    EXPECT_EQ(TreySeason_Get(), SEASON_WINTER);
    TreySeason_DebugForce(SEASON_AUTUMN);
    EXPECT_EQ(TreySeason_Get(), SEASON_WINTER); // unchanged until the next map load
    TreySeason_LockForMapLoad();
    EXPECT_EQ(TreySeason_Get(), SEASON_AUTUMN);
    TreySeason_DebugForce(TREY_SEASON_NOT_FORCED);
    EXPECT_EQ(TreySeason_DebugGetForced(), TREY_SEASON_NOT_FORCED);
    TreySeason_LockForMapLoad();
    EXPECT_LT(TreySeason_Get(), TREY_SEASONS_COUNT);
}
