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

// Wild encounters by season and weather (4b-2)
#include "trey_wild.h"
#include "constants/map_groups.h"
#include "constants/weather.h"

static u32 TreyTest_FindWildHeader(u8 group, u8 num)
{
    u32 i;
    for (i = 0; gWildMonHeaders[i].mapGroup != MAP_GROUP(MAP_UNDEFINED); i++)
    {
        if (gWildMonHeaders[i].mapGroup == group && gWildMonHeaders[i].mapNum == num)
            return i;
    }
    return HEADER_NONE;
}

TEST("TREY Wild: CSV tables override Route 101's Emerald tables only where they apply")
{
    u32 id = TreyTest_FindWildHeader(MAP_GROUP(MAP_ROUTE101), MAP_NUM(MAP_ROUTE101));
    const struct WildEncounterTypes *t;
    ASSUME(id != HEADER_NONE);
    t = TreyWild_GetTypesFor(id, TIME_DAY, SEASON_WINTER, TREY_WEATHER_CLEAR);
    EXPECT_EQ(t->landMonsInfo->wildPokemon[0].species, SPECIES_SNORUNT);
    t = TreyWild_GetTypesFor(id, TIME_NIGHT, SEASON_SPRING, TREY_WEATHER_RAIN);
    EXPECT_EQ(t->landMonsInfo->wildPokemon[0].species, SPECIES_LOTAD);
    t = TreyWild_GetTypesFor(id, TIME_DAY, SEASON_SUMMER, TREY_WEATHER_CLEAR);
    EXPECT_EQ(t->landMonsInfo, gWildMonHeaders[id].encounterTypes[TIME_DAY].landMonsInfo);
}

TEST("TREY Wild: weather groups")
{
    EXPECT_EQ(TreyWild_GetWeatherGroup(WEATHER_DOWNPOUR), TREY_WEATHER_RAIN);
    EXPECT_EQ(TreyWild_GetWeatherGroup(WEATHER_SNOW), TREY_WEATHER_SNOW);
    EXPECT_EQ(TreyWild_GetWeatherGroup(WEATHER_FOG_DIAGONAL), TREY_WEATHER_FOG);
    EXPECT_EQ(TreyWild_GetWeatherGroup(WEATHER_DROUGHT), TREY_WEATHER_SUN);
    EXPECT_EQ(TreyWild_GetWeatherGroup(WEATHER_SUNNY), TREY_WEATHER_CLEAR);
}

// Transit (4c)
#include "trey_transit.h"
#include "constants/vars.h"

TEST("TREY Transit: boarding, getting under way and resting in the cabin brings the ship in")
{
    gSpecialVar_0x8005 = TRANSIT_STOP_SLATEPORT;
    gSpecialVar_0x8006 = TRANSIT_STOP_LILYCOVE;
    TreyTransit_Board();
    EXPECT_EQ(VarGet(VAR_TREY_TRANSIT_STATE), TRANSIT_STATE_BOARDED);
    EXPECT(TreyTransit_IsTravelling());
    TreyTransit_ArriveNow();                       // not under way yet: nothing happens
    EXPECT_EQ(gSpecialVar_Result, FALSE);
    TreyTransit_Depart();
    EXPECT_EQ(VarGet(VAR_TREY_TRANSIT_STATE), TRANSIT_STATE_UNDERWAY);
    TreyTransit_ArriveNow();
    EXPECT_EQ(gSpecialVar_Result, TRUE);
    EXPECT_EQ(VarGet(VAR_TREY_TRANSIT_STATE), TRANSIT_STATE_ARRIVED);
    VarSet(VAR_TREY_TRANSIT_TRIP, 0);
    VarSet(VAR_TREY_TRANSIT_STATE, TRANSIT_STATE_NONE);
}

// Pokédex (4d)
#include "pokedex.h"
#include "pokemon_storage_system.h"
#include "trey_dex.h"
#include "constants/pokedex.h"

static void TreyTest_ClearDex(void)
{
    memset(gSaveBlock1Ptr->dexSeen, 0, sizeof(gSaveBlock1Ptr->dexSeen));
    memset(gSaveBlock1Ptr->dexCaught, 0, sizeof(gSaveBlock1Ptr->dexCaught));
    TreyDex_ResetDiscovery();
}

TEST("TREY Dex: discovery numbers follow the order Pokémon are first seen")
{
    TreyTest_ClearDex();
    GetSetPokedexFlag(NATIONAL_DEX_PIKACHU, FLAG_SET_SEEN);
    GetSetPokedexFlag(NATIONAL_DEX_BULBASAUR, FLAG_SET_SEEN);
    GetSetPokedexFlag(NATIONAL_DEX_PIKACHU, FLAG_SET_SEEN);    // seen again: keeps its number
    GetSetPokedexFlag(NATIONAL_DEX_TREECKO, FLAG_SET_CAUGHT);  // caught without being seen still counts
    EXPECT_EQ(TreyDex_GetDiscoveryCount(), 3);
    EXPECT_EQ(TreyDex_GetDiscoveryNumber(NATIONAL_DEX_PIKACHU), 1);
    EXPECT_EQ(TreyDex_GetDiscoveryNumber(NATIONAL_DEX_BULBASAUR), 2);
    EXPECT_EQ(TreyDex_GetDiscoveryNumber(NATIONAL_DEX_TREECKO), 3);
    EXPECT_EQ(TreyDex_GetDiscoveryNumber(NATIONAL_DEX_MEW), 0);
    EXPECT_EQ(SpeciesToPokedexNum(SPECIES_BULBASAUR), 2);
    EXPECT_EQ(SpeciesToPokedexNum(SPECIES_MEW), 0xFFFF);
    TreyTest_ClearDex();
}

