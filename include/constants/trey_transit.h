#ifndef GUARD_CONSTANTS_TREY_TRANSIT_H
#define GUARD_CONSTANTS_TREY_TRANSIT_H

// TREY (TREY_PLAN.md 5.4, Phase 4 chunk 4c): ships and trains. #defines only (read by scripts too).
#define TRANSIT_SHIP    0
#define TRANSIT_TRAIN   1
#define TRANSIT_BUS     2 // TREY (6d-2, D48/D50): Goldenrod/Jubilife <-> Mossui; ridden without an on-board map

// Stops. The table is src/trey_transit.c. Stops whose map doesn't exist yet are never offered.
#define TRANSIT_STOP_SLATEPORT        0
#define TRANSIT_STOP_LILYCOVE         1
#define TRANSIT_STOP_BATTLE_FRONTIER  2
#define TRANSIT_STOP_VERMILION        3
#define TRANSIT_STOP_OLIVINE          4
#define TRANSIT_STOP_HAMLIN           5  // TREY (6c-4b, D43): Orange stop, was VALENCIA
#define TRANSIT_STOP_ONE_ISLAND       6
#define TRANSIT_STOP_CANALAVE         7
#define TRANSIT_STOP_MOSSUI           8  // bus (6d-2, D48); was a ship stop
#define TRANSIT_STOP_GOLDENROD        9  // train
#define TRANSIT_STOP_SAFFRON          10 // train
#define TRANSIT_STOP_JUBILIFE         11 // train
#define TRANSIT_STOP_GOLDENROD_BUS    12 // bus (6d-2)
#define TRANSIT_STOP_JUBILIFE_BUS     13 // bus (6d-2)
#define TRANSIT_STOP_COUNT            14 // up to 32 (visited flags reserved)
#define TRANSIT_STOP_NONE             0xFF

// VAR_TREY_TRANSIT_STATE
#define TRANSIT_STATE_NONE      0
#define TRANSIT_STATE_BOARDED   1 // walked on board, not yet under way
#define TRANSIT_STATE_UNDERWAY  2 // counting steps; resting in a cabin bed arrives at once
#define TRANSIT_STATE_ARRIVED   3 // the attendant at the exit lets you off

#define TRANSIT_STEPS_PER_TRIP  150

#endif // GUARD_CONSTANTS_TREY_TRANSIT_H
