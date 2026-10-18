#ifndef GUARD_TREY_SAVE_TYPES_H
#define GUARD_TREY_SAVE_TYPES_H

// TREY: save data structures (TREY_PLAN.md Section 4).
// Included by global.h. Sizes are set in include/config/trey.h.
//
// RULES (TREY_PLAN.md 2.2):
//  - New save data takes bytes from the matching reserved array: add the new field
//    directly ABOVE the reserved array and shrink the array by the same amount.
//    Never insert fields anywhere else in a save block.
//  - Every layout change bumps TREY_SAVE_VERSION. Exception: a new field carved from the TOP of a reserved
//    array whose all-zero value means "empty" (reserved bytes are always zero) reads correctly from an
//    older save, so it needs no bump (4f quest stages).

// Stored in SaveBlock2. Identifies a save written by this save layout.
struct TreySaveHeader
{
    u32 magic;   // TREY_SAVE_MAGIC
    u16 version; // TREY_SAVE_VERSION
    u16 flags;   // reserved for future use, always 0 for now
};

// Stored in SaveBlock3.
#define TREY_QUEST_SLOTS 256 // 4f: one stage byte per quest num (0 = not started, 255 = done)

struct TreySaveData
{
    // New SaveBlock3 fields go here (stamina, layer return warp, ...).
    u8 questStages[TREY_QUEST_SLOTS]; // 4f (TREY_PLAN.md E15)
    u8 reserved[TREY_SB3_RESERVED - TREY_QUEST_SLOTS];
};

#endif // GUARD_TREY_SAVE_TYPES_H
