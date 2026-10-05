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

// Settings are added here phase by phase as each system is built:
//   Phase 2: battle model (TREY_STAT_LEVEL_FLOOR, TREY_DISABLE_OBEDIENCE, TREY_DISABLE_ZMOVES), Orange variants
//   Phase 3: traversal (TREY_STAMINA_ENABLED and stamina tuning)
//   Phase 4: seasons, transit, quests

#endif // GUARD_CONFIG_TREY_H