// The game's roster fitting TREY_DEX_ORDER_MAX (and 10 bits) is checked at build time by tools/trey/dex_lists.py:
// test builds switch every species on, so they can't check it here.
TEST("TREY Dex: the discovery list packs large National numbers and stops when full")
{
    u32 i, natDex, count = 0;
    TreyTest_ClearDex();
    for (natDex = 1023; natDex >= 1 && count < TREY_DEX_ORDER_MAX; natDex--) // large numbers stress the 10-bit packing
    {
        if (NationalPokedexNumToSpecies(natDex) == SPECIES_NONE)
            continue;
        GetSetPokedexFlag(natDex, FLAG_SET_SEEN);
        count++;
    }
    EXPECT_EQ(count, TREY_DEX_ORDER_MAX);
    EXPECT_EQ(TreyDex_GetDiscoveryCount(), TREY_DEX_ORDER_MAX);
    for (i = 0, natDex = 1023; i < TREY_DEX_ORDER_MAX; natDex--)
    {
        if (NationalPokedexNumToSpecies(natDex) == SPECIES_NONE)
            continue;
        EXPECT_EQ(TreyDex_GetDiscoveryAt(i), natDex);
        i++;
    }
    GetSetPokedexFlag(NATIONAL_DEX_BULBASAUR, FLAG_SET_SEEN); // list full: ignored, no overflow
    EXPECT_EQ(TreyDex_GetDiscoveryCount(), TREY_DEX_ORDER_MAX);
    EXPECT_EQ(TreyDex_GetDiscoveryNumber(NATIONAL_DEX_BULBASAUR), 0);
    TreyTest_ClearDex();
}

TEST("TREY Dex: repair adds seen Pokémon missing from the list")
{
    TreyTest_ClearDex();
    GetSetPokedexFlag(NATIONAL_DEX_MUDKIP, FLAG_SET_SEEN);
    gSaveBlock1Ptr->dexSeen[(NATIONAL_DEX_EEVEE - 1) / 8] |= 1 << ((NATIONAL_DEX_EEVEE - 1) % 8); // behind the hook's back
    EXPECT_EQ(TreyDex_GetDiscoveryNumber(NATIONAL_DEX_EEVEE), 0);
    TreyDex_Repair();
    EXPECT_EQ(TreyDex_GetDiscoveryNumber(NATIONAL_DEX_MUDKIP), 1);
    EXPECT_EQ(TreyDex_GetDiscoveryNumber(NATIONAL_DEX_EEVEE), 2);
    TreyTest_ClearDex();
}

TEST("TREY Dex: regional dex membership")
{
    EXPECT(TreyDex_IsInDex(TREY_DEX_KANTO, NATIONAL_DEX_PIKACHU));
    EXPECT(TreyDex_IsInDex(TREY_DEX_JOHTO, NATIONAL_DEX_PIKACHU));
    EXPECT(TreyDex_IsInDex(TREY_DEX_HOENN, NATIONAL_DEX_PIKACHU));
    EXPECT(TreyDex_IsInDex(TREY_DEX_SINNOH, NATIONAL_DEX_PIKACHU));
    EXPECT(TreyDex_IsInDex(TREY_DEX_KITAKAMI, NATIONAL_DEX_PIKACHU));
    EXPECT(TreyDex_IsInDex(TREY_DEX_KITAKAMI, NATIONAL_DEX_OGERPON));
    EXPECT(!TreyDex_IsInDex(TREY_DEX_HOENN, NATIONAL_DEX_OGERPON));
    EXPECT(!TreyDex_IsInDex(TREY_DEX_HOENN, NATIONAL_DEX_BULBASAUR));
    EXPECT(TreyDex_IsInDex(TREY_DEX_HOENN, NATIONAL_DEX_GALLADE));  // ORAS list
    EXPECT(TreyDex_IsInDex(TREY_DEX_SINNOH, NATIONAL_DEX_GIRATINA)); // Platinum list
    EXPECT(TreyDex_IsInDex(TREY_DEX_NATIONAL, NATIONAL_DEX_OGERPON));
    EXPECT_EQ(TreyDex_GetDexOfRegion(REGION_HOENN), TREY_DEX_HOENN);
    EXPECT_EQ(TreyDex_GetDexOfRegion(REGION_KITAKAMI), TREY_DEX_KITAKAMI);
}

