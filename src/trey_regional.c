// TREY: regional variants (TREY_PLAN.md 5.8). See include/trey_regional.h.

#include "global.h"
#include "pokemon.h"
#include "trey_regional.h"
#include "trey_regions.h"
#include "constants/rgb.h"

// ---------------------------------------------------------------------------
// Orange Islands variants
// ---------------------------------------------------------------------------

bool32 TreyOrange_IsActiveHere(void)
{
    if (TREY_DEBUG_ORANGE_EVERYWHERE)
        return TRUE;
    // Sevii maps count as Kanto for gameplay (D16/D21), so they never return REGION_ORANGE.
    return TreyGetCurrentRegion() == REGION_ORANGE;
}

void TreyOrange_ApplyIfInOrangeIslands(struct Pokemon *mon)
{
    u8 isOrange = TRUE;
    if (!TreyOrange_IsActiveHere())
        return;
    SetMonData(mon, MON_DATA_ORANGE_VARIANT, &isOrange);
}

void TreyOrange_CopyBit(struct Pokemon *to, struct BoxPokemon *from)
{
    u8 isOrange = GetBoxMonData(from, MON_DATA_ORANGE_VARIANT, NULL) ? TRUE : FALSE;
    SetMonData(to, MON_DATA_ORANGE_VARIANT, &isOrange);
}

// Ring buffer of tinted palettes. Callers load the result immediately (LoadPalette and friends),
// so a few slots are enough even when a screen loads several Pokémon in a row.
#define TREY_ORANGE_PALETTE_SLOTS 4
static EWRAM_DATA u16 sTreyOrangePalettes[TREY_ORANGE_PALETTE_SLOTS][16] = {0};
static EWRAM_DATA u8 sTreyOrangeNextSlot = 0;

static u16 TintColor(u16 color, u16 target, u32 strength)
{
    s32 r = GET_R(color), g = GET_G(color), b = GET_B(color);
    s32 tr = GET_R(target), tg = GET_G(target), tb = GET_B(target);
    r += ((tr - r) * (s32)strength) / 16;
    g += ((tg - g) * (s32)strength) / 16;
    b += ((tb - b) * (s32)strength) / 16;
    return RGB(r, g, b);
}

static const u16 *TintPalette(const u16 *palette)
{
    u32 i;
    u16 *dest = sTreyOrangePalettes[sTreyOrangeNextSlot];
    sTreyOrangeNextSlot = (sTreyOrangeNextSlot + 1) % TREY_ORANGE_PALETTE_SLOTS;

    dest[0] = palette[0]; // colour 0 is transparent
    for (i = 1; i < 16; i++)
        dest[i] = TintColor(palette[i], TREY_ORANGE_TINT_COLOR, TREY_ORANGE_TINT_STRENGTH);
    return dest;
}

const u16 *TreyOrange_GetMonPalette(struct Pokemon *mon, const u16 *palette)
{
    if (palette == NULL || !GetMonData(mon, MON_DATA_ORANGE_VARIANT, NULL) || GetMonData(mon, MON_DATA_IS_EGG, NULL))
        return palette;
    return TintPalette(palette);
}

const u16 *TreyOrange_GetBoxMonPalette(struct BoxPokemon *boxMon, const u16 *palette)
{
    if (palette == NULL || !GetBoxMonData(boxMon, MON_DATA_ORANGE_VARIANT, NULL) || GetBoxMonData(boxMon, MON_DATA_IS_EGG, NULL))
        return palette;
    return TintPalette(palette);
}
