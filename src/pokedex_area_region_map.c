#include "global.h"
#include "main.h"
#include "menu.h"
#include "bg.h"
#include "malloc.h"
#include "palette.h"
#include "pokedex_area_region_map.h"
#include "region_map.h" // TREY (4a): gTreyRegionMapPage

static EWRAM_DATA u8 *sPokedexAreaMapBgNum = NULL;

// TREY (4a): one area map per region map page (Hoenn is Emerald's). Art: tools/trey/region_maps.py.
static const u16 ALIGNED(4) sPokedexAreaMap_Pal_KANTO[] = INCBIN_U16("graphics/pokedex/region_map_kanto.gbapal");
static const u32 sPokedexAreaMap_Gfx_KANTO[] = INCBIN_U32("graphics/pokedex/region_map_kanto.8bpp.lz");
static const u32 sPokedexAreaMap_Tilemap_KANTO[] = INCBIN_U32("graphics/pokedex/region_map_kanto.bin.lz");
static const u16 ALIGNED(4) sPokedexAreaMap_Pal_SEVII_123[] = INCBIN_U16("graphics/pokedex/region_map_sevii_123.gbapal");
static const u32 sPokedexAreaMap_Gfx_SEVII_123[] = INCBIN_U32("graphics/pokedex/region_map_sevii_123.8bpp.lz");
static const u32 sPokedexAreaMap_Tilemap_SEVII_123[] = INCBIN_U32("graphics/pokedex/region_map_sevii_123.bin.lz");
static const u16 ALIGNED(4) sPokedexAreaMap_Pal_SEVII_45[] = INCBIN_U16("graphics/pokedex/region_map_sevii_45.gbapal");
static const u32 sPokedexAreaMap_Gfx_SEVII_45[] = INCBIN_U32("graphics/pokedex/region_map_sevii_45.8bpp.lz");
static const u32 sPokedexAreaMap_Tilemap_SEVII_45[] = INCBIN_U32("graphics/pokedex/region_map_sevii_45.bin.lz");
static const u16 ALIGNED(4) sPokedexAreaMap_Pal_SEVII_67[] = INCBIN_U16("graphics/pokedex/region_map_sevii_67.gbapal");
static const u32 sPokedexAreaMap_Gfx_SEVII_67[] = INCBIN_U32("graphics/pokedex/region_map_sevii_67.8bpp.lz");
static const u32 sPokedexAreaMap_Tilemap_SEVII_67[] = INCBIN_U32("graphics/pokedex/region_map_sevii_67.bin.lz");
static const u16 ALIGNED(4) sPokedexAreaMap_Pal_ORANGE[] = INCBIN_U16("graphics/pokedex/region_map_orange.gbapal");
static const u32 sPokedexAreaMap_Gfx_ORANGE[] = INCBIN_U32("graphics/pokedex/region_map_orange.8bpp.lz");
static const u32 sPokedexAreaMap_Tilemap_ORANGE[] = INCBIN_U32("graphics/pokedex/region_map_orange.bin.lz");
static const u16 ALIGNED(4) sPokedexAreaMap_Pal_JOHTO[] = INCBIN_U16("graphics/pokedex/region_map_johto.gbapal");
static const u32 sPokedexAreaMap_Gfx_JOHTO[] = INCBIN_U32("graphics/pokedex/region_map_johto.8bpp.lz");
static const u32 sPokedexAreaMap_Tilemap_JOHTO[] = INCBIN_U32("graphics/pokedex/region_map_johto.bin.lz");
static const u16 ALIGNED(4) sPokedexAreaMap_Pal_HOENN[] = INCBIN_U16("graphics/pokedex/region_map.gbapal");
static const u32 sPokedexAreaMap_Gfx_HOENN[] = INCBIN_U32("graphics/pokedex/region_map.8bpp.lz");
static const u32 sPokedexAreaMap_Tilemap_HOENN[] = INCBIN_U32("graphics/pokedex/region_map.bin.lz");
static const u16 ALIGNED(4) sPokedexAreaMap_Pal_SINNOH[] = INCBIN_U16("graphics/pokedex/region_map_sinnoh.gbapal");
static const u32 sPokedexAreaMap_Gfx_SINNOH[] = INCBIN_U32("graphics/pokedex/region_map_sinnoh.8bpp.lz");
static const u32 sPokedexAreaMap_Tilemap_SINNOH[] = INCBIN_U32("graphics/pokedex/region_map_sinnoh.bin.lz");
static const u16 ALIGNED(4) sPokedexAreaMap_Pal_KITAKAMI[] = INCBIN_U16("graphics/pokedex/region_map_kitakami.gbapal");
static const u32 sPokedexAreaMap_Gfx_KITAKAMI[] = INCBIN_U32("graphics/pokedex/region_map_kitakami.8bpp.lz");
static const u32 sPokedexAreaMap_Tilemap_KITAKAMI[] = INCBIN_U32("graphics/pokedex/region_map_kitakami.bin.lz");

