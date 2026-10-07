#ifndef GUARD_TREY_ENERGY_H
#define GUARD_TREY_ENERGY_H

// TREY: Energy, a seventh stat that replaces PP (TREY_PLAN.md 5.6, D23).
//
//   max Energy = (2 x base + IV + EV/4) x effectiveLevel / 100 + 5     (no nature, like HP)
//
// base and EV yield default to the species' base HP and HP EV yield; override per species in
// docs/trey/species_energy.csv. Move costs come from a formula; override per move in
// docs/trey/move_energy.csv. Current Energy, the Energy IV and the Energy EV are stored in the
// Pokémon data where PP used to be (MON_DATA_ENERGY, MON_DATA_ENERGY_IV, MON_DATA_ENERGY_EV).

struct Pokemon;
struct BoxPokemon;

#define TREY_ENERGY_MAX_VALUE 1023 // storage limit (10 bits)

u32 TreyEnergy_GetBase(u16 species);
u32 TreyEnergy_GetEVYield(u16 species);
u32 TreyEnergy_CalcMax(u16 species, u32 level, u32 iv, u32 ev);
u32 TreyEnergy_GetBoxMonMax(struct BoxPokemon *boxMon);
u32 TreyEnergy_GetMonMax(struct Pokemon *mon);
u32 TreyEnergy_GetMoveCost(u16 move);
void TreyEnergy_Refill(struct Pokemon *mon);
void TreyEnergy_RefillBoxMon(struct BoxPokemon *boxMon);

// Recalculates current Energy after a level change (called from CalculateMonStats).
// Battle (step E2). Energy lives in the party Pokémon; gBattleMons PP stays full and is unused.
u32 TreyEnergy_GetBattlerEnergy(u32 battler);
u32 TreyEnergy_GetBattlerMoveCost(u32 battler, u32 moveIndex, u32 pressureCount);
bool32 TreyEnergy_BattlerCanAffordMove(u32 battler, u32 moveIndex);
void TreyEnergy_BattlerSpend(u32 battler, u32 amount);
// Items (step E3).
u32 TreyEnergy_GetItemRestoreAmount(u16 item);
bool32 TreyEnergy_IsFull(struct Pokemon *mon);
u32 TreyEnergy_Restore(struct Pokemon *mon, u32 amount);   // returns the Energy restored
u32 TreyEnergy_AddEVs(struct Pokemon *mon, u32 amount);    // returns the Energy EVs added
u32 TreyEnergy_GetVitaminEVs(u16 item);
// Moves (step E3).
u32 TreyEnergy_BattlerDrain(u32 battler, u32 amount);      // returns the Energy drained
void TreyEnergy_OnStatsRecalculated(struct Pokemon *mon, u32 oldLevel, u32 newLevel);

#endif // GUARD_TREY_ENERGY_H
