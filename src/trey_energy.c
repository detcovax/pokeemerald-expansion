// TREY: Energy (TREY_PLAN.md 5.6, D23). See include/trey_energy.h.

#include "global.h"
#include "battle.h"
#include "battle_interface.h"
#include "caps.h"
#include "item.h"
#include "constants/item_effects.h"
#include "constants/items.h"
#include "move.h"
#include "pokemon.h"
#include "trey_battle.h"
#include "trey_energy.h"
#include "constants/moves.h"
#include "constants/species.h"

struct TreySpeciesEnergyOverride
{
    u16 species;
    u8 baseEnergy;
    u8 energyEVYield;
};

struct TreyMoveEnergyOverride
{
    u16 move;
    u8 cost;
};

#include "data/trey/energy_overrides.h"

static const struct TreySpeciesEnergyOverride *FindSpeciesOverride(u16 species)
{
    u32 i;
    for (i = 0; sTreySpeciesEnergyOverrides[i].species != SPECIES_NONE; i++)
    {
        if (sTreySpeciesEnergyOverrides[i].species == species)
            return &sTreySpeciesEnergyOverrides[i];
    }
    return NULL;
}

u32 TreyEnergy_GetBase(u16 species)
{
    const struct TreySpeciesEnergyOverride *o = FindSpeciesOverride(species);
    if (o != NULL)
        return o->baseEnergy;
    return gSpeciesInfo[SanitizeSpeciesId(species)].baseHP;
}

u32 TreyEnergy_GetEVYield(u16 species)
{
    const struct TreySpeciesEnergyOverride *o = FindSpeciesOverride(species);
    if (o != NULL)
        return o->energyEVYield;
    return gSpeciesInfo[SanitizeSpeciesId(species)].evYield_HP;
}

u32 TreyEnergy_CalcMax(u16 species, u32 level, u32 iv, u32 ev)
{
    u32 statLevel = TreyGetStatLevel(level);
    u32 value = ((2 * TreyEnergy_GetBase(species) + iv + ev / 4) * statLevel) / 100 + 5;
    if (species == SPECIES_NONE || species == SPECIES_EGG)
        return 0;
    return min(value, TREY_ENERGY_MAX_VALUE);
}

u32 TreyEnergy_GetBoxMonMax(struct BoxPokemon *boxMon)
{
    u16 species = GetBoxMonData(boxMon, MON_DATA_SPECIES, NULL);
    return TreyEnergy_CalcMax(species,
                              GetLevelFromBoxMonExp(boxMon),
                              GetBoxMonData(boxMon, MON_DATA_ENERGY_IV, NULL),
                              GetBoxMonData(boxMon, MON_DATA_ENERGY_EV, NULL));
}

u32 TreyEnergy_GetMonMax(struct Pokemon *mon)
{
    return TreyEnergy_GetBoxMonMax(&mon->box);
}

u32 TreyEnergy_GetMoveCost(u16 move)
{
    u32 i, pp, cost;

    for (i = 0; sTreyMoveEnergyOverrides[i].move != MOVE_NONE; i++)
    {
        if (sTreyMoveEnergyOverrides[i].move == move)
            return sTreyMoveEnergyOverrides[i].cost;
    }
    if (move == MOVE_NONE || move == MOVE_STRUGGLE || move >= MOVES_COUNT_ALL)
        return 0; // Struggle is free: it is what a Pokémon uses when it cannot afford anything

    // round(SCALE / PP), then x power factor x accuracy factor. Worked in hundredths, rounded at the end.
    pp = GetMovePP(move);
    if (pp == 0)
        return 0;
    cost = ((TREY_ENERGY_COST_SCALE + pp / 2) / pp) * 100;
    if (GetMoveCategory(move) == DAMAGE_CATEGORY_STATUS)
        cost = cost * 85 / 100;
    else
        cost = cost * (400 + (s32)GetMovePower(move) - 80) / 400;
    if (GetMoveAccuracy(move) != 0 && GetMoveAccuracy(move) < 100)
        cost = cost * 95 / 100;
    cost = (cost + 50) / 100; // round to whole Energy
    return max(cost, 1);
}

void TreyEnergy_RefillBoxMon(struct BoxPokemon *boxMon)
{
    u16 energy = TreyEnergy_GetBoxMonMax(boxMon);
    SetBoxMonData(boxMon, MON_DATA_ENERGY, &energy);
}

void TreyEnergy_Refill(struct Pokemon *mon)
{
    TreyEnergy_RefillBoxMon(&mon->box);
}