static const struct
{
    const u16 *pal;
    u16 palSize;
    const u32 *gfx;
    const u32 *tilemap;
} sPokedexAreaMaps[TREY_REGION_MAP_COUNT] =
{
    [TREY_REGION_MAP_KANTO] = {sPokedexAreaMap_Pal_KANTO, sizeof(sPokedexAreaMap_Pal_KANTO), sPokedexAreaMap_Gfx_KANTO, sPokedexAreaMap_Tilemap_KANTO},
    [TREY_REGION_MAP_SEVII_123] = {sPokedexAreaMap_Pal_SEVII_123, sizeof(sPokedexAreaMap_Pal_SEVII_123), sPokedexAreaMap_Gfx_SEVII_123, sPokedexAreaMap_Tilemap_SEVII_123},
    [TREY_REGION_MAP_SEVII_45] = {sPokedexAreaMap_Pal_SEVII_45, sizeof(sPokedexAreaMap_Pal_SEVII_45), sPokedexAreaMap_Gfx_SEVII_45, sPokedexAreaMap_Tilemap_SEVII_45},
    [TREY_REGION_MAP_SEVII_67] = {sPokedexAreaMap_Pal_SEVII_67, sizeof(sPokedexAreaMap_Pal_SEVII_67), sPokedexAreaMap_Gfx_SEVII_67, sPokedexAreaMap_Tilemap_SEVII_67},
    [TREY_REGION_MAP_ORANGE] = {sPokedexAreaMap_Pal_ORANGE, sizeof(sPokedexAreaMap_Pal_ORANGE), sPokedexAreaMap_Gfx_ORANGE, sPokedexAreaMap_Tilemap_ORANGE},
    [TREY_REGION_MAP_JOHTO] = {sPokedexAreaMap_Pal_JOHTO, sizeof(sPokedexAreaMap_Pal_JOHTO), sPokedexAreaMap_Gfx_JOHTO, sPokedexAreaMap_Tilemap_JOHTO},
    [TREY_REGION_MAP_HOENN] = {sPokedexAreaMap_Pal_HOENN, sizeof(sPokedexAreaMap_Pal_HOENN), sPokedexAreaMap_Gfx_HOENN, sPokedexAreaMap_Tilemap_HOENN},
    [TREY_REGION_MAP_SINNOH] = {sPokedexAreaMap_Pal_SINNOH, sizeof(sPokedexAreaMap_Pal_SINNOH), sPokedexAreaMap_Gfx_SINNOH, sPokedexAreaMap_Tilemap_SINNOH},
    [TREY_REGION_MAP_KITAKAMI] = {sPokedexAreaMap_Pal_KITAKAMI, sizeof(sPokedexAreaMap_Pal_KITAKAMI), sPokedexAreaMap_Gfx_KITAKAMI, sPokedexAreaMap_Tilemap_KITAKAMI},
};

static const u32 sPokedexAreaMapAffine_Gfx[] = INCBIN_U32("graphics/pokedex/region_map_affine.8bpp.lz");
static const u32 sPokedexAreaMapAffine_Tilemap[] = INCBIN_U32("graphics/pokedex/region_map_affine.bin.lz");

void LoadPokedexAreaMapGfx(const struct PokedexAreaMapTemplate *template)
{
    u8 mode;
    void *tilemap;
    sPokedexAreaMapBgNum = Alloc(sizeof(sPokedexAreaMapBgNum));
    mode = template->mode;

    if (mode == 0)
    {
        SetBgAttribute(template->bg, BG_ATTR_METRIC, 0);
        DecompressAndCopyTileDataToVram(template->bg, sPokedexAreaMaps[gTreyRegionMapPage].gfx, 0, template->offset, 0);
        tilemap = DecompressAndCopyTileDataToVram(template->bg, sPokedexAreaMaps[gTreyRegionMapPage].tilemap, 0, 0, 1);
        AddValToTilemapBuffer(tilemap, template->offset, 32, 32, FALSE); // template->offset is always 0, so this does nothing.
    }
    else
    {
        // This is never reached, only a mode of 0 is given
        SetBgAttribute(template->bg, BG_ATTR_METRIC, 2);
        SetBgAttribute(template->bg, BG_ATTR_TYPE, BG_TYPE_AFFINE); // This does nothing. BG_ATTR_TYPE can't be set with this function
        DecompressAndCopyTileDataToVram(template->bg, sPokedexAreaMapAffine_Gfx, 0, template->offset, 0);
        tilemap = DecompressAndCopyTileDataToVram(template->bg, sPokedexAreaMapAffine_Tilemap, 0, 0, 1);
        AddValToTilemapBuffer(tilemap, template->offset, 64, 64, TRUE); // template->offset is always 0, so this does nothing.
    }

    ChangeBgX(template->bg, 0, BG_COORD_SET);
    ChangeBgY(template->bg, 0, BG_COORD_SET);
    SetBgAttribute(template->bg, BG_ATTR_PALETTEMODE, 1);
    CpuCopy16(sPokedexAreaMaps[gTreyRegionMapPage].pal, &gPlttBufferUnfaded[BG_PLTT_ID(7)], sPokedexAreaMaps[gTreyRegionMapPage].palSize); // TREY (4a)
    *sPokedexAreaMapBgNum = template->bg;
}

bool32 TryShowPokedexAreaMap(void)
{
    if (!FreeTempTileDataBuffersIfPossible())
    {
        ShowBg(*sPokedexAreaMapBgNum);
        return FALSE;
    }
    else
    {
        return TRUE;
    }
}

void FreePokedexAreaMapBgNum(void)
{
    TRY_FREE_AND_SET_NULL(sPokedexAreaMapBgNum);
}

void PokedexAreaMapChangeBgY(u32 move)
{
    ChangeBgY(*sPokedexAreaMapBgNum, move * 0x100, BG_COORD_SET);
}
