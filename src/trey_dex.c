// TREY (TREY_PLAN.md E13, Phase 4 chunk 4d): regional Pokédexes, professor unlocks, discovery numbers.
//
// Discovery numbers (David, 2026-10-16): no canon dex numbers anywhere. Every Pokémon gets the next number
// the first time the player SEES it, and every Pokédex list is ordered and numbered that way. A regional
// dex is the same list filtered to that region's canon members (docs/trey/dex/*.txt).
// The order is stored as 10-bit National numbers at the end of the PC storage block.

#include "global.h"
#include "event_data.h"
#include "pokedex.h"
#include "pokemon.h"
#include "pokemon_storage_system.h"
#include "script.h"
#include "trey_dex.h"
#include "trey_regions.h"
#include "constants/flags.h"
#include "constants/vars.h"

#include "data/trey/dex_regions.h"

STATIC_ASSERT(TREY_DEX_COUNT <= 8, TreyDexMaskIsU8);
STATIC_ASSERT(TREY_FLAG_DEX_UNLOCK_START + TREY_DEX_COUNT - 1 <= TREY_FLAG_DEX_UNLOCK_END, TreyDexUnlockFlags);
STATIC_ASSERT(TREY_FLAG_REGION_ARRIVED_START + TREY_DEX_COUNT - 1 <= TREY_FLAG_REGION_ARRIVED_END, TreyDexArrivalFlags);
STATIC_ASSERT(TREY_FLAG_NEXT_FREE - 1 <= TREY_FLAGS_END, TreyDexFlagsOutOfRange);

#define ENTRY_BITS 10
#define ENTRY_MASK ((1 << ENTRY_BITS) - 1)

static const u8 sText_National[] = _("NATIONAL");
static const u8 sText_Kanto[]    = _("KANTO");
static const u8 sText_Orange[]   = _("ORANGE");
static const u8 sText_Johto[]    = _("JOHTO");
static const u8 sText_Hoenn[]    = _("HOENN");
static const u8 sText_Sinnoh[]   = _("SINNOH");
static const u8 sText_Kitakami[] = _("KITAKAMI");

static const u8 *const sDexNames[TREY_DEX_COUNT] =
{
    [TREY_DEX_NATIONAL] = sText_National,
    [TREY_DEX_KANTO]    = sText_Kanto,
    [TREY_DEX_ORANGE]   = sText_Orange,
    [TREY_DEX_JOHTO]    = sText_Johto,
    [TREY_DEX_HOENN]    = sText_Hoenn,
    [TREY_DEX_SINNOH]   = sText_Sinnoh,
    [TREY_DEX_KITAKAMI] = sText_Kitakami,
};

// First arrival in a region (the professor event). NULL = nothing to run yet: each region's
// story fills this in when its maps are built (Phase 5/6). The arrival flag is set either way.
static const u8 *const sArrivalScripts[TREY_DEX_COUNT] =
{
    [TREY_DEX_NATIONAL] = NULL,
    [TREY_DEX_KANTO]    = NULL,
    [TREY_DEX_ORANGE]   = NULL,
    [TREY_DEX_JOHTO]    = NULL,
    [TREY_DEX_HOENN]    = NULL,
    [TREY_DEX_SINNOH]   = NULL,
    [TREY_DEX_KITAKAMI] = NULL,
};

// ---------------------------------------------------------------------------
// Discovery order
// ---------------------------------------------------------------------------

static u16 ReadEntry(u32 index)
{
    const u8 *data = gPokemonStoragePtr->treyDexOrder;
    u32 bit = index * ENTRY_BITS;
    u32 byte = bit / 8;
    u32 value = data[byte] | (data[byte + 1] << 8);
    return (value >> (bit % 8)) & ENTRY_MASK;
}

static void WriteEntry(u32 index, u16 natDex)
{
    u8 *data = gPokemonStoragePtr->treyDexOrder;
    u32 bit = index * ENTRY_BITS;
    u32 byte = bit / 8;
    u32 shift = bit % 8;
    u32 value = data[byte] | (data[byte + 1] << 8);
    value = (value & ~(ENTRY_MASK << shift)) | ((natDex & ENTRY_MASK) << shift);
    data[byte] = value & 0xFF;
    data[byte + 1] = value >> 8;
}

void TreyDex_ResetDiscovery(void)
{
    memset(gPokemonStoragePtr->treyDexOrder, 0, sizeof(gPokemonStoragePtr->treyDexOrder));
}

u32 TreyDex_GetDiscoveryCount(void)
{
    u32 i;
    for (i = 0; i < TREY_DEX_ORDER_MAX; i++)
    {
        if (ReadEntry(i) == 0)
            break;
    }
    return i;
}

u16 TreyDex_GetDiscoveryAt(u32 index)
{
    if (index >= TREY_DEX_ORDER_MAX)
        return 0;
    return ReadEntry(index);
}

u16 TreyDex_GetDiscoveryNumber(u16 natDex)
{
    u32 i;
    if (natDex == 0 || natDex > ENTRY_MASK)
        return 0;
    for (i = 0; i < TREY_DEX_ORDER_MAX; i++)
    {
        u16 entry = ReadEntry(i);
        if (entry == natDex)
            return i + 1;
        if (entry == 0)
            break;
    }
    return 0;
}

static bool32 CanList(u16 natDex)
{
    // Only Pokémon in the game's roster (disabled families have no species).
    return natDex != 0 && natDex <= ENTRY_MASK && natDex <= NATIONAL_DEX_COUNT
        && NationalPokedexNumToSpecies(natDex) != SPECIES_NONE;
}

