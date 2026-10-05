#ifndef GUARD_CONFIG_TREY_H
#define GUARD_CONFIG_TREY_H

// Pokémon TREY project settings.
// Every TREY-specific switch lives in this file. See TREY_PLAN.md (one folder above the repo).
// This file is also read by the assembler for scripts, so keep it to #defines only.

#define TREY_VERSION_MAJOR 0
#define TREY_VERSION_MINOR 0
#define TREY_VERSION_PATCH 0

// Settings are added here phase by phase as each system is built:
//   Phase 1: save layout (TREY_SAVE_VERSION, reserved space sizes)
//   Phase 2: battle model (TREY_STAT_LEVEL_FLOOR, TREY_DISABLE_OBEDIENCE, TREY_DISABLE_ZMOVES), Orange variants
//   Phase 3: traversal (TREY_STAMINA_ENABLED and stamina tuning)
//   Phase 4: seasons, transit, quests

#endif // GUARD_CONFIG_TREY_H
