#ifndef GUARD_TREY_SKY_H
#define GUARD_TREY_SKY_H

// TREY: sky layer extras (TREY_PLAN.md 5.2, phase 3e): storm palettes for the sky tileset and the cloud
// puff when the player flies onto a cloud. Art: tools/trey/sky_art.py.

bool32 TreySky_IsStormWeather(void);
void TreySky_ResetPalettes(void);    // call when the sky tileset is loaded
void TreySky_UpdatePalettes(void);   // call every frame while the sky tileset is in use
void TreySky_OnObjectBeginStep(struct ObjectEvent *objEvent);
void TreySky_StartGustBurst(struct ObjectEvent *puff, u8 direction); // 3g: wind blowing into a pushed storm puff
void TreySky_CheckWhirlwindPath(void);  // special (3g)
void TreySky_StartWhirlwindRide(void);  // special (3g), use with waitstate

#endif // GUARD_TREY_SKY_H
