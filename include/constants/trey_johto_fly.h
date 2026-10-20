#ifndef GUARD_CONSTANTS_TREY_JOHTO_FLY_H
#define GUARD_CONSTANTS_TREY_JOHTO_FLY_H

// TREY (6a-7): Johto's Fly/Teleport destinations. F(location, map, heal location), names without the
// MAPSEC_/MAP_/HEAL_LOCATION_ prefix. Entering the map sets FLAG_WORLD_MAP_JOHTO_<location> (src/trey_regions.c);
// the Teleport map (src/region_map.c) shows the icon and flies to the heal location.
#define TREY_JOHTO_FLY(F)                                          \
    F(NEW_BARK_TOWN,    NEW_BARK_TOWN,     NEW_BARK_TOWN)          \
    F(CHERRYGROVE_CITY, CHERRYGROVE_CITY,  CHERRYGROVE_CITY)       \
    F(VIOLET_CITY,      VIOLET_CITY,       VIOLET_CITY)            \
    F(AZALEA_TOWN,      AZALEA_TOWN,       AZALEA_TOWN)            \
    F(GOLDENROD_CITY,   GOLDENROD_CITY,    GOLDENROD_CITY)         \
    F(ECRUTEAK_CITY,    ECRUTEAK_CITY,     ECRUTEAK_CITY)          \
    F(OLIVINE_CITY,     OLIVINE_CITY,      OLIVINE_CITY)           \
    F(CIANWOOD_CITY,    CIANWOOD_CITY,     CIANWOOD_CITY)          \
    F(MAHOGANY_TOWN,    MAHOGANY_TOWN,     MAHOGANY_TOWN)          \
    F(BLACKTHORN_CITY,  BLACKTHORN_CITY,   BLACKTHORN_CITY)        \
    F(LAKE_OF_RAGE,     LAKE_OF_RAGE,      LAKE_OF_RAGE)           \
    F(MT_SILVER,        MT_SILVER_OUTSIDE, MT_SILVER)              \
    F(SAFARI_ZONE_GATE, SAFARI_ZONE_GATE,  SAFARI_ZONE_GATE)

#endif // GUARD_CONSTANTS_TREY_JOHTO_FLY_H