TEST("TREY Dex: professor unlocks")
{
    FlagClear(FLAG_TREY_DEX_SINNOH);
    EXPECT(TreyDex_IsUnlocked(TREY_DEX_NATIONAL));
    EXPECT(!TreyDex_IsUnlocked(TREY_DEX_SINNOH));
    gSpecialVar_0x8004 = TREY_DEX_SINNOH;
    TreyDex_UnlockFromVar();
    EXPECT(TreyDex_IsUnlocked(TREY_DEX_SINNOH));
    FlagClear(FLAG_TREY_DEX_SINNOH);
}

// Leagues (4e)
TEST("TREY League: admission needs all of the region's league badges, in any order")
{
    u32 i;
    for (i = 0; i < 8; i++)
        FlagClear(TreyBadges_GetFlag(REGION_HOENN, i));
    for (i = 0; i < 5; i++)
        FlagClear(TreyBadges_GetFlag(REGION_ORANGE, i));

    for (i = 7; i >= 1; i--) // backwards: order doesn't matter
        FlagSet(TreyBadges_GetFlag(REGION_HOENN, i));
    gSpecialVar_0x8004 = TREY_DEX_HOENN;
    TreyLeague_CheckAdmission();
    EXPECT_EQ(gSpecialVar_Result, FALSE);      // Stone Badge missing
    FlagSet(TreyBadges_GetFlag(REGION_HOENN, 0));
    TreyLeague_CheckAdmission();
    EXPECT_EQ(gSpecialVar_Result, TRUE);

    for (i = 0; i < 4; i++)
        FlagSet(TreyBadges_GetFlag(REGION_ORANGE, i));
    EXPECT(TreyLeague_HasAdmission(REGION_ORANGE)); // the Winner's Trophy isn't needed to enter
    EXPECT(!TreyLeague_HasAdmission(REGION_KITAKAMI)); // no league

    for (i = 0; i < 8; i++)
        FlagClear(TreyBadges_GetFlag(REGION_HOENN, i));
    for (i = 0; i < 5; i++)
        FlagClear(TreyBadges_GetFlag(REGION_ORANGE, i));
}

// Quests (4f)
#include "trey_quest.h"

TEST("TREY Quest: stages start, advance, clamp and complete")
{
    memset(gSaveBlock3Ptr->trey.questStages, 0, sizeof(gSaveBlock3Ptr->trey.questStages));
    EXPECT(!TreyQuest_AnyStarted());
    EXPECT_EQ(TreyQuest_GetStage(QUEST_TEST_SURVEY), QUEST_STAGE_NONE);
    EXPECT(TreyQuest_GetStageText(QUEST_TEST_SURVEY) == NULL);

    TreyQuest_SetStage(QUEST_TEST_SURVEY, 1);
    EXPECT(TreyQuest_IsStarted(QUEST_TEST_SURVEY));
    EXPECT(TreyQuest_AnyStarted());
    EXPECT(TreyQuest_GetStageText(QUEST_TEST_SURVEY) == gTreyQuests[QUEST_TEST_SURVEY].stages[0]);

    TreyQuest_SetStage(QUEST_TEST_SURVEY, 99);                 // past the last stage: clamped
    EXPECT_EQ(TreyQuest_GetStage(QUEST_TEST_SURVEY), 3);
    EXPECT(!TreyQuest_IsDone(QUEST_TEST_SURVEY));

    TreyQuest_Complete(QUEST_TEST_SURVEY);
    EXPECT(TreyQuest_IsDone(QUEST_TEST_SURVEY));
    EXPECT_GE(TreyQuest_GetStage(QUEST_TEST_SURVEY), 3);        // done counts as past every stage
    EXPECT(TreyQuest_GetStageText(QUEST_TEST_SURVEY) == gTreyQuests[QUEST_TEST_SURVEY].stages[2]);

    TreyQuest_SetStage(QUEST_TEST_SURVEY, QUEST_STAGE_NONE);
    EXPECT(!TreyQuest_AnyStarted());
}

TEST("TREY Quest: every region has a story quest and empty slots are ignored")
{
    EXPECT(TreyQuest_IsValid(QUEST_KANTO_STORY));
    EXPECT(TreyQuest_IsValid(QUEST_ORANGE_STORY));
    EXPECT(TreyQuest_IsValid(QUEST_JOHTO_STORY));
    EXPECT(TreyQuest_IsValid(QUEST_HOENN_STORY));
    EXPECT(TreyQuest_IsValid(QUEST_SINNOH_STORY));
    EXPECT(TreyQuest_IsValid(QUEST_KITAKAMI_STORY));
    EXPECT_EQ(gTreyQuests[QUEST_KITAKAMI_STORY].region, TREY_DEX_KITAKAMI);
    EXPECT(!TreyQuest_IsValid(100));                            // unused num
    TreyQuest_SetStage(100, 1);                                 // ignored
    EXPECT_EQ(gSaveBlock3Ptr->trey.questStages[100], 0);
    EXPECT(!TreyQuest_IsValid(QUEST_COUNT));
}
