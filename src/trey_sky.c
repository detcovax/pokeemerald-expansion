// TREY: sky layer extras (TREY_PLAN.md 5.2, phase 3e). See include/trey_sky.h.

#include "global.h"
#include "graphics.h"
#include "event_data.h"
#include "event_object_movement.h"
#include "field_player_avatar.h"
#include "field_weather.h"
#include "fieldmap.h"
#include "metatile_behavior.h"
#include "overworld.h"
#include "palette.h"
#include "script.h"
#include "sound.h"
#include "sprite.h"
#include "task.h"
#include "tilesets.h"
#include "trey_sky.h"
#include "constants/event_object_movement.h"
#include "constants/event_objects.h"
#include "constants/songs.h"
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

static EWRAM_DATA s8 sStormShown = 0;

bool32 TreySky_IsStormWeather(void)
{
    u32 weather = GetCurrentWeather();
    return weather == WEATHER_RAIN || weather == WEATHER_RAIN_THUNDERSTORM || weather == WEATHER_DOWNPOUR;
}

void TreySky_ResetPalettes(void)
{
    sStormShown = -1;
}

// 3f: storm puffs (Gust) darken a little in storms too. Their palette can be loaded at any time
// (map load, return from battle), so it is checked every frame by one colour.
static void TreySky_UpdateStormPuffPalette(bool32 storm)
{
    u32 slot = IndexOfSpritePaletteTag(OBJ_EVENT_PAL_TAG_TREY_STORM_PUFF);
    const u16 *src = storm ? gObjectEventPal_TreyStormPuffStorm : gObjectEventPal_TreyStormPuff;

    if (slot == 0xFF || gPlttBufferUnfaded[OBJ_PLTT_ID(slot) + 1] == src[1])
        return;
    CpuCopy16(src, &gPlttBufferUnfaded[OBJ_PLTT_ID(slot)], PLTT_SIZE_4BPP);
    if (!gPaletteFade.active)
        TreyWeather_RefreshPalettes(16 + slot, 1);
}

