#ifndef GUARD_TREY_REGIONS_H
#define GUARD_TREY_REGIONS_H

// TREY: regions and badges (TREY_PLAN.md E6, E7, 5.9).

#include "constants/regions.h"

#define TREY_MAX_BADGES_PER_REGION 8

// Region a location belongs to, for gameplay (badges, leagues, regional forms).
// Which region MAP a location is drawn on is a separate question, handled in Phase 4.
enum Region TreyGetRegionOfMapsec(u16 mapSec);
enum Region TreyGetCurrentRegion(void);

// Badges. Regions without a league (Kitakami, none) have 0 badges.
u32 TreyBadges_GetCount(enum Region region);                 // how many badges the region has
u16 TreyBadges_GetFlag(enum Region region, u32 badgeIndex);  // flag for one badge, or 0 if out of range
bool32 TreyBadges_Has(enum Region region, u32 badgeIndex);
u32 TreyBadges_CountOwned(enum Region region);
u32 TreyBadges_CountOwnedTotal(void);

#endif // GUARD_TREY_REGIONS_H
