// TREY: Updraft, the sky Waterfall HM's battle move (TREY_PLAN.md 3f)
#include "global.h"
#include "test/battle.h"

SINGLE_BATTLE_TEST("TREY Updraft: deals damage and raises the user's Speed")
{
    GIVEN {
        ASSUME(GetMoveType(MOVE_UPDRAFT) == TYPE_FLYING);
        ASSUME(GetMovePower(MOVE_UPDRAFT) == 50);
        PLAYER(SPECIES_PIDGEY) { Moves(MOVE_UPDRAFT); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(player, MOVE_UPDRAFT); }
    } SCENE {
        ANIMATION(ANIM_TYPE_MOVE, MOVE_UPDRAFT, player);
        HP_BAR(opponent);
        ANIMATION(ANIM_TYPE_GENERAL, B_ANIM_STATS_CHANGE, player);
    } THEN {
        EXPECT_EQ(player->statStages[STAT_SPEED], DEFAULT_STAT_STAGE + 1);
    }
}
