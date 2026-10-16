#ifndef GUARD_TREY_DEX_H
#define GUARD_TREY_DEX_H

// TREY (TREY_PLAN.md E13, Phase 4 chunk 4d): regional Pokédexes, professor unlocks and the personal
// discovery numbers that replace every canon dex number.

#include "constants/trey_dex.h"
#include "constants/regions.h"

// Discovery order: National numbers in the order the player first saw them.
void TreyDex_ResetDiscovery(void);
u32 TreyDex_GetDiscoveryCount(void);
u16 TreyDex_GetDiscoveryAt(u32 index);      // National number, 0 past the end
u16 TreyDex_GetDiscoveryNumber(u16 natDex); // 1-based discovery number, 0 = not discovered yet
void TreyDex_OnFirstSeen(u16 natDex);       // called by GetSetPokedexFlag the first time a Pokémon is seen
void TreyDex_Repair(void);                  // adds any seen Pokémon missing from the list (National order)

// Regional dexes
bool32 TreyDex_IsInDex(u32 dex, u16 natDex);
bool32 TreyDex_IsUnlocked(u32 dex);
void TreyDex_Unlock(u32 dex);
void TreyDex_UnlockFromVar(void);           // special: VAR_0x8004 = TREY_DEX_*
u32 TreyDex_GetDexOfRegion(enum Region region); // TREY_DEX_NATIONAL if the region has no dex
u32 TreyDex_GetCurrentRegionDex(void);
const u8 *TreyDex_GetName(u32 dex);
u32 TreyDex_CountSeen(u32 dex);
u32 TreyDex_CountCaught(u32 dex);

// Game hooks
void TreyDex_InitNewGame(void);             // National dex on, debug unlocks
void TreyDex_OnMapEnter(void);              // first arrival in a region
bool32 TreyDex_TryRunArrivalScript(void);   // field: runs the pending first-arrival script

#endif // GUARD_TREY_DEX_H
