#ifndef GUARD_TREY_REGIONAL_H
#define GUARD_TREY_REGIONAL_H

// TREY: regional variants (TREY_PLAN.md 5.8, D10/D18/D21).
//
// Orange Islands variants: every Pokémon created in the Orange Islands (wild, scripted wild battle,
// gift, and trainers' Pokémon) is an Orange variant: a per-Pokémon bit plus a palette tint. Sevii counts
// as Kanto, so Sevii Pokémon are never tinted. Eggs take the bit from the mother (the non-Ditto parent),
// and the hatched Pokémon keeps it.
//
// Hisuian and Paldean forms are separate species IDs, placed in encounter tables next to the normal
// form with their own rates (so they are found by chance alongside the normal form). The map check
// (tools/trey/check_maps.py) fails the build if a Hisuian form appears outside Sinnoh or a Paldean
// form outside Kitakami.

struct Pokemon;
struct BoxPokemon;

// TRUE when the current map is in the Orange Islands proper.
bool32 TreyOrange_IsActiveHere(void);

// Marks a newly created Pokémon as an Orange variant if the player is in the Orange Islands.
void TreyOrange_ApplyIfInOrangeIslands(struct Pokemon *mon);

// Copies the Orange bit from `from` to `to` (eggs from the mother, hatched Pokémon from the egg).
void TreyOrange_CopyBit(struct Pokemon *to, struct BoxPokemon *from);

// Returns `palette`, or a tinted copy of it if `mon` is an Orange variant.
// The copy lives in a small ring buffer: load it straight away, don't keep the pointer.
const u16 *TreyOrange_GetMonPalette(struct Pokemon *mon, const u16 *palette);
const u16 *TreyOrange_GetBoxMonPalette(struct BoxPokemon *boxMon, const u16 *palette);

#endif // GUARD_TREY_REGIONAL_H
