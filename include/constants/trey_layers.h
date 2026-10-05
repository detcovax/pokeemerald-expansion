#ifndef GUARD_CONSTANTS_TREY_LAYERS_H
#define GUARD_CONSTANTS_TREY_LAYERS_H

// TREY: layer link types (TREY_PLAN.md 5.2, E10). #defines only: also read by the assembler.
// A layer link says: "standing inside this rectangle of this map, this move takes you to
// that map, at the matching spot". A map can have many links of the same type.
#define LAYER_LINK_NONE       0
#define LAYER_LINK_SKY_UP     1 // Fly / Soar: surface -> Sky map
#define LAYER_LINK_SKY_DOWN   2 // land from a Sky map -> surface
#define LAYER_LINK_DIG_DOWN   3 // Dig: surface -> Underground layer
#define LAYER_LINK_DIG_UP     4 // Dig: Underground layer -> surface
#define LAYER_LINK_DIVE       5 // Dive: water surface -> underwater
#define LAYER_LINK_EMERGE     6 // Dive: underwater -> water surface
#define LAYER_LINK_TYPES_COUNT 7

#endif // GUARD_CONSTANTS_TREY_LAYERS_H
