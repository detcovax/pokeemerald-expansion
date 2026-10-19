#ifndef GUARD_TREY_HM_H
#define GUARD_TREY_HM_H

// TREY: HMs (TREY_PLAN.md 5.3). Sixteen field moves are "HMs" (the 12 from the design, Dig, and the sky HMs Gust, Whirlwind and Updraft): each is unlocked by a flag
// (FLAG_TREY_HM_*, set by the tutorial). Once unlocked, any party Pokémon that CAN learn the move
// (level-up or teachable learnset) may use it in the field, without knowing it or using a move slot.
// Other field moves (Secret Power, Milk Drink, Soft-Boiled, Sweet Scent) still need the move known.

struct Pokemon;

u16 TreyHM_GetUnlockFlag(u16 move);              // 0 if the move is not a TREY HM
bool32 TreyHM_IsHM(u16 move);
bool32 TreyHM_IsUnlocked(u16 move);
bool32 TreyHM_SpeciesCanLearn(u16 species, u16 move);
bool32 TreyHM_IsSkyHM(u16 move);                 // Gust, Whirlwind, Updraft (3f)
bool32 TreyHM_SpeciesIsSkyEligible(u16 species); // Sky Battle rules by species: every one can learn the sky HMs
bool32 TreyHM_MonCanUseInField(struct Pokemon *mon, u16 move);
u8 TreyHM_FindPartyMon(u16 move);
void TreyHM_CheckPartyMove(void); // special: see the treycheckpartymove macro
void TreyHM_DebugUnlockAll(void); // new game: unlock every HM when TREY_DEBUG_UNLOCK_ALL_HMS is 1
u32 TreyHM_Count(void);
u16 TreyHM_GetMove(u32 index);
// Move relearner: adds every HM the species can learn (whether or not it is unlocked) that the
// Pokémon doesn't know and isn't listed yet. Returns the new count.
u32 TreyHM_AppendRelearnableMoves(u16 species, const u16 *knownMoves, u16 *moves, u32 numMoves, u32 maxMoves);                // party index, or PARTY_SIZE if none

// Teleport opens the fly map; these remember that the next fly-map choice is a Teleport.
void TreyTeleport_SetPending(bool32 pending);
bool32 TreyTeleport_IsPending(void);
void FieldCallback_TreyTeleport(void);

#endif // GUARD_TREY_HM_H
