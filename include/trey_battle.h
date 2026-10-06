#ifndef GUARD_TREY_BATTLE_H
#define GUARD_TREY_BATTLE_H

// TREY: battle model (TREY_PLAN.md 5.7, D5). Level matters much less to stats and damage.
//
// Effective level = floor + level * (100 - floor) / 100
//   floor 50: level 1 -> 50, level 10 -> 55, level 50 -> 75, level 100 -> 100.
//   A level 10 vs level 50 stat ratio becomes 55/75 = 0.73 instead of 10/50 = 0.20.
// Used for stats (CalculateMonStats), the level term of the damage formula, and level-based
// fixed damage (Seismic Toss, Night Shade, Psywave). Not used for EXP, catch rates, OHKO checks,
// Pay Day or anything else that reads the real level.

static inline s32 TreyGetStatLevelWithFloor(s32 level, s32 floor)
{
    if (floor <= 0)
        return level;
    return floor + (level * (100 - floor)) / 100;
}

// The expansion's own tests (make check) are written against the vanilla formulas,
// so test builds use the real level. TREY's own tests call TreyGetStatLevelWithFloor directly.
static inline s32 TreyGetStatLevel(s32 level)
{
#if TESTING
    return level;
#else
    return TreyGetStatLevelWithFloor(level, TREY_STAT_LEVEL_FLOOR);
#endif
}

#endif // GUARD_TREY_BATTLE_H
