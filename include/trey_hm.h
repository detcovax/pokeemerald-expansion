#ifndef GUARD_TREY_HM_H
#define GUARD_TREY_HM_H

// TREY: HMs (TREY_PLAN.md 5.3). Thirteen field moves are "HMs" (the 12 from the design plus Dig): each is unlocked by a flag
// (FLAG_TREY_HM_*, set by the tutorial). Once unlocked, any party Pokémon that CAN learn the move
// (level-up or teachable learnset) may use it in the field, without knowing it or using a move slot.
// Other field moves (Secret Power, Milk Drink, Soft-Boiled, Sweet Scent) still need the move known.

struct Pokemon;

u16 TreyHM_GetUnlockFlag(u16 move);              // 0 if the move is not a TREY HM
bool32 TreyHM_IsHM(u16 move);
bool32 TreyHM_IsUnlocked(u16 move);
bool32 TreyHM_SpeciesCanLearn(u16 species, u16 move);
bool32 TreyHM_MonCanUseInField(struct Pokemon *mon, u16 move);
u8 TreyHM_FindPartyMon(u16 move);                // party index, or PARTY_SIZE if none

// Teleport opens the fly map; these remember that the next fly-map choice is a Teleport.
void TreyTeleport_SetPending(bool32 pending);
bool32 TreyTeleport_IsPending(void);
void FieldCallback_TreyTeleport(void);

#endif // GUARD_TREY_HM_H