void TreySky_UpdatePalettes(void)
{
    s8 storm = TreySky_IsStormWeather();
    const u16 *src;

    TreySky_UpdateStormPuffPalette(storm);
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

// ---------------------------------------------------------------------------
// 3g: Gust air burst. Wind streaks blow from the player into the storm puff being pushed, drawn just
// behind the puff, straddling the edge between the player and the puff.
// ---------------------------------------------------------------------------
#define TAG_TREY_GUST_BURST 0x1C31
#define GUST_FRAME_SIZE     (16 * 16 / 2)
#define GUST_FRAMES         5

static const u8 sGustBurstGfx[] = INCBIN_U8("graphics/field_effects/pics/trey_gust_burst.4bpp");

static const struct SpriteFrameImage sGustBurstImages[] =
{
    {sGustBurstGfx + GUST_FRAME_SIZE * 0, GUST_FRAME_SIZE},
    {sGustBurstGfx + GUST_FRAME_SIZE * 1, GUST_FRAME_SIZE},
    {sGustBurstGfx + GUST_FRAME_SIZE * 2, GUST_FRAME_SIZE},
    {sGustBurstGfx + GUST_FRAME_SIZE * 3, GUST_FRAME_SIZE},
    {sGustBurstGfx + GUST_FRAME_SIZE * 4, GUST_FRAME_SIZE},
    {sGustBurstGfx + GUST_FRAME_SIZE * 5, GUST_FRAME_SIZE},
    {sGustBurstGfx + GUST_FRAME_SIZE * 6, GUST_FRAME_SIZE},
    {sGustBurstGfx + GUST_FRAME_SIZE * 7, GUST_FRAME_SIZE},
    {sGustBurstGfx + GUST_FRAME_SIZE * 8, GUST_FRAME_SIZE},
    {sGustBurstGfx + GUST_FRAME_SIZE * 9, GUST_FRAME_SIZE},
};

// Frames 0-4 blow east, 5-9 blow south; west and north are the mirrored versions.
#define GUST_ANIM(first, h, v)                                  \
{                                                               \
    ANIMCMD_FRAME((first) + 0, 3, .hFlip = (h), .vFlip = (v)),  \
    ANIMCMD_FRAME((first) + 1, 3, .hFlip = (h), .vFlip = (v)),  \
    ANIMCMD_FRAME((first) + 2, 3, .hFlip = (h), .vFlip = (v)),  \
    ANIMCMD_FRAME((first) + 3, 3, .hFlip = (h), .vFlip = (v)),  \
    ANIMCMD_FRAME((first) + 4, 4, .hFlip = (h), .vFlip = (v)),  \
    ANIMCMD_END,                                                \
}

static const union AnimCmd sGustBurstAnim_South[] = GUST_ANIM(GUST_FRAMES, FALSE, FALSE);
static const union AnimCmd sGustBurstAnim_North[] = GUST_ANIM(GUST_FRAMES, FALSE, TRUE);
static const union AnimCmd sGustBurstAnim_West[]  = GUST_ANIM(0, TRUE, FALSE);
static const union AnimCmd sGustBurstAnim_East[]  = GUST_ANIM(0, FALSE, FALSE);

// Indexed by direction - 1 (DIR_SOUTH, DIR_NORTH, DIR_WEST, DIR_EAST).
static const union AnimCmd *const sGustBurstAnims[] =
{
    sGustBurstAnim_South,
    sGustBurstAnim_North,
    sGustBurstAnim_West,
    sGustBurstAnim_East,
};

static const struct OamData sGustBurstOam =
{
    .shape = SPRITE_SHAPE(16x16),
    .size = SPRITE_SIZE(16x16),
    .priority = 1,
};

static void SpriteCB_GustBurst(struct Sprite *sprite);

static const struct SpriteTemplate sGustBurstTemplate =
{
    .tileTag = TAG_NONE,
    .paletteTag = TAG_TREY_GUST_BURST,
    .oam = &sGustBurstOam,
    .anims = sGustBurstAnims,
    .images = sGustBurstImages,
    .affineAnims = gDummySpriteAffineAnimTable,
    .callback = SpriteCB_GustBurst,
};

static void SpriteCB_GustBurst(struct Sprite *sprite)
{
    u32 i;

    if (!sprite->animEnded)
        return;
    DestroySprite(sprite);
    for (i = 0; i < MAX_SPRITES; i++)
    {
        if (gSprites[i].inUse && gSprites[i].template == &sGustBurstTemplate)
            return;
    }
    FreeSpritePaletteByTag(TAG_TREY_GUST_BURST);
}

void TreySky_StartGustBurst(struct ObjectEvent *puff, u8 direction)
{
    struct Sprite *puffSprite = &gSprites[puff->spriteId];
    s16 dx = 0, dy = 0;
    u8 spriteId, palSlot;

    if (direction < DIR_SOUTH || direction > DIR_EAST)
        return;
    palSlot = IndexOfSpritePaletteTag(TAG_TREY_GUST_BURST);
    if (palSlot == 0xFF)
    {
        struct SpritePalette pal = {sCloudPuffPal, TAG_TREY_GUST_BURST};
        palSlot = LoadSpritePalette(&pal);
        if (palSlot == 0xFF)
            return;
    }
    LoadPalette(TreySky_IsStormWeather() ? sCloudPuffStormPal : sCloudPuffPal, OBJ_PLTT_ID(palSlot), PLTT_SIZE_4BPP);
    UpdateSpritePaletteWithTime(palSlot);

    // half a tile back from the puff, towards the player
    if (direction == DIR_EAST)
        dx = -8;
    else if (direction == DIR_WEST)
        dx = 8;
    else if (direction == DIR_SOUTH)
        dy = -8;
    else
        dy = 8;
    spriteId = CreateSprite(&sGustBurstTemplate, puffSprite->x + dx, puffSprite->y + dy, 0);
    if (spriteId == MAX_SPRITES)
        return;
    gSprites[spriteId].coordOffsetEnabled = TRUE;
    gSprites[spriteId].oam.priority = puffSprite->oam.priority;
    gSprites[spriteId].subpriority = puffSprite->subpriority < 0xFF ? puffSprite->subpriority + 1 : 0xFF; // behind the puff
    StartSpriteAnim(&gSprites[spriteId], direction - 1);
}

// ---------------------------------------------------------------------------
// 3g: Whirlwind, one cyclone at a time (like HGSS Whirlpool). The player spins through the cyclone (or a
// line of them) to the open sky on the far side; the cyclone stays.
// ---------------------------------------------------------------------------
#define WHIRLWIND_MAX_CYCLONES 8

// special: VAR_RESULT = TRUE if there is a cyclone in front of the player with open sky beyond it.
void TreySky_CheckWhirlwindPath(void)
{
    struct ObjectEvent *player = &gObjectEvents[gPlayerAvatar.objectEventId];
    u8 dir = player->facingDirection;
    s16 x = player->currentCoords.x;
    s16 y = player->currentCoords.y;
    u32 cyclones = 0;
    u8 behavior;

    gSpecialVar_Result = FALSE;
    MoveCoords(dir, &x, &y);
    while (MetatileBehavior_IsSkyCyclone(MapGridGetMetatileBehaviorAt(x, y)) && cyclones <= WHIRLWIND_MAX_CYCLONES)
    {
        cyclones++;
        MoveCoords(dir, &x, &y);
    }
    if (cyclones == 0 || cyclones > WHIRLWIND_MAX_CYCLONES)
        return;
    behavior = MapGridGetMetatileBehaviorAt(x, y);
    if (MapGridGetCollisionAt(x, y) || GetObjectEventIdByXY(x, y) != OBJECT_EVENTS_COUNT
     || (MetatileBehavior_IsSkyUpdraft(behavior) && dir != DIR_SOUTH))
        return;
    gSpecialVar_Result = TRUE;
}

#define tState data[0]
#define tDir   data[1]
#define tSpin  data[2]
#define tTimer data[3]

#define WHIRLWIND_SPINS_PER_TILE 8 // two full turns
#define WHIRLWIND_SPIN_FRAMES    3 // frames per facing

static const u8 sWhirlwindSpinOrder[] = {DIR_SOUTH, DIR_WEST, DIR_NORTH, DIR_EAST};

static void Task_TreyWhirlwindRide(u8 taskId)
{
    struct Task *task = &gTasks[taskId];
    struct ObjectEvent *player = &gObjectEvents[gPlayerAvatar.objectEventId];

    if (!ObjectEventClearHeldMovementIfFinished(player))
        return; // a movement is still playing

    switch (task->tState)
    {
    case 0: // fly one tile forward
        ObjectEventSetHeldMovement(player, GetWalkFastMovementAction(task->tDir));
        task->tSpin = 0;
        task->tTimer = 0;
        task->tState = 1;
        break;
    case 1: // arrived: spin while inside a cyclone, then carry on
        if (MetatileBehavior_IsSkyCyclone(player->currentMetatileBehavior))
        {
            if (task->tSpin == 0 && task->tTimer == 0)
                PlaySE(SE_M_GUST2);
            if (task->tSpin >= WHIRLWIND_SPINS_PER_TILE)
            {
                task->tState = 0;
            }
            else if (task->tTimer++ % WHIRLWIND_SPIN_FRAMES == 0)
            {
                ObjectEventSetHeldMovement(player, GetFaceDirectionMovementAction(sWhirlwindSpinOrder[task->tSpin % 4]));
                task->tSpin++;
            }
        }
        else
        {
            ObjectEventSetHeldMovement(player, GetFaceDirectionMovementAction(task->tDir));
            task->tState = 2;
        }
        break;
    default:
        gPlayerAvatar.preventStep = FALSE;
        ScriptContext_Enable();
        DestroyTask(taskId);
        break;
    }
}

// special (use with waitstate): spins the player through the cyclone(s) in front.
void TreySky_StartWhirlwindRide(void)
{
    u8 taskId = CreateTask(Task_TreyWhirlwindRide, 0xFF);

    gTasks[taskId].tDir = gObjectEvents[gPlayerAvatar.objectEventId].facingDirection;
    gPlayerAvatar.preventStep = TRUE;
}

#undef tState
#undef tDir
#undef tSpin
#undef tTimer
