// TREY: Energy in battle (TREY_PLAN.md 5.6, step E2)
#include "global.h"
#include "test/battle.h"
#include "trey_energy.h"

SINGLE_BATTLE_TEST("TREY Energy: using a move spends its Energy cost and PP stays full")
{
    GIVEN {
        PLAYER(SPECIES_WOBBUFFET) { Moves(MOVE_TACKLE); Energy(200); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(player, MOVE_TACKLE); }
    } THEN {
        EXPECT_EQ(GetMonData(&gPlayerParty[0], MON_DATA_ENERGY), 200 - TreyEnergy_GetMoveCost(MOVE_TACKLE));
        EXPECT_EQ(player->pp[0], GetMovePP(MOVE_TACKLE));
    }
}

SINGLE_BATTLE_TEST("TREY Energy: opponents spend Energy too")
{
    GIVEN {
        PLAYER(SPECIES_WOBBUFFET);
        OPPONENT(SPECIES_WOBBUFFET) { Moves(MOVE_TACKLE); Energy(100); }
    } WHEN {
        TURN { MOVE(opponent, MOVE_TACKLE); }
    } THEN {
        EXPECT_EQ(GetMonData(&gEnemyParty[0], MON_DATA_ENERGY), 100 - TreyEnergy_GetMoveCost(MOVE_TACKLE));
    }
}

SINGLE_BATTLE_TEST("TREY Energy: a Pokemon that cannot afford any move uses Struggle")
{
    GIVEN {
        PLAYER(SPECIES_WOBBUFFET) { Moves(MOVE_HYDRO_PUMP); Energy(1); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(player, MOVE_HYDRO_PUMP, allowed: FALSE); }
    } SCENE {
        ANIMATION(ANIM_TYPE_MOVE, MOVE_STRUGGLE, player);
    } THEN {
        EXPECT_EQ(GetMonData(&gPlayerParty[0], MON_DATA_ENERGY), 1); // Struggle is free
    }
}

SINGLE_BATTLE_TEST("TREY Energy: Pressure multiplies the cost")
{
    GIVEN {
        PLAYER(SPECIES_WOBBUFFET) { Moves(MOVE_FLAMETHROWER); Energy(100); }
        OPPONENT(SPECIES_WOBBUFFET) { Ability(ABILITY_PRESSURE); }
    } WHEN {
        TURN { MOVE(player, MOVE_FLAMETHROWER); }
    } THEN {
        EXPECT_EQ(GetMonData(&gPlayerParty[0], MON_DATA_ENERGY), 100 - (TreyEnergy_GetMoveCost(MOVE_FLAMETHROWER) * TREY_ENERGY_PRESSURE_PERCENT + 99) / 100);
    }
}

TEST("TREY Energy: healing refills Energy")
{
    struct Pokemon mon;
    u16 energy = 0;
    CreateMon(&mon, SPECIES_WOBBUFFET, 50, 0, FALSE, 0, OT_ID_PRESET, 0);
    SetMonData(&mon, MON_DATA_ENERGY, &energy);
    HealPokemon(&mon);
    EXPECT_EQ(GetMonData(&mon, MON_DATA_ENERGY), TreyEnergy_GetMonMax(&mon));
}
