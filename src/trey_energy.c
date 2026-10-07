// TREY: Energy (TREY_PLAN.md 5.6, D23). See include/trey_energy.h.

#include "global.h"
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
    if (move == MOVE_NONE || move >= MOVES_COUNT_ALL)
        return 0;

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
