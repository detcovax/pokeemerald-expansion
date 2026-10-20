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
#define TREY_SAVE_VERSION  4 // 2: 10-bit met location + Orange variant bit (Phase 1b). 3: Energy replaces PP storage (E1). 4: Pokédex discovery order (4d)

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
// Testing only: 1 = every HM is unlocked when a new game starts. Keep at 0 for real builds.
#define TREY_DEBUG_UNLOCK_ALL_HMS      0
// Debug (4a): every region map page counts as visited, so the Teleport map and the Pokédex area page
// can flip through all regions before they have maps. Set back to 0 for real play.
#define TREY_DEBUG_ALL_REGION_MAPS      0
// Debug (4c): you hold the S.S. Ticket and every transit stop counts as visited, so the ferries can be tested
// before the Kanto story exists. Set to 0 for real play.
#define TREY_DEBUG_ALL_TRANSIT          0
// Debug (4d): every regional Pokédex is unlocked when a new game starts, without meeting the professors.
// Set to 0 for real play.
// Kanto (5a, TREY_PLAN.md D25): 1 = the FRLG tilesets, overworld sprites and door animations are built into
// the TREY (Emerald) ROM, so the FRLG Kanto/Sevii maps can be used. Upstream only builds them for FireRed.
#define TREY_FRLG_DATA                  1
// Vertical slice (5b, TREY_PLAN.md D27): 1 = a new game skips Birch's speech and the truck. You wake up in your room in
// Pallet Town, pick boy/girl and a name, and get a Mew (src/trey_intro.c, data/scripts/trey_intro.inc). Placeholder until
// the real TREY intro (D25).
#define TREY_MINIMAL_INTRO              1
#define TREY_INTRO_MEW_LEVEL            100
// Battle difficulty (5d, TREY_PLAN.md 5.7a, D24): every TREY trainer (bosses, gym trainers, route trainers) is this level.
// tools/trey/check_trainers.py reads it and fails the build if a TREY trainer's team breaks its tier.
#define TREY_TRAINER_LEVEL              100
#define TREY_DEBUG_ALL_DEXES            0

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
// AI (step E5, trainers with AI_FLAG_ENERGY_AWARE, which AI_FLAG_SMART_TRAINER includes).
#define TREY_AI_SIMILAR_DAMAGE_PERCENT      90   // a cheaper move doing at least this % of the damage counts as "as good"
#define TREY_AI_SWITCH_LOW_ENERGY_PERCENT   50   // chance to switch when it can afford its cheapest attack fewer than 2 more times
#define TREY_AI_ETHER_ENERGY_PERCENT        25   // use an Ether once Energy is at or below this % and a damaging move is unaffordable
// Display (step E4).
// Testing only: 1 = the summary screen's skills page can cycle through IVs and EVs (Energy included).
#define TREY_DEBUG_SHOW_IVS_EVS         0

// Settings are added here phase by phase as each system is built:
//   Phase 4: seasons, transit, quests

#endif // GUARD_CONFIG_TREY_H