void TreyDex_OnFirstSeen(u16 natDex)
{
    u32 i;
    if (!CanList(natDex))
        return;
    for (i = 0; i < TREY_DEX_ORDER_MAX; i++)
    {
        u16 entry = ReadEntry(i);
        if (entry == natDex)
            return; // already listed
        if (entry == 0)
        {
            WriteEntry(i, natDex);
            return;
        }
    }
    // full: cannot happen in the game, tools/trey/dex_lists.py checks the roster fits TREY_DEX_ORDER_MAX
}

void TreyDex_Repair(void)
{
    u8 listed[(NATIONAL_DEX_COUNT + 8) / 8];
    u32 i, count;

    memset(listed, 0, sizeof(listed));
    for (count = 0; count < TREY_DEX_ORDER_MAX; count++)
    {
        u16 entry = ReadEntry(count);
        if (entry == 0)
            break;
        if (entry <= NATIONAL_DEX_COUNT)
            listed[entry / 8] |= 1 << (entry % 8);
    }
    for (i = 1; i <= NATIONAL_DEX_COUNT && count < TREY_DEX_ORDER_MAX; i++)
    {
        if (!(listed[i / 8] & (1 << (i % 8))) && GetSetPokedexFlag(i, FLAG_GET_SEEN) && CanList(i))
            WriteEntry(count++, i);
    }
}

// ---------------------------------------------------------------------------
// Regional dexes
// ---------------------------------------------------------------------------

bool32 TreyDex_IsInDex(u32 dex, u16 natDex)
{
    if (natDex == 0 || natDex > NATIONAL_DEX_COUNT)
        return FALSE;
    if (dex == TREY_DEX_NATIONAL)
        return TRUE;
    if (dex >= TREY_DEX_COUNT)
        return FALSE;
    return (gTreyDexRegionMask[natDex] & TREY_DEX_BIT(dex)) != 0;
}

bool32 TreyDex_IsUnlocked(u32 dex)
{
    if (dex == TREY_DEX_NATIONAL)
        return TRUE;
    if (dex >= TREY_DEX_COUNT)
        return FALSE;
    return FlagGet(TREY_FLAG_DEX_UNLOCK_START + dex);
}

void TreyDex_Unlock(u32 dex)
{
    if (dex != TREY_DEX_NATIONAL && dex < TREY_DEX_COUNT)
        FlagSet(TREY_FLAG_DEX_UNLOCK_START + dex);
}

void TreyDex_UnlockFromVar(void)
{
    TreyDex_Unlock(gSpecialVar_0x8004);
}

u32 TreyDex_GetDexOfRegion(enum Region region)
{
    switch (region)
    {
    case REGION_KANTO:    return TREY_DEX_KANTO; // Sevii counts as Kanto (D16)
    case REGION_ORANGE:   return TREY_DEX_ORANGE;
    case REGION_JOHTO:    return TREY_DEX_JOHTO;
    case REGION_HOENN:    return TREY_DEX_HOENN;
    case REGION_SINNOH:   return TREY_DEX_SINNOH;
    case REGION_KITAKAMI: return TREY_DEX_KITAKAMI;
    default:              return TREY_DEX_NATIONAL;
    }
}

u32 TreyDex_GetCurrentRegionDex(void)
{
    return TreyDex_GetDexOfRegion(TreyGetCurrentRegion());
}

const u8 *TreyDex_GetName(u32 dex)
{
    if (dex >= TREY_DEX_COUNT)
        dex = TREY_DEX_NATIONAL;
    return sDexNames[dex];
}

static u32 CountFlag(u32 dex, u8 caseId)
{
    u32 i, count = 0;
    for (i = 1; i <= NATIONAL_DEX_COUNT; i++)
    {
        if (TreyDex_IsInDex(dex, i) && GetSetPokedexFlag(i, caseId))
            count++;
    }
    return count;
}

u32 TreyDex_CountSeen(u32 dex)
{
    return CountFlag(dex, FLAG_GET_SEEN);
}

u32 TreyDex_CountCaught(u32 dex)
{
    return CountFlag(dex, FLAG_GET_CAUGHT);
}

// ---------------------------------------------------------------------------
// Game hooks
// ---------------------------------------------------------------------------

void TreyDex_InitNewGame(void)
{
    u32 dex;

    TreyDex_ResetDiscovery();
    EnableNationalPokedex(); // the National dex is there from the start (David, 2026-10-16)
    VarSet(VAR_TREY_DEX_LAST, TREY_DEX_NATIONAL);
    VarSet(VAR_TREY_REGION_ARRIVAL, 0);
    if (TREY_DEBUG_ALL_DEXES)
    {
        for (dex = 0; dex < TREY_DEX_COUNT; dex++)
            TreyDex_Unlock(dex);
    }
}

void TreyDex_OnMapEnter(void)
{
    u32 dex = TreyDex_GetCurrentRegionDex();

    if (dex == TREY_DEX_NATIONAL || FlagGet(TREY_FLAG_REGION_ARRIVED_START + dex))
        return;
    FlagSet(TREY_FLAG_REGION_ARRIVED_START + dex);
    if (sArrivalScripts[dex] != NULL)
        VarSet(VAR_TREY_REGION_ARRIVAL, dex + 1);
}

bool32 TreyDex_TryRunArrivalScript(void)
{
    u32 pending = VarGet(VAR_TREY_REGION_ARRIVAL);

    if (pending == 0)
        return FALSE;
    VarSet(VAR_TREY_REGION_ARRIVAL, 0);
    if (pending > TREY_DEX_COUNT || sArrivalScripts[pending - 1] == NULL)
        return FALSE;
    ScriptContext_SetupScript(sArrivalScripts[pending - 1]);
    return TRUE;
}
