// TREY: tests for TREY systems. Run with `make check`.
#include "global.h"
#include "test/test.h"
#include "trey_battle.h"

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
