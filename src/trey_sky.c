// TREY: sky layer extras (TREY_PLAN.md 5.2, phase 3e). See include/trey_sky.h.

#include "global.h"
#include "event_object_movement.h"
#include "field_player_avatar.h"
#include "field_weather.h"
#include "fieldmap.h"
#include "metatile_behavior.h"
#include "overworld.h"
#include "palette.h"
#include "sprite.h"
#include "tilesets.h"
#include "trey_sky.h"
#include "constants/weather.h"

// ---------------------------------------------------------------------------
// Storm palettes: in rain, thunderstorms and downpours the clouds turn dark and the sky, storm walls
// and mountains tint darker. Swapped live, so a weather change on the map is picked up too.
// ---------------------------------------------------------------------------
#define SKY_FIRST_PAL 6
#define SKY_NUM_PALS  4

static const u16 sStormPalettes[SKY_NUM_PALS][16] =
{
    INCBIN_U16("data/tilesets/secondary/trey_sky/palettes/storm/06.gbapal"),
    INCBIN_U16("data/tilesets/secondary/trey_sky/palettes/storm/07.gbapal"),
    INCBIN_U16("data/tilesets/secondary/trey_sky/palettes/storm/08.gbapal"),
    INCBIN_U16("data/tilesets/secondary/trey_sky/palettes/storm/09.gbapal"),
};

static EWRAM_DATA s8 sStormShown = -1;

bool32 TreySky_IsStormWeather(void)
{
    u32 weather = GetCurrentWeather();
    return weather == WEATHER_RAIN || weather == WEATHER_RAIN_THUNDERSTORM || weather == WEATHER_DOWNPOUR;
}

void TreySky_ResetPalettes(void)
{
    sStormShown = -1;
}

void TreySky_UpdatePalettes(void)
{
    s8 storm = TreySky_IsStormWeather();
    const u16 *src;

    if (storm == sStormShown)
        return;
    src = storm ? sStormPalettes[0] : gTileset_TreySky.palettes[SKY_FIRST_PAL];
    // The unfaded buffer is what fades and weather work from; refresh the visible colours if nothing is fading.
    CpuCopy16(src, &gPlttBufferUnfaded[BG_PLTT_ID(SKY_FIRST_PAL)], SKY_NUM_PALS * PLTT_SIZE_4BPP);
    if (!gPaletteFade.active)
        TreyWeather_RefreshPalettes(SKY_FIRST_PAL, SKY_NUM_PALS);
    sStormShown = storm;
}

// ---------------------------------------------------------------------------
// Cloud puff: flying onto a cloud makes it swell and break into little puffs, drawn over the player.
// ---------------------------------------------------------------------------
#define TAG_TREY_CLOUD_PUFF 0x1C30
#define PUFF_FRAME_SIZE     (32 * 32 / 2)

static const u8 sCloudPuffGfx[] = INCBIN_U8("graphics/field_effects/pics/trey_cloud_puff.4bpp");
static const u16 sCloudPuffPal[] = INCBIN_U16("graphics/field_effects/palettes/trey_cloud_puff.gbapal");
static const u16 sCloudPuffStormPal[] = INCBIN_U16("graphics/field_effects/palettes/trey_cloud_puff_storm.gbapal");

static const struct SpriteFrameImage sCloudPuffImages[] =
{
    {sCloudPuffGfx + PUFF_FRAME_SIZE * 0, PUFF_FRAME_SIZE},
    {sCloudPuffGfx + PUFF_FRAME_SIZE * 1, PUFF_FRAME_SIZE},
    {sCloudPuffGfx + PUFF_FRAME_SIZE * 2, PUFF_FRAME_SIZE},
    {sCloudPuffGfx + PUFF_FRAME_SIZE * 3, PUFF_FRAME_SIZE},
    {sCloudPuffGfx + PUFF_FRAME_SIZE * 4, PUFF_FRAME_SIZE},
    {sCloudPuffGfx + PUFF_FRAME_SIZE * 5, PUFF_FRAME_SIZE},
};

static const union AnimCmd sCloudPuffAnim[] =
{
    ANIMCMD_FRAME(0, 3),
    ANIMCMD_FRAME(1, 4),
    ANIMCMD_FRAME(2, 4),
    ANIMCMD_FRAME(3, 4),
    ANIMCMD_FRAME(4, 4),
    ANIMCMD_FRAME(5, 5),
    ANIMCMD_END,
};

static const union AnimCmd *const sCloudPuffAnims[] = {sCloudPuffAnim};

static const struct OamData sCloudPuffOam =
{
    .shape = SPRITE_SHAPE(32x32),
    .size = SPRITE_SIZE(32x32),
    .priority = 1,
};

static void SpriteCB_CloudPuff(struct Sprite *sprite);

static const struct SpriteTemplate sCloudPuffTemplate =
{
    .tileTag = TAG_NONE,
    .paletteTag = TAG_TREY_CLOUD_PUFF,
    .oam = &sCloudPuffOam,
    .anims = sCloudPuffAnims,
    .images = sCloudPuffImages,
    .affineAnims = gDummySpriteAffineAnimTable,
    .callback = SpriteCB_CloudPuff,
};

static void SpriteCB_CloudPuff(struct Sprite *sprite)
{
    struct Sprite *player = &gSprites[gPlayerAvatar.spriteId];

    // Stay just above the player in draw order.
    sprite->oam.priority = player->oam.priority;
    sprite->subpriority = player->subpriority > 0 ? player->subpriority - 1 : 0;
    if (sprite->animEnded)
    {
        DestroySprite(sprite);
        if (IndexOfSpritePaletteTag(TAG_TREY_CLOUD_PUFF) != 0xFF)
        {
            u32 i;
            for (i = 0; i < MAX_SPRITES; i++)
            {
                if (gSprites[i].inUse && gSprites[i].template == &sCloudPuffTemplate)
                    return;
            }
            FreeSpritePaletteByTag(TAG_TREY_CLOUD_PUFF);
        }
    }
}

void TreySky_OnObjectBeginStep(struct ObjectEvent *objEvent)
{
    s16 x, y;
    u8 spriteId, palSlot;

    if (!objEvent->isPlayer || !TestPlayerAvatarFlags(PLAYER_AVATAR_FLAG_SOARING))
        return;
    if (!MetatileBehavior_IsSkyCloud(objEvent->currentMetatileBehavior))
        return;

    palSlot = IndexOfSpritePaletteTag(TAG_TREY_CLOUD_PUFF);
    if (palSlot == 0xFF)
    {
        struct SpritePalette pal = {sCloudPuffPal, TAG_TREY_CLOUD_PUFF};
        palSlot = LoadSpritePalette(&pal);
        if (palSlot == 0xFF)
            return;
    }
    // Storm or clear colours, then the day/night tint.
    LoadPalette(TreySky_IsStormWeather() ? sCloudPuffStormPal : sCloudPuffPal, OBJ_PLTT_ID(palSlot), PLTT_SIZE_4BPP);
    UpdateSpritePaletteWithTime(palSlot);

    x = objEvent->currentCoords.x;
    y = objEvent->currentCoords.y;
    SetSpritePosToOffsetMapCoords(&x, &y, 8, 6);
    spriteId = CreateSprite(&sCloudPuffTemplate, x, y, 0);
    if (spriteId != MAX_SPRITES)
    {
        gSprites[spriteId].coordOffsetEnabled = TRUE;
        SpriteCB_CloudPuff(&gSprites[spriteId]);
    }
}
