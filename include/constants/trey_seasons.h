#ifndef GUARD_CONSTANTS_TREY_SEASONS_H
#define GUARD_CONSTANTS_TREY_SEASONS_H

// TREY: seasons, Gen 5 rules (TREY_PLAN.md 5.5, D6). #defines only: also read by the assembler.
// Season = (calendar month - 1) % 4: Jan/May/Sep Spring, Feb/Jun/Oct Summer,
// Mar/Jul/Nov Autumn, Apr/Aug/Dec Winter. The season logic itself arrives in Phase 4.
#define SEASON_SPRING       0
#define SEASON_SUMMER       1
#define SEASON_AUTUMN       2
#define SEASON_WINTER       3
#define TREY_SEASONS_COUNT  4

#endif // GUARD_CONSTANTS_TREY_SEASONS_H
