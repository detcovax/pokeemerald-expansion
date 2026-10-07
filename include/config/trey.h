#ifndef GUARD_CONFIG_TREY_H
#define GUARD_CONFIG_TREY_H

// Pokémon TREY project settings.
// Every TREY-specific switch lives in this file. See TREY_PLAN.md (one folder above the repo).
// This file is also read by the assembler for scripts, so keep it to #defines only.

#define TREY_VERSION_MAJOR 0
#define TREY_VERSION_MINOR 1
#define TREY_VERSION_PATCH 0

// ---------------------------------------------------------------------------
// Save layout (Phase 1, TREY_PLAN.md Section 4)
// ---------------------------------------------------------------------------
// A save is only loaded if its header matches these two values.
// Bump TREY_SAVE_VERSION on ANY change to a save structure.
#define TREY_SAVE_MAGIC    0x59455254 // "TREY"
#define TREY_SAVE_VERSION  3 // 2: 10-bit met location + Orange variant bit (Phase 1b). 3: Energy replaces PP storage (E1)

// Reserved bytes at the end of each save block. New save data is carved out of these.
#define TREY_SB1_RESERVED  512
#define TREY_SB2_RESERVED  256
#define TREY_SB3_RESERVED  1024

// ---------------------------------------------------------------------------
// Battle model (Phase 2b, TREY_PLAN.md 5.7)
// ---------------------------------------------------------------------------
// Effective level for stats and damage = floor + level * (100 - floor) / 100. See include/trey_battle.h.
// 50 means a level 1 Pokémon fights like level 50 and a level 100 like level 100. 0 = vanilla formulas.
#define TREY_STAT_LEVEL_FLOOR   50
// Pokémon always obey, regardless of badges, level or original trainer (D12).
#define TREY_DISABLE_OBEDIENCE  1

// ---------------------------------------------------------------------------
// Battle gimmicks (Phase 2c, TREY_PLAN.md 5.13, D19/D20)
// ---------------------------------------------------------------------------
// Mega Evolution: on. The player needs ITEM_MEGA_RING (given in the Hoenn story). No setting needed.
// Terastallization: on. The player needs ITEM_TERA_ORB (Kitakami story); it recharges at Pokémon Centers.
// Z-Moves and Dynamax/Gigantamax: off for everyone.
#define TREY_DISABLE_ZMOVES     1
#define TREY_DISABLE_DYNAMAX    1

// ---------------------------------------------------------------------------
// Orange Islands variants (Phase 2d, TREY_PLAN.md 5.8, D18)
// ---------------------------------------------------------------------------
// Tint colour (RGB, 0-31 per channel) and strength (0 = none, 16 = solid colour).
#define TREY_ORANGE_TINT_COLOR      RGB(31, 15, 0)
#define TREY_ORANGE_TINT_STRENGTH   6
// Testing only: 1 = treat every map as the Orange Islands, so you can see the tint before any
// Orange Islands maps exist. Keep at 0 for real builds.
#define TREY_DEBUG_ORANGE_EVERYWHERE 0

// Breeding: the egg always takes the mother's form (the non-Ditto parent when breeding with Ditto),
// including Hisuian/Paldean forms, with no Everstone needed. The Orange variant also comes from the mother.
#define TREY_EGGS_INHERIT_MOTHER_FORM 1

// ---------------------------------------------------------------------------
// Traversal (Phase 3, TREY_PLAN.md 5.3)
// ---------------------------------------------------------------------------
// Rock Climb walls are climbed up or down only, like Gen 4. 1 = also allow sideways walls.
#define TREY_ROCK_CLIMB_ALLOW_SIDEWAYS 0

// ---------------------------------------------------------------------------
// Energy, replaces PP (TREY_PLAN.md 5.6, D23)
// ---------------------------------------------------------------------------
// Move cost = round(SCALE / PP) x power factor x accuracy factor (see src/trey_energy.c).
#define TREY_ENERGY_COST_SCALE          100
// Items (step E3).
#define TREY_ENERGY_ETHER_AMOUNT        50   // Ether and Elixir, one Pokémon
#define TREY_ENERGY_LEPPA_AMOUNT        20   // Leppa Berry, in battle
#define TREY_ENERGY_PP_UP_EVS           10   // PP Up = Energy vitamin
#define TREY_ENERGY_PP_MAX_EVS          30   // PP Max = Energy vitamin
// Moves and abilities (step E3).
#define TREY_ENERGY_PRESSURE_PERCENT    150  // moves used against Pressure cost 1.5x (rounded up)
#define TREY_ENERGY_SPITE_DRAIN         10
#define TREY_ENERGY_EERIE_SPELL_DRAIN   15
#define TREY_ENERGY_GRUDGE_PERCENT      50   // Grudge drains 50% of the attacker's max Energy

// Settings are added here phase by phase as each system is built:
//   Phase 4: seasons, transit, quests

#endif // GUARD_CONFIG_TREY_H
