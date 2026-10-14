#ifndef GUARD_CONSTANTS_TREY_REGION_MAPS_H
#define GUARD_CONSTANTS_TREY_REGION_MAPS_H

// TREY (TREY_PLAN.md Phase 4, chunk 4a): region map pages. Every location (MAPSEC) is drawn on one page,
// set by "trey_map" in src/data/region_map/region_map_sections.json. Grids and art: tools/trey/region_maps.py.
// The order here is the L/R switching order on the map screens.
#define TREY_REGION_MAP_KANTO      0
#define TREY_REGION_MAP_SEVII_123  1
#define TREY_REGION_MAP_SEVII_45   2
#define TREY_REGION_MAP_SEVII_67   3
#define TREY_REGION_MAP_ORANGE     4
#define TREY_REGION_MAP_JOHTO      5
#define TREY_REGION_MAP_HOENN      6
#define TREY_REGION_MAP_SINNOH     7
#define TREY_REGION_MAP_KITAKAMI   8
#define TREY_REGION_MAP_COUNT      9

#endif // GUARD_CONSTANTS_TREY_REGION_MAPS_H
