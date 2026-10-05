#ifndef GUARD_REGIONS_H
#define GUARD_REGIONS_H

#include "constants/regions.h"
#include "trey_regions.h" // TREY

static inline u32 GetCurrentRegion(void)
{
    // TREY: the region now comes from the current map's MAPSEC (src/trey_regions.c).
    // How regions map to regional FORMS (e.g. Hisuian forms in Sinnoh) is decided in Phase 2.
    return TreyGetCurrentRegion();
}

#endif // GUARD_REGIONS_H