void TreyEnergy_OnStatsRecalculated(struct Pokemon *mon, u32 oldLevel, u32 newLevel)
{
    u16 species = GetMonData(mon, MON_DATA_SPECIES, NULL);
    u32 iv = GetMonData(mon, MON_DATA_ENERGY_IV, NULL);
    u32 ev = GetMonData(mon, MON_DATA_ENERGY_EV, NULL);
    u32 newMax = TreyEnergy_CalcMax(species, newLevel, iv, ev);
    u32 current = GetMonData(mon, MON_DATA_ENERGY, NULL);
    u16 value;

    // Levelling up adds the gained max Energy to current Energy, like HP.
    if (oldLevel != 0 && newLevel > oldLevel)
    {
        u32 oldMax = TreyEnergy_CalcMax(species, oldLevel, iv, ev);
        if (newMax > oldMax)
            current += newMax - oldMax;
    }
    value = min(current, newMax);
    SetMonData(mon, MON_DATA_ENERGY, &value);
}

// ---------------------------------------------------------------------------
// Battle (step E2)
// ---------------------------------------------------------------------------
u32 TreyEnergy_GetBattlerEnergy(u32 battler)
{
    return GetMonData(GetBattlerMon(battler), MON_DATA_ENERGY, NULL);
}

// Cost of the move in the battler's slot. Each Pokémon with Pressure on the other side
// multiplies the cost by TREY_ENERGY_PRESSURE_PERCENT, rounded up.
u32 TreyEnergy_GetBattlerMoveCost(u32 battler, u32 moveIndex, u32 pressureCount)
{
    u32 cost = TreyEnergy_GetMoveCost(gBattleMons[battler].moves[moveIndex]);
    while (pressureCount-- > 0)
        cost = (cost * TREY_ENERGY_PRESSURE_PERCENT + 99) / 100;
    return cost;
}

bool32 TreyEnergy_BattlerCanAffordMove(u32 battler, u32 moveIndex)
{
    // Pressure is not counted here, like PP: a move can be chosen with enough Energy for its
    // normal cost, and Pressure then takes whatever is left if it is short.
    return TreyEnergy_GetBattlerEnergy(battler) >= TreyEnergy_GetBattlerMoveCost(battler, moveIndex, 0);
}

void TreyEnergy_BattlerSpend(u32 battler, u32 amount)
{
    struct Pokemon *mon = GetBattlerMon(battler);
    u32 current = GetMonData(mon, MON_DATA_ENERGY, NULL);
    u16 value = (current > amount) ? current - amount : 0;
    SetMonData(mon, MON_DATA_ENERGY, &value);
    TreyEnergy_UpdateHealthboxBar(battler); // E4: redraw the Energy bar
}

// Battle drain (Spite, Eerie Spell, Grudge).
u32 TreyEnergy_BattlerDrain(u32 battler, u32 amount)
{
    u32 current = TreyEnergy_GetBattlerEnergy(battler);
    amount = min(amount, current);
    TreyEnergy_BattlerSpend(battler, amount);
    return amount;
}

// ---------------------------------------------------------------------------
// Items (step E3)
// ---------------------------------------------------------------------------
// Ether and Elixir: TREY_ENERGY_ETHER_AMOUNT. Max Ether and Max Elixir: full. Leppa Berry: TREY_ENERGY_LEPPA_AMOUNT.
u32 TreyEnergy_GetItemRestoreAmount(u16 item)
{
    const u8 *effect = GetItemEffect(item);
    if (item == ITEM_LEPPA_BERRY)
        return TREY_ENERGY_LEPPA_AMOUNT;
    if (effect != NULL && effect[6] == ITEM6_HEAL_PP_FULL)
        return TREY_ENERGY_MAX_VALUE;
    return TREY_ENERGY_ETHER_AMOUNT;
}

bool32 TreyEnergy_IsFull(struct Pokemon *mon)
{
    return GetMonData(mon, MON_DATA_ENERGY, NULL) >= TreyEnergy_GetMonMax(mon);
}

u32 TreyEnergy_Restore(struct Pokemon *mon, u32 amount)
{
    u32 current = GetMonData(mon, MON_DATA_ENERGY, NULL);
    u32 max = TreyEnergy_GetMonMax(mon);
    u16 value;
    if (current >= max)
        return 0;
    amount = min(amount, max - current);
    value = current + amount;
    SetMonData(mon, MON_DATA_ENERGY, &value);
    return amount;
}

// PP Up and PP Max are Energy vitamins.
u32 TreyEnergy_GetVitaminEVs(u16 item)
{
    return (item == ITEM_PP_MAX) ? TREY_ENERGY_PP_MAX_EVS : TREY_ENERGY_PP_UP_EVS;
}

u32 TreyEnergy_AddEVs(struct Pokemon *mon, u32 amount)
{
    u32 ev = GetMonData(mon, MON_DATA_ENERGY_EV, NULL);
    u32 total = GetMonEVCount(mon);
    u32 cap = !B_EV_ITEMS_CAP ? MAX_TOTAL_EVS : GetCurrentEVCap();
    u8 value;

    if (ev >= MAX_PER_STAT_EVS || total >= cap)
        return 0;
    amount = min(amount, MAX_PER_STAT_EVS - ev);
    amount = min(amount, cap - total);
    value = ev + amount;
    SetMonData(mon, MON_DATA_ENERGY_EV, &value);
    CalculateMonStats(mon); // raises max Energy; current Energy is unchanged
    return amount;
}
