#ifndef GUARD_TREY_SAVE_TYPES_H
#define GUARD_TREY_SAVE_TYPES_H

// TREY: save data structures (TREY_PLAN.md Section 4).
// Included by global.h. Sizes are set in include/config/trey.h.
//
// RULES (TREY_PLAN.md 2.2):
//  - New save data takes bytes from the matching reserved array: add the new field
//    directly ABOVE the reserved array and shrink the array by the same amount.
//    Never insert fields anywhere else in a save block.
//  - Every layout change bumps TREY_SAVE_VERSION.

// Stored in SaveBlock2. Identifies a save written by this save layout.
struct TreySaveHeader
{
    u32 magic;   // TREY_SAVE_MAGIC
    u16 version; // TREY_SAVE_VERSION
    u16 flags;   // reserved for future use, always 0 for now
};

// Stored in SaveBlock3.
struct TreySaveData
{
    // New SaveBlock3 fields go here (quest stages, stamina, layer return warp, ...).
    u8 reserved[TREY_SB3_RESERVED];
};

#endif // GUARD_TREY_SAVE_TYPES_H
