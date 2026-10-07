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

// ---------------------------------------------------------------------------
// Step E3: items, Spite, Eerie Spell, Grudge
// ---------------------------------------------------------------------------
SINGLE_BATTLE_TEST("TREY Energy: Ether restores 50 Energy in battle without choosing a move")
{
    GIVEN {
        ASSUME(gItemsInfo[ITEM_ETHER].type == ITEM_USE_PARTY_MENU);
        PLAYER(SPECIES_WOBBUFFET) { Energy(10); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { USE_ITEM(player, ITEM_ETHER, partyIndex: 0); }
    } THEN {
        EXPECT_EQ(GetMonData(&gPlayerParty[0], MON_DATA_ENERGY), 10 + TREY_ENERGY_ETHER_AMOUNT);
    }
}

SINGLE_BATTLE_TEST("TREY Energy: Max Elixir fully restores Energy")
{
    GIVEN {
        PLAYER(SPECIES_WOBBUFFET) { Energy(10); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { USE_ITEM(player, ITEM_MAX_ELIXIR, partyIndex: 0); }
    } THEN {
        EXPECT_EQ(GetMonData(&gPlayerParty[0], MON_DATA_ENERGY), TreyEnergy_GetMonMax(&gPlayerParty[0]));
    }
}

SINGLE_BATTLE_TEST("TREY Energy: Leppa Berry restores 20 Energy once a move becomes unaffordable")
{
    GIVEN {
        PLAYER(SPECIES_WOBBUFFET) { Moves(MOVE_HYDRO_PUMP, MOVE_TACKLE); Item(ITEM_LEPPA_BERRY); Energy(25); }
        OPPONENT(SPECIES_WOBBUFFET);
    } WHEN {
        TURN { MOVE(player, MOVE_HYDRO_PUMP); }
    } THEN {
        EXPECT_EQ(GetMonData(&gPlayerParty[0], MON_DATA_ENERGY), 25 - TreyEnergy_GetMoveCost(MOVE_HYDRO_PUMP) + TREY_ENERGY_LEPPA_AMOUNT);
        EXPECT_EQ(player->item, ITEM_NONE);
    }
}

SINGLE_BATTLE_TEST("TREY Energy: Spite drains a fixed amount of Energy")
{
    u32 max = 0;
    GIVEN {
        PLAYER(SPECIES_WOBBUFFET) { Moves(MOVE_SPITE); Speed(5); }
        OPPONENT(SPECIES_WOBBUFFET) { Moves(MOVE_TACKLE); Speed(10); }
    } WHEN {
        TURN { MOVE(opponent, MOVE_TACKLE); MOVE(player, MOVE_SPITE); }
    } THEN {
        max = TreyEnergy_GetMonMax(&gEnemyParty[0]);
        EXPECT_EQ(GetMonData(&gEnemyParty[0], MON_DATA_ENERGY), max - TreyEnergy_GetMoveCost(MOVE_TACKLE) - TREY_ENERGY_SPITE_DRAIN);
    }
}

SINGLE_BATTLE_TEST("TREY Energy: Grudge drains half of the attacker's max Energy")
{
    u32 max = 0;
    GIVEN {
        PLAYER(SPECIES_WOBBUFFET) { Moves(MOVE_TACKLE); Speed(5); }
        OPPONENT(SPECIES_WOBBUFFET) { Moves(MOVE_GRUDGE); HP(1); Speed(10); }
    } WHEN {
        TURN { MOVE(opponent, MOVE_GRUDGE); MOVE(player, MOVE_TACKLE); }
    } THEN {
        max = TreyEnergy_GetMonMax(&gPlayerParty[0]);
        EXPECT_EQ(GetMonData(&gPlayerParty[0], MON_DATA_ENERGY),
                  max - TreyEnergy_GetMoveCost(MOVE_TACKLE) - (max * TREY_ENERGY_GRUDGE_PERCENT + 99) / 100);
    }
}

TEST("TREY Energy: PP Up and PP Max add Energy EVs and raise max Energy")
{
    struct Pokemon mon;
    u32 before;
    CreateMon(&mon, SPECIES_WOBBUFFET, 100, 0, FALSE, 0, OT_ID_PRESET, 0);
    before = TreyEnergy_GetMonMax(&mon);
    EXPECT_EQ(TreyEnergy_AddEVs(&mon, TreyEnergy_GetVitaminEVs(ITEM_PP_UP)), TREY_ENERGY_PP_UP_EVS);
    EXPECT_EQ(TreyEnergy_AddEVs(&mon, TreyEnergy_GetVitaminEVs(ITEM_PP_MAX)), TREY_ENERGY_PP_MAX_EVS);
    EXPECT_EQ(GetMonData(&mon, MON_DATA_ENERGY_EV), TREY_ENERGY_PP_UP_EVS + TREY_ENERGY_PP_MAX_EVS);
    EXPECT_GT(TreyEnergy_GetMonMax(&mon), before);
}

// ---------------------------------------------------------------------------
// Step E5: Energy-aware AI (AI_FLAG_ENERGY_AWARE, part of AI_FLAG_SMART_TRAINER)
// ---------------------------------------------------------------------------
AI_SINGLE_BATTLE_TEST("TREY Energy AI: prefers the cheaper of two moves that both knock out")
{
    GIVEN {
        ASSUME(TreyEnergy_GetMoveCost(MOVE_WATER_GUN) < TreyEnergy_GetMoveCost(MOVE_SURF));
        AI_FLAGS(AI_FLAG_CHECK_BAD_MOVE | AI_FLAG_CHECK_VIABILITY | AI_FLAG_TRY_TO_FAINT | AI_FLAG_ENERGY_AWARE);
        PLAYER(SPECIES_WOBBUFFET) { HP(1); }
        OPPONENT(SPECIES_WOBBUFFET) { Moves(MOVE_SURF, MOVE_WATER_GUN); }
    } WHEN {
        TURN { SCORE_GT(opponent, MOVE_WATER_GUN, MOVE_SURF); }
    }
}

AI_SINGLE_BATTLE_TEST("TREY Energy AI: a smart trainer switches out a Pokemon that can't afford to attack")
{
    GIVEN {
        AI_FLAGS(AI_FLAG_SMART_TRAINER);
        PLAYER(SPECIES_WOBBUFFET) { Moves(MOVE_TACKLE); }
        OPPONENT(SPECIES_WOBBUFFET) { Moves(MOVE_SURF); Energy(1); }
        OPPONENT(SPECIES_UMBREON) { Moves(MOVE_BITE); }
    } WHEN {
        TURN { MOVE(player, MOVE_TACKLE); EXPECT_SWITCH(opponent, 1); }
    }
}
