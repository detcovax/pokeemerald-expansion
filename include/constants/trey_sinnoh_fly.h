#ifndef GUARD_CONSTANTS_TREY_SINNOH_FLY_H
#define GUARD_CONSTANTS_TREY_SINNOH_FLY_H

// TREY (6b-6): Sinnoh's Fly/Teleport destinations (DPPt's Fly list). F(location, map, heal location), names without
// the MAPSEC_/MAP_/HEAL_LOCATION_ prefix. Entering the map sets FLAG_WORLD_MAP_SINNOH_<location> (src/trey_regions.c);
// the Teleport map (src/region_map.c) shows the icon on the Sinnoh page and flies to the heal location.
// Flags live in their own 64-slot block (TREY_FLAG_WORLD_MAP_SINNOH_START): the first world map block is full.
#define TREY_SINNOH_FLY(F)                                                   \
    F(TWINLEAF_TOWN,         TWINLEAF_TOWN,         TWINLEAF_TOWN)           \
    F(SANDGEM_TOWN,          SANDGEM_TOWN,          SANDGEM_TOWN)            \
    F(JUBILIFE_CITY,         JUBILIFE_CITY,         JUBILIFE_CITY)           \
    F(OREBURGH_CITY,         OREBURGH_CITY,         OREBURGH_CITY)           \
    F(FLOAROMA_TOWN,         FLOAROMA_TOWN,         FLOAROMA_TOWN)           \
    F(ETERNA_CITY,           ETERNA_CITY,           ETERNA_CITY)             \
    F(HEARTHOME_CITY,        HEARTHOME_CITY,        HEARTHOME_CITY)          \
    F(SOLACEON_TOWN,         SOLACEON_TOWN,         SOLACEON_TOWN)           \
    F(CELESTIC_TOWN,         CELESTIC_TOWN,         CELESTIC_TOWN)           \
    F(SNOWPOINT_CITY,        SNOWPOINT_CITY,        SNOWPOINT_CITY)          \
    F(CANALAVE_CITY,         CANALAVE_CITY,         CANALAVE_CITY)           \
    F(VEILSTONE_CITY,        VEILSTONE_CITY,        VEILSTONE_CITY)          \
    F(PASTORIA_CITY,         PASTORIA_CITY,         PASTORIA_CITY)           \
    F(SUNYSHORE_CITY,        SUNYSHORE_CITY,        SUNYSHORE_CITY)          \
    F(SINNOH_POKEMON_LEAGUE, SINNOH_POKEMON_LEAGUE, SINNOH_POKEMON_LEAGUE)   \
    F(FIGHT_AREA,            FIGHT_AREA,            FIGHT_AREA)              \
    F(SURVIVAL_AREA,         SURVIVAL_AREA,         SURVIVAL_AREA)           \
    F(RESORT_AREA,           RESORT_AREA,           RESORT_AREA)

#endif // GUARD_CONSTANTS_TREY_SINNOH_FLY_H
