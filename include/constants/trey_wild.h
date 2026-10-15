#ifndef GUARD_CONSTANTS_TREY_WILD_H
#define GUARD_CONSTANTS_TREY_WILD_H

// TREY (TREY_PLAN.md 5.11, D22; Phase 4 chunk 4b-2): wild encounters by season, time of day and weather.
// Weather groups (the current weather decides):
#define TREY_WEATHER_CLEAR      0 // none, sunny, sunny clouds, shade, volcanic ash, underwater, others
#define TREY_WEATHER_RAIN       1 // rain, thunderstorm, downpour
#define TREY_WEATHER_SNOW       2
#define TREY_WEATHER_SANDSTORM  3
#define TREY_WEATHER_FOG        4 // horizontal and diagonal fog
#define TREY_WEATHER_SUN        5 // harsh sun (drought)
#define TREY_WEATHER_GROUPS_COUNT 6

// Header IDs above this are maps that only have TREY (CSV) encounters.
#define TREY_WILD_HEADER_BASE   0x8000

#endif // GUARD_CONSTANTS_TREY_WILD_H
