// TREY: Rock Climb, Gen 4 style (TREY_PLAN.md 5.3). Face a rock wall (MB_ROCK_CLIMB) going up or down
// and press A; the player climbs along the wall at a steady pace, using the normal walking animation,
// until they reach the first tile that is not a rock wall. Sideways walls only work if
// TREY_ROCK_CLIMB_ALLOW_SIDEWAYS is 1 (include/config/trey.h).

#include "global.h"
#include "event_data.h"
#include "event_object_movement.h"
#include "field_effect.h"
#include "field_player_avatar.h"
#include "metatile_behavior.h"
#include "script.h"
#include "task.h"
#include "constants/field_effects.h"

#define TREY_ROCK_CLIMB_MAX_STEPS 64 // safety stop for badly drawn walls

#define tState  data[0]
#define tMonId  data[1]
#define tDir    data[2]
#define tSteps  data[3]

enum
{
    CLIMB_SHOW_MON,
    CLIMB_WAIT_SHOW_MON,
    CLIMB_STEP,
    CLIMB_WAIT_STEP,
    CLIMB_END,
};

static void Task_TreyRockClimb(u8 taskId)
{
    struct Task *task = &gTasks[taskId];
    struct ObjectEvent *player = &gObjectEvents[gPlayerAvatar.objectEventId];

    switch (task->tState)
    {
    case CLIMB_SHOW_MON:
        if (ObjectEventIsMovementOverridden(player) && !ObjectEventClearHeldMovementIfFinished(player))
            break;
        gFieldEffectArguments[0] = task->tMonId;
        FieldEffectStart(FLDEFF_FIELD_MOVE_SHOW_MON_INIT);
        task->tState = CLIMB_WAIT_SHOW_MON;
        break;
    case CLIMB_WAIT_SHOW_MON:
        if (FieldEffectActiveListContains(FLDEFF_FIELD_MOVE_SHOW_MON))
            break;
        gPlayerAvatar.flags |= PLAYER_AVATAR_FLAG_CLIMBING;
        task->tState = CLIMB_STEP;
        // fallthrough
    case CLIMB_STEP:
        ObjectEventSetHeldMovement(player, GetWalkSlowMovementAction(task->tDir)); // Waterfall-like pace
        task->tSteps++;
        task->tState = CLIMB_WAIT_STEP;
        break;
    case CLIMB_WAIT_STEP:
        if (!ObjectEventClearHeldMovementIfFinished(player))
            break;
        if (MetatileBehavior_IsRockClimb(player->currentMetatileBehavior) && task->tSteps < TREY_ROCK_CLIMB_MAX_STEPS)
            task->tState = CLIMB_STEP; // still on the wall
        else
            task->tState = CLIMB_END;
        break;
    case CLIMB_END:
        gPlayerAvatar.flags &= ~PLAYER_AVATAR_FLAG_CLIMBING;
        gPlayerAvatar.preventStep = FALSE;
        DestroyTask(taskId);
        ScriptContext_Enable();
        break;
    }
}

// special, used by EventScript_TreyRockClimb. VAR_0x8004 = party slot of the Pokémon that climbs.
void TreyRockClimb_Start(void)
{
    u8 taskId = CreateTask(Task_TreyRockClimb, 0xFF);
    gPlayerAvatar.preventStep = TRUE;
    gTasks[taskId].tMonId = gSpecialVar_0x8004;
    gTasks[taskId].tDir = GetPlayerFacingDirection();
    gTasks[taskId].tSteps = 0;
}

#undef tState
#undef tMonId
#undef tDir
#undef tSteps
