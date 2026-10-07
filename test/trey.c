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
