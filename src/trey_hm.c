// TREY: HMs and Teleport (TREY_PLAN.md 5.3). See include/trey_hm.h.

#include "global.h"
#include "event_data.h"
#include "event_object_movement.h"
#include "field_effect.h"
#include "field_player_avatar.h"
#include "follower_npc.h"
#include "overworld.h"
#include "palette.h"
#include "party_menu.h"
#include "pokemon.h"
#include "script.h"
#include "trey_hm.h"
#include "constants/field_effects.h"
#include "constants/moves.h"
#include "field_screen_effect.h"

struct TreyHM
{
    u16 move;
    u16 flag;
};

// The TREY HM list, in the order from the design ("to do.txt").
static const struct TreyHM sTreyHMs[] =
{
    { MOVE_TELEPORT,   FLAG_TREY_HM_TELEPORT },
    { MOVE_CUT,        FLAG_TREY_HM_CUT },
    { MOVE_FLY,        FLAG_TREY_HM_FLY },
    { MOVE_SURF,       FLAG_TREY_HM_SURF },
    { MOVE_STRENGTH,   FLAG_TREY_HM_STRENGTH },
    { MOVE_FLASH,      FLAG_TREY_HM_FLASH },
    { MOVE_WHIRLPOOL,  FLAG_TREY_HM_WHIRLPOOL },
    { MOVE_WATERFALL,  FLAG_TREY_HM_WATERFALL },
    { MOVE_ROCK_SMASH, FLAG_TREY_HM_ROCK_SMASH },
    { MOVE_DIVE,       FLAG_TREY_HM_DIVE },
    { MOVE_DEFOG,      FLAG_TREY_HM_DEFOG },
    { MOVE_ROCK_CLIMB, FLAG_TREY_HM_ROCK_CLIMB },
    { MOVE_DIG,        FLAG_TREY_HM_DIG },
};

u16 TreyHM_GetUnlockFlag(u16 move)
{
    u32 i;
    for (i = 0; i < ARRAY_COUNT(sTreyHMs); i++)
    {
        if (sTreyHMs[i].move == move)
            return sTreyHMs[i].flag;
    }
    return 0;
}

bool32 TreyHM_IsHM(u16 move)
{
    return TreyHM_GetUnlockFlag(move) != 0;
}

bool32 TreyHM_IsUnlocked(u16 move)
{
    u16 flag = TreyHM_GetUnlockFlag(move);
    return flag != 0 && FlagGet(flag);
}

bool32 TreyHM_SpeciesCanLearn(u16 species, u16 move)
{
    u32 i;
    const struct LevelUpMove *learnset;

    if (CanLearnTeachableMove(species, move))
        return TRUE;
    learnset = GetSpeciesLevelUpLearnset(species);
    for (i = 0; learnset != NULL && learnset[i].move != LEVEL_UP_MOVE_END; i++)
    {
        if (learnset[i].move == move)
            return TRUE;
    }
    return FALSE;
}

bool32 TreyHM_MonCanUseInField(struct Pokemon *mon, u16 move)
{
    u16 species = GetMonData(mon, MON_DATA_SPECIES);

    if (species == SPECIES_NONE || GetMonData(mon, MON_DATA_IS_EGG))
        return FALSE;
    if (!TreyHM_IsHM(move))
        return MonKnowsMove(mon, move);
    if (!TreyHM_IsUnlocked(move))
        return FALSE;
    return MonKnowsMove(mon, move) || TreyHM_SpeciesCanLearn(species, move);
}

u8 TreyHM_FindPartyMon(u16 move)
{
    u8 i;
    for (i = 0; i < PARTY_SIZE; i++)
    {
        if (GetMonData(&gPlayerParty[i], MON_DATA_SPECIES) == SPECIES_NONE)
            break;
        if (TreyHM_MonCanUseInField(&gPlayerParty[i], move))
            return i;
    }
    return PARTY_SIZE;
}

// ---------------------------------------------------------------------------
// Teleport: fast travel to any visited Pokémon Center, chosen on the fly map
// ---------------------------------------------------------------------------

static EWRAM_DATA bool8 sTeleportPending = FALSE;

void TreyTeleport_SetPending(bool32 pending)
{
    sTeleportPending = pending;
}

bool32 TreyTeleport_IsPending(void)
{
    return sTeleportPending;
}

// gFieldCallback after a fly-map choice made through Teleport: play the Teleport animation,
// then warp to the chosen town (the warp was already set by the fly map).
void FieldCallback_TreyTeleport(void)
{
    gFieldCallback = NULL;
    RemoveFollowingPokemon();
    FadeInFromBlack();
    LockPlayerFieldControls();
    Overworld_ResetStateAfterTeleport();
    gFieldEffectArguments[0] = (u32)GetCursorSelectionMonId();
    FieldEffectStart(FLDEFF_USE_TELEPORT);
}
