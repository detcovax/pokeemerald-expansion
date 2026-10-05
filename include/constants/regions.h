#ifndef GUARD_CONSTANTS_REGIONS_H
#define GUARD_CONSTANTS_REGIONS_H

// Core-series regions
enum Region
{
    REGION_NONE,
    REGION_KANTO,
    REGION_JOHTO,
    REGION_HOENN,
    REGION_SINNOH,
    REGION_UNOVA,
    REGION_KALOS,
    REGION_ALOLA,
    REGION_GALAR,
    REGION_HISUI,
    REGION_PALDEA,
    REGION_ORANGE,   // TREY (TREY_PLAN.md E7): Orange Islands. Sevii maps count as Kanto for gameplay; they only sit on the Orange region MAP (D16).
    REGION_KITAKAMI, // TREY
    REGIONS_COUNT,
};

#endif  // GUARD_CONSTANTS_REGIONS_H
