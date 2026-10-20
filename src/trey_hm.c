// TREY: HMs and Teleport (TREY_PLAN.md 5.3). See include/trey_hm.h.

#include "global.h"
#include "battle_util.h"
#include "constants/abilities.h"
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
    // Sky HMs (3f), used while soaring: Gust pushes storm puffs, Whirlwind flies through cyclones,
    // Updraft rides rising-air columns north.
    { MOVE_GUST,       FLAG_TREY_HM_GUST },
    { MOVE_WHIRLWIND,  FLAG_TREY_HM_WHIRLWIND },
    { MOVE_UPDRAFT,    FLAG_TREY_HM_UPDRAFT },
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

bool32 TreyHM_IsSkyHM(u16 move)
{
    return move == MOVE_GUST || move == MOVE_WHIRLWIND || move == MOVE_UPDRAFT;
}

// Sky Battle rules by species: Flying type or Levitate in any ability slot, and not on the ban list.
bool32 TreyHM_SpeciesIsSkyEligible(u16 species)
{
    u32 i;
    bool32 eligible = gSpeciesInfo[species].types[0] == TYPE_FLYING || gSpeciesInfo[species].types[1] == TYPE_FLYING;

    for (i = 0; i < NUM_ABILITY_SLOTS && !eligible; i++)
    {
        if (gSpeciesInfo[species].abilities[i] == ABILITY_LEVITATE)
            eligible = TRUE;
    }
    return eligible && !gSpeciesInfo[species].isSkyBattleBanned;
}

bool32 TreyHM_SpeciesCanLearn(u16 species, u16 move)
{
    u32 i;
    const struct LevelUpMove *learnset;

    // David, 2026-10-12: every Pokémon that can take part in a Sky Battle can learn the three sky HMs.
    if (TreyHM_IsSkyHM(move) && TreyHM_SpeciesIsSkyEligible(species))
        return TRUE;
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
        if (GetMonData(&gParties[B_TRAINER_PLAYER][i], MON_DATA_SPECIES) == SPECIES_NONE)
            break;
        if (TreyHM_MonCanUseInField(&gParties[B_TRAINER_PLAYER][i], move))
            return i;
    }
    return PARTY_SIZE;
}

// special (6a): VAR_RESULT = party slot of the first Pokémon that knows HEADBUTT, or PARTY_SIZE.
void TreyHeadbutt_FindPartyMon(void)
{
    u8 i;
    gSpecialVar_Result = PARTY_SIZE;
    for (i = 0; i < PARTY_SIZE; i++)
    {
        struct Pokemon *mon = &gParties[B_TRAINER_PLAYER][i];
        if (GetMonData(mon, MON_DATA_SPECIES) == SPECIES_NONE)
            break;
        if (!GetMonData(mon, MON_DATA_IS_EGG) && MonKnowsMove(mon, MOVE_HEADBUTT))
        {
            gSpecialVar_Result = i;
            return;
        }
    }
}

// special for the treycheckpartymove script macro (upstream 1.16 removed checkpartymove).
// VAR_0x8004 = move in; VAR_RESULT = party slot or PARTY_SIZE, VAR_0x8004 = that Pokémon's species.
void TreyHM_CheckPartyMove(void)
{
    u8 slot = TreyHM_FindPartyMon(gSpecialVar_0x8004);
    gSpecialVar_Result = slot;
    if (slot < PARTY_SIZE)
        gSpecialVar_0x8004 = GetMonData(&gParties[B_TRAINER_PLAYER][slot], MON_DATA_SPECIES);
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

u32 TreyHM_Count(void)
{
    return ARRAY_COUNT(sTreyHMs);
}

u16 TreyHM_GetMove(u32 index)
{
    return index < ARRAY_COUNT(sTreyHMs) ? sTreyHMs[index].move : MOVE_NONE;
}

// David, 2026-10-12: all HMs a species could learn are always in the move relearner; TMs are still
// taught from the bag.
u32 TreyHM_AppendRelearnableMoves(u16 species, const u16 *knownMoves, u16 *moves, u32 numMoves, u32 maxMoves)
{
    u32 i, j;

    for (i = 0; i < ARRAY_COUNT(sTreyHMs) && numMoves < maxMoves; i++)
    {
        u16 move = sTreyHMs[i].move;
        bool32 skip = !TreyHM_SpeciesCanLearn(species, move);

        for (j = 0; j < MAX_MON_MOVES && !skip; j++)
        {
            if (knownMoves[j] == move)
                skip = TRUE;
        }
        for (j = 0; j < numMoves && !skip; j++)
        {
            if (moves[j] == move)
                skip = TRUE;
        }
        if (!skip)
            moves[numMoves++] = move;
    }
    return numMoves;
}

void TreyHM_DebugUnlockAll(void)
{
    u32 i;
    if (!TREY_DEBUG_UNLOCK_ALL_HMS)
        return;
    for (i = 0; i < ARRAY_COUNT(sTreyHMs); i++)
        FlagSet(sTreyHMs[i].flag);
}
