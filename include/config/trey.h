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
#define TREY_SAVE_VERSION  2 // 2: 10-bit met location + Orange variant bit in Pokémon data (Phase 1b)

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

// Settings are added here phase by phase as each system is built:
//   Phase 3: traversal (TREY_STAMINA_ENABLED and stamina tuning)
//   Phase 4: seasons, transit, quests

#endif // GUARD_CONFIG_TREY_H
