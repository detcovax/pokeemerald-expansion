#ifndef GUARD_TREY_MUSIC_H
#define GUARD_TREY_MUSIC_H

// TREY (6b-3, TREY_PLAN.md D34): regional battle music and day/night map music.

struct MapHeader;

// The region's version of an Emerald battle or victory song (Johto: HGSS, Sinnoh: DPPt); other songs unchanged.
// Kanto keeps upstream's FRLG battle music (GetBattleBGM already picks it there).
u16 TreyMusic_Regional(u16 song);

// A map's music: its "trey_night_music" from evening on, else its normal music.
u16 TreyMusic_MapMusic(const struct MapHeader *header);

#endif // GUARD_TREY_MUSIC_H
