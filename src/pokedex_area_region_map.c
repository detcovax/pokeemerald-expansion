#include "global.h"
#include "main.h"
#include "menu.h"
#include "bg.h"
#include "malloc.h"
#include "palette.h"
#include "pokedex_area_region_map.h"
#include "region_map.h" // TREY (4a): gTreyRegionMapPage, gRegionMapInfos

static EWRAM_DATA u8 *sPokedexAreaMapBgNum = NULL;

// TREY (4a): one area map per region map page. Kanto, Sevii and Hoenn use upstream's art (gRegionMapInfos,
// FRLG-style Kanto, D25); Orange, Johto, Sinnoh and Kitakami use TREY art (tools/trey/region_maps.py).
static const u16 ALIGNED(4) sPokedexAreaMap_Pal_ORANGE[] = INCBIN_U16("graphics/pokedex/region_map_orange.gbapal");
static const u32 sPokedexAreaMap_Gfx_ORANGE[] = INCBIN_U32("graphics/pokedex/region_map_orange.8bpp.lz");
static const u32 sPokedexAreaMap_Tilemap_ORANGE[] = INCBIN_U32("graphics/pokedex/region_map_orange.bin.lz");
static const u16 ALIGNED(4) sPokedexAreaMap_Pal_JOHTO[] = INCBIN_U16("graphics/pokedex/region_map_johto.gbapal");
static const u32 sPokedexAreaMap_Gfx_JOHTO[] = INCBIN_U32("graphics/pokedex/region_map_johto.8bpp.lz");
static const u32 sPokedexAreaMap_Tilemap_JOHTO[] = INCBIN_U32("graphics/pokedex/region_map_johto.bin.lz");
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
    [TREY_REGION_MAP_ORANGE] = {sPokedexAreaMap_Pal_ORANGE, sizeof(sPokedexAreaMap_Pal_ORANGE), sPokedexAreaMap_Gfx_ORANGE, sPokedexAreaMap_Tilemap_ORANGE},
    [TREY_REGION_MAP_JOHTO] = {sPokedexAreaMap_Pal_JOHTO, sizeof(sPokedexAreaMap_Pal_JOHTO), sPokedexAreaMap_Gfx_JOHTO, sPokedexAreaMap_Tilemap_JOHTO},
    [TREY_REGION_MAP_SINNOH] = {sPokedexAreaMap_Pal_SINNOH, sizeof(sPokedexAreaMap_Pal_SINNOH), sPokedexAreaMap_Gfx_SINNOH, sPokedexAreaMap_Tilemap_SINNOH},
    [TREY_REGION_MAP_KITAKAMI] = {sPokedexAreaMap_Pal_KITAKAMI, sizeof(sPokedexAreaMap_Pal_KITAKAMI), sPokedexAreaMap_Gfx_KITAKAMI, sPokedexAreaMap_Tilemap_KITAKAMI},
};

struct TreyAreaMapGfx
{
    const u16 *pal;
    u16 palSize;
    const u32 *gfx;
    const u32 *tilemap;
};

static struct TreyAreaMapGfx GetAreaMapGfx(u32 page)
{
    struct TreyAreaMapGfx g;
    s32 type = -1;

    switch (page)
    {
    case TREY_REGION_MAP_KANTO:     type = REGION_MAP_KANTO; break;
    case TREY_REGION_MAP_SEVII_123: type = REGION_MAP_SEVII123; break;
    case TREY_REGION_MAP_SEVII_45:  type = REGION_MAP_SEVII45; break;
    case TREY_REGION_MAP_SEVII_67:  type = REGION_MAP_SEVII67; break;
    case TREY_REGION_MAP_HOENN:     type = REGION_MAP_HOENN; break;
    }
    if (type >= 0)
    {
        g.pal = gRegionMapInfos[type].dexMapPalette;
        g.palSize = gRegionMapInfos[type].dexMapPaletteSize;
        g.gfx = gRegionMapInfos[type].dexMapGfx;
        g.tilemap = gRegionMapInfos[type].dexMapTilemap;
    }
    else
    {
        g.pal = sPokedexAreaMaps[page].pal;
        g.palSize = sPokedexAreaMaps[page].palSize;
        g.gfx = sPokedexAreaMaps[page].gfx;
        g.tilemap = sPokedexAreaMaps[page].tilemap;
    }
    return g;
}

static const u32 sPokedexAreaMapAffine_Gfx[] = INCBIN_U32("graphics/pokedex/region_map_affine.8bpp.lz");
static const u32 sPokedexAreaMapAffine_Tilemap[] = INCBIN_U32("graphics/pokedex/region_map_affine.bin.lz");

void LoadPokedexAreaMapGfx(const struct PokedexAreaMapTemplate *template)
{
    u8 mode;
    void *tilemap;
    struct TreyAreaMapGfx page = GetAreaMapGfx(gTreyRegionMapPage); // TREY (4a)
    sPokedexAreaMapBgNum = Alloc(sizeof(sPokedexAreaMapBgNum));
    mode = template->mode;

    if (mode == 0)
    {
        SetBgAttribute(template->bg, BG_ATTR_METRIC, 0);
        DecompressAndCopyTileDataToVram(template->bg, page.gfx, 0, template->offset, 0);
        tilemap = DecompressAndCopyTileDataToVram(template->bg, page.tilemap, 0, 0, 1);
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
    CpuCopy16(page.pal, &gPlttBufferUnfaded[BG_PLTT_ID(7)], page.palSize); // TREY (4a)
    // TREY (4a): switching region redraws the area page without a fade, so update the visible colours too
    // (otherwise the previous region's palette stays on screen).
    CpuCopy16(page.pal, &gPlttBufferFaded[BG_PLTT_ID(7)], page.palSize);
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
