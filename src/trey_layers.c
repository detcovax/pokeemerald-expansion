// TREY: layer links at runtime (TREY_PLAN.md 5.2, 5.3). See include/trey_layers.h.

#include "global.h"
#include "battle_util.h"
#include "field_effect.h"
#include "task.h"
#include "trey_hm.h"
#include "constants/moves.h"
#include "event_data.h"
#include "event_object_movement.h"
#include "event_scripts.h"
#include "field_player_avatar.h"
#include "field_screen_effect.h"
#include "fieldmap.h"
#include "metatile_behavior.h"
#include "overworld.h"
#include "script.h"
#include "sound.h"
#include "sprite.h"
#include "trey_layers.h"
#include "constants/event_objects.h"
#include "constants/field_effects.h"
#include "constants/map_types.h"
#include "constants/songs.h"

extern const u8 EventScript_TreyLand[];
extern const u8 EventScript_TreySoarUp[]; // 3h: data/scripts/trey_layers.inc

static EWRAM_DATA bool8 sSoarPending = FALSE;

// ---------------------------------------------------------------------------
// Lookup
// ---------------------------------------------------------------------------

static void GetPlayerMapCoords(s16 *x, s16 *y)
{
    PlayerGetDestCoords(x, y);
    *x -= MAP_OFFSET;
    *y -= MAP_OFFSET;
}

static const struct LayerLink *FindLink(const struct MapHeader *header, u8 type, s16 x, s16 y)
{
    u32 i;
    const struct MapHeaderTrey *trey = header->trey;

    if (trey == NULL || trey->layerLinks == NULL)
        return NULL;
    for (i = 0; i < trey->layerLinkCount; i++)
    {
        const struct LayerLink *link = &trey->layerLinks[i];
        if (link->type == type
         && x >= link->x && x < link->x + link->width
         && y >= link->y && y < link->y + link->height)
            return link;
    }
    return NULL;
}

const struct LayerLink *TreyLayer_FindAtPlayer(u8 type)
{
    s16 x, y;
    GetPlayerMapCoords(&x, &y);
    return FindLink(&gMapHeader, type, x, y);
}

// ---------------------------------------------------------------------------
// Landing check on a map that is not loaded yet
// ---------------------------------------------------------------------------

static u16 GetLayoutBehaviorAt(const struct MapLayout *layout, s16 x, s16 y, u16 *block)
{
    u16 metatileId;
    const u16 *attributes;

    *block = layout->map[x + y * layout->width];
    metatileId = UNPACK_METATILE(*block);
    if (metatileId < NUM_METATILES_IN_PRIMARY)
        attributes = layout->primaryTileset->metatileAttributes;
    else
    {
        attributes = layout->secondaryTileset->metatileAttributes;
        metatileId -= NUM_METATILES_IN_PRIMARY;
    }
    return UNPACK_BEHAVIOR(attributes[metatileId]);
}

static bool32 IsTileLandable(const struct MapHeader *header, s16 x, s16 y)
{
    u32 i;
    u16 block, behavior;
    const struct MapLayout *layout = header->mapLayout;

    if (x < 0 || y < 0 || x >= layout->width || y >= layout->height)
        return FALSE;

    behavior = GetLayoutBehaviorAt(layout, x, y, &block);
    if (UNPACK_COLLISION(block) != 0)
        return FALSE;
    if (MetatileBehavior_IsWaterfall(behavior) || MetatileBehavior_IsDoor(behavior) || MetatileBehavior_IsNonAnimDoor(behavior))
        return FALSE;

    // Don't land on people or warps.
    for (i = 0; i < header->events->objectEventCount; i++)
    {
        if (header->events->objectEvents[i].x == x && header->events->objectEvents[i].y == y)
            return FALSE;
    }
    for (i = 0; i < header->events->warpCount; i++)
    {
        if (header->events->warps[i].x == x && header->events->warps[i].y == y)
            return FALSE;
    }
    return TRUE;
}

// Tries the tile itself, then rings of radius 1 and 2 around it.
static bool32 FindLandableTile(const struct MapHeader *header, s16 *x, s16 *y)
{
    s32 radius, dx, dy;

    for (radius = 0; radius <= 2; radius++)
    {
        for (dy = -radius; dy <= radius; dy++)
        {
            for (dx = -radius; dx <= radius; dx++)
            {
                if (max(abs(dx), abs(dy)) != radius)
                    continue;
                if (IsTileLandable(header, *x + dx, *y + dy))
                {
                    *x += dx;
                    *y += dy;
                    return TRUE;
                }
            }
        }
    }
    return FALSE;
}

static bool32 GetDestination(u8 type, bool32 requireLandable, u8 *mapGroup, u8 *mapNum, s16 *destX, s16 *destY)
{
    s16 x, y;
    const struct LayerLink *link;
    const struct MapHeader *destHeader;

    GetPlayerMapCoords(&x, &y);
    link = FindLink(&gMapHeader, type, x, y);
    if (link == NULL)
        return FALSE;

    *mapGroup = link->mapGroup;
    *mapNum = link->mapNum;
    *destX = link->destX + (x - link->x);
    *destY = link->destY + (y - link->y);

    if (requireLandable)
    {
        destHeader = Overworld_GetMapHeaderByGroupAndId(*mapGroup, *mapNum);
        if (!FindLandableTile(destHeader, destX, destY))
            return FALSE;
    }
    return TRUE;
}

bool32 TreyLayer_SetWarpFromPlayer(u8 type, bool32 requireLandable)
{
    u8 mapGroup, mapNum;
    s16 x, y;

    if (!GetDestination(type, requireLandable, &mapGroup, &mapNum, &x, &y))
        return FALSE;
    SetWarpDestination(mapGroup, mapNum, WARP_ID_NONE, x, y);
    return TRUE;
}

// ---------------------------------------------------------------------------
// Soar (Fly) and landing
// ---------------------------------------------------------------------------

bool32 TreyLayer_IsSoaring(void)
{
    return (gPlayerAvatar.flags & PLAYER_AVATAR_FLAG_SOARING) != 0;
}

bool32 TreyLayer_PrepareSoar(void)
{
    sSoarPending = FALSE;
    if (TreyLayer_IsSoaring())
        return FALSE;
    if (!TreyLayer_SetWarpFromPlayer(LAYER_LINK_SKY_UP, TRUE))
        return FALSE;
    sSoarPending = TRUE;
    return TRUE;
}

bool32 TreyLayer_IsSoarPending(void)
{
    return sSoarPending;
}

bool32 TreyLayer_ConsumeSoarPending(void)
{
    bool32 pending = sSoarPending;
    sSoarPending = FALSE;
    return pending;
}

// A while soaring lands only on a landing spot (3g/3h, David 2026-10-13). Fly from the party menu
// while soaring also lands only there; there is no emergency landing.
bool32 TreyLayer_TrySetupLandScript(void)
{
    if (!TreyLayer_IsOnLandingSpot())
        return FALSE;
    ScriptContext_SetupScript(EventScript_TreyLand);
    return TRUE;
}

void TreyLayer_FieldCallback_Land(void)
{
    ScriptContext_SetupScript(EventScript_TreyLand);
}

// special: VAR_RESULT = TRUE if the player can land here (and sets the warp).
void TreyLayer_CheckLanding(void)
{
    gSpecialVar_Result = TreyLayer_SetWarpFromPlayer(LAYER_LINK_SKY_DOWN, TRUE);
}

// special: fades out and lands on the surface with the Fly-in animation.
void TreyLayer_StartLanding(void)
{
    StoreInitialPlayerAvatarState();
    DoTreyLandingWarp();
}

// ---------------------------------------------------------------------------
// Dig
// ---------------------------------------------------------------------------

bool32 TreyLayer_CanDig(void)
{
    u8 mapGroup, mapNum;
    s16 x, y;
    return GetDestination(LAYER_LINK_DIG_DOWN, TRUE, &mapGroup, &mapNum, &x, &y)
        || GetDestination(LAYER_LINK_DIG_UP, TRUE, &mapGroup, &mapNum, &x, &y);
}

void TreyLayer_FieldCallback_Dig(void)
{
    s16 x, y;

    if (TreyLayer_SetWarpFromPlayer(LAYER_LINK_DIG_DOWN, TRUE))
    {
        // Escape Rope / Dig without a link in the Underground layer brings you back to where you dug.
        GetPlayerMapCoords(&x, &y);
        SetEscapeWarp(gSaveBlock1Ptr->location.mapGroup, gSaveBlock1Ptr->location.mapNum, WARP_ID_NONE, x, y);
    }
    else if (!TreyLayer_SetWarpFromPlayer(LAYER_LINK_DIG_UP, TRUE))
    {
        return;
    }
    StoreInitialPlayerAvatarState();
    PlaySE(SE_M_DIG);
    DoDiveWarp();
}

// ---------------------------------------------------------------------------
// Soaring mount sprite (placeholder: the Fly bird, under the player)
// ---------------------------------------------------------------------------

#define sPlayerObjId data[0]

static void SpriteCB_SoarBird(struct Sprite *sprite)
{
    struct ObjectEvent *playerObj = &gObjectEvents[sprite->sPlayerObjId];
    struct Sprite *playerSprite = &gSprites[playerObj->spriteId];

    if (!TreyLayer_IsSoaring())
    {
        DestroySprite(sprite);
        return;
    }
    sprite->x = playerSprite->x;
    sprite->y = playerSprite->y + 8;
    sprite->x2 = playerSprite->x2;
    sprite->y2 = playerSprite->y2;
    sprite->invisible = playerSprite->invisible;
    sprite->hFlip = (playerObj->facingDirection == DIR_EAST);
    sprite->oam.priority = playerSprite->oam.priority;
    sprite->subpriority = playerSprite->subpriority + 1;
}

u8 TreyLayer_CreateSoarBird(u8 playerObjectEventId)
{
    u8 spriteId = CreateSprite(gFieldEffectObjectTemplatePointers[FLDEFFOBJ_BIRD], 0, 0, 1);
    if (spriteId != MAX_SPRITES)
    {
        struct Sprite *sprite = &gSprites[spriteId];
        sprite->oam.paletteNum = LoadPlayerObjectEventPalette(gSaveBlock2Ptr->playerGender);
        sprite->coordOffsetEnabled = TRUE;
        sprite->sPlayerObjId = playerObjectEventId;
        sprite->callback = SpriteCB_SoarBird;
        SpriteCB_SoarBird(sprite);
    }
    return spriteId;
}

#undef sPlayerObjId

// ---------------------------------------------------------------------------
// Sky clearings (3h, David 2026-10-13). Like Dive: the sky is entered and left only at clearings.
// On the ground (or water) a clearing is a LAYER_LINK_SKY_UP link tile, shown by a light-beam sprite;
// on the Sky map it is a landing spot (MB_SKY_LANDING) with a LAYER_LINK_SKY_DOWN link back.
// tools/trey/check_maps.py checks that every pair matches.
// ---------------------------------------------------------------------------

bool32 TreyLayer_IsOnLandingSpot(void)
{
    if (!TreyLayer_IsSoaring())
        return FALSE;
    if (!MetatileBehavior_IsSkyLanding(gObjectEvents[gPlayerAvatar.objectEventId].currentMetatileBehavior))
        return FALSE;
    return TreyLayer_FindAtPlayer(LAYER_LINK_SKY_DOWN) != NULL;
}

bool32 TreyLayer_IsOnSkyClearing(void)
{
    return !TreyLayer_IsSoaring() && TreyLayer_FindAtPlayer(LAYER_LINK_SKY_UP) != NULL;
}

// A button: land at a landing spot, or fly up at a clearing.
bool32 TreyLayer_TrySetupLayerScript(void)
{
    if (TreyLayer_TrySetupLandScript())
        return TRUE;
    if (TreyLayer_IsOnSkyClearing())
    {
        ScriptContext_SetupScript(EventScript_TreySoarUp);
        return TRUE;
    }
    return FALSE;
}

// special: VAR_RESULT = the first party Pokémon that can carry the player up (can use Fly, and can
// take part in Sky Battles), or PARTY_SIZE.
void TreyLayer_FindSoarMon(void)
{
    u32 i;

    gSpecialVar_Result = PARTY_SIZE;
    for (i = 0; i < PARTY_SIZE; i++)
    {
        struct Pokemon *mon = &gPlayerParty[i];
        if (GetMonData(mon, MON_DATA_SPECIES) == SPECIES_NONE)
            break;
        if (TreyHM_MonCanUseInField(mon, MOVE_FLY) && CanMonParticipateInSkyBattle(mon))
        {
            gSpecialVar_Result = i;
            return;
        }
    }
}

// special: VAR_RESULT = TRUE if the player can fly up from here (also sets the warp).
void TreyLayer_CheckSoar(void)
{
    gSpecialVar_Result = TreyLayer_PrepareSoar();
}

#define tState data[0]
#define tMonId data[1]

static void Task_TreySoarFromClearing(u8 taskId)
{
    struct Task *task = &gTasks[taskId];

    if (task->tState == 0)
    {
        gFieldEffectArguments[0] = task->tMonId;
        FieldEffectStart(FLDEFF_USE_FLY);
        task->tState = 1;
    }
    else if (!FieldEffectActiveListContains(FLDEFF_USE_FLY))
    {
        Overworld_ResetStateAfterFly();
        WarpIntoMap();
        SetMainCallback2(CB2_LoadMap);
        TreyLayer_ConsumeSoarPending();
        gFieldCallback = FieldCB_DefaultWarpExit; // arrive in the air
        ScriptContext_Enable(); // let EventScript_TreySoarUp finish (it only has `end` left)
        DestroyTask(taskId);
    }
}

// special (use with waitstate): fly up from a clearing on the Pokémon in VAR_0x8004 (after
// TreyLayer_CheckSoar). The script must keep waiting: if it ended, the field controls would unlock and
// the player's normal input handling would keep the Fly animation from running.
void TreyLayer_StartSoarFromClearing(void)
{
    u8 taskId = CreateTask(Task_TreySoarFromClearing, 0xFF);
    gTasks[taskId].tMonId = gSpecialVar_0x8004;
    // lockall froze the player too, which pauses its sprite animation, so the Fly pose never finished
    // (until a menu unfroze everything). Party-menu Fly only freezes the other objects; do the same.
    UnfreezeObjectEvent(&gObjectEvents[gPlayerAvatar.objectEventId]);
}

#undef tState
#undef tMonId

// ---------------------------------------------------------------------------
// Light beams over the clearings: placed automatically from the map's SKY_UP links, so they work on
// any tileset, on land and on water. Respawned whenever the map changes or sprites were reset.
// Look (David's reference, 2026-10-13): a soft shaft of light slanting down from the upper right.
// Semi-transparent sprites (the overworld already blends OBJ over the BGs), so the ground under the
// beam brightens. The shaft is one 64x64 image drawn 2x bigger and leaned 35 degrees with an affine
// matrix (double-size mode); the pool of light on the tile is a 32x16 sprite. All beams share one
// sprite sheet each, one palette and one matrix. Art: tools/trey/sky_art.py.
// ---------------------------------------------------------------------------
#define TAG_TREY_SKY_BEAM       0x1C32
#define TAG_TREY_SKY_BEAM_POOL  0x1C33
#define MAX_SKY_BEAMS           6
#define NUM_BEAM_SPRITES        (MAX_SKY_BEAMS * 2)

// From sky_art.py beam_affine_params(): 2x scale, leaning 35 degrees clockwise (8.8 fixed point).
#define BEAM_PA 105
#define BEAM_PB 73
#define BEAM_PC (-73)
#define BEAM_PD 105
// Shaft sprite centre relative to the clearing tile's centre (the shaft's foot sits on the tile).
#define BEAM_SHAFT_DX 32
#define BEAM_SHAFT_DY (-46)

static const u32 sSkyBeamShaftGfx[] = INCBIN_U32("graphics/field_effects/pics/trey_sky_beam.4bpp");
static const u32 sSkyBeamPoolGfx[] = INCBIN_U32("graphics/field_effects/pics/trey_sky_beam_pool.4bpp");
static const u16 sSkyBeamPal[] = INCBIN_U16("graphics/field_effects/palettes/trey_sky_beam.gbapal");

static const struct SpriteSheet sSkyBeamShaftSheet = {sSkyBeamShaftGfx, sizeof(sSkyBeamShaftGfx), TAG_TREY_SKY_BEAM};
static const struct SpriteSheet sSkyBeamPoolSheet = {sSkyBeamPoolGfx, sizeof(sSkyBeamPoolGfx), TAG_TREY_SKY_BEAM_POOL};

static const union AnimCmd sSkyBeamAnim[] =
{
    ANIMCMD_FRAME(0, 0),
    ANIMCMD_END,
};

static const union AnimCmd *const sSkyBeamAnims[] = {sSkyBeamAnim};

static const struct OamData sSkyBeamShaftOam =
{
    .affineMode = ST_OAM_AFFINE_DOUBLE,
    .objMode = ST_OAM_OBJ_BLEND,
    .shape = SPRITE_SHAPE(64x64),
    .size = SPRITE_SIZE(64x64),
    .priority = 2,
};

static const struct OamData sSkyBeamPoolOam =
{
    .objMode = ST_OAM_OBJ_BLEND,
    .shape = SPRITE_SHAPE(32x16),
    .size = SPRITE_SIZE(32x16),
    .priority = 2,
};

static void SpriteCB_SkyBeam(struct Sprite *sprite);

static const struct SpriteTemplate sSkyBeamShaftTemplate =
{
    .tileTag = TAG_TREY_SKY_BEAM,
    .paletteTag = TAG_TREY_SKY_BEAM,
    .oam = &sSkyBeamShaftOam,
    .anims = sSkyBeamAnims,
    .images = NULL,
    .affineAnims = gDummySpriteAffineAnimTable,
    .callback = SpriteCB_SkyBeam,
};

static const struct SpriteTemplate sSkyBeamPoolTemplate =
{
    .tileTag = TAG_TREY_SKY_BEAM_POOL,
    .paletteTag = TAG_TREY_SKY_BEAM,
    .oam = &sSkyBeamPoolOam,
    .anims = sSkyBeamAnims,
    .images = NULL,
    .affineAnims = gDummySpriteAffineAnimTable,
    .callback = SpriteCB_SkyBeam,
};

static EWRAM_DATA u8 sSkyBeamSprites[NUM_BEAM_SPRITES] = {0};
static EWRAM_DATA u8 sSkyBeamSpriteCount = 0;
static EWRAM_DATA u8 sSkyBeamMatrixPlus1 = 0; // OAM matrix number + 1, 0 = none (EWRAM can only start at zero)
static EWRAM_DATA u16 sSkyBeamMapKey = 0; // (mapGroup << 8 | mapNum) + 1, 0 = none yet

static void SpriteCB_SkyBeam(struct Sprite *sprite)
{
    // OAM x wraps at 512, so hide beams that are well off screen (the shaft's box is 128x128).
    s32 x = sprite->x + sprite->x2 + gSpriteCoordOffsetX;
    s32 y = sprite->y + sprite->y2 + gSpriteCoordOffsetY;
    sprite->invisible = (x < -64 || x > DISPLAY_WIDTH + 64 || y < -64 || y > DISPLAY_HEIGHT + 64);
}

static bool32 IsSkyBeamSprite(u8 spriteId)
{
    return gSprites[spriteId].inUse
        && (gSprites[spriteId].template == &sSkyBeamShaftTemplate || gSprites[spriteId].template == &sSkyBeamPoolTemplate);
}

static void DestroySkyBeams(void)
{
    u32 i;
    bool32 anyAlive = FALSE;

    for (i = 0; i < sSkyBeamSpriteCount; i++)
    {
        if (IsSkyBeamSprite(sSkyBeamSprites[i]))
        {
            DestroySprite(&gSprites[sSkyBeamSprites[i]]);
            anyAlive = TRUE;
        }
    }
    // If the sprites were wiped (battle, menu), the sheets, palette and matrix were reset with them.
    if (anyAlive)
    {
        if (sSkyBeamMatrixPlus1 != 0)
            FreeOamMatrix(sSkyBeamMatrixPlus1 - 1);
        FreeSpriteTilesByTag(TAG_TREY_SKY_BEAM);
        FreeSpriteTilesByTag(TAG_TREY_SKY_BEAM_POOL);
        FreeSpritePaletteByTag(TAG_TREY_SKY_BEAM);
    }
    sSkyBeamMatrixPlus1 = 0;
    sSkyBeamSpriteCount = 0;
}

static bool32 LoadSkyBeamGfx(void)
{
    if (sSkyBeamMatrixPlus1 == 0)
    {
        u8 matrixNum = AllocOamMatrix();
        if (matrixNum == 0xFF)
            return FALSE;
        SetOamMatrix(matrixNum, BEAM_PA, BEAM_PB, BEAM_PC, BEAM_PD);
        sSkyBeamMatrixPlus1 = matrixNum + 1;
    }
    if (GetSpriteTileStartByTag(TAG_TREY_SKY_BEAM) == TAG_NONE && LoadSpriteSheet(&sSkyBeamShaftSheet) == 0)
        return FALSE;
    if (GetSpriteTileStartByTag(TAG_TREY_SKY_BEAM_POOL) == TAG_NONE && LoadSpriteSheet(&sSkyBeamPoolSheet) == 0)
        return FALSE;
    if (IndexOfSpritePaletteTag(TAG_TREY_SKY_BEAM) == 0xFF)
    {
        struct SpritePalette pal = {sSkyBeamPal, TAG_TREY_SKY_BEAM};
        if (LoadSpritePalette(&pal) == 0xFF)
            return FALSE;
        // Not tinted for the time of day: the light should stand out at night.
    }
    return TRUE;
}

static void CreateSkyBeam(s16 mapX, s16 mapY)
{
    s16 x, y;
    u8 spriteId;

    SetSpritePosToMapCoords(mapX + MAP_OFFSET, mapY + MAP_OFFSET, &x, &y);
    x += 8; // centre of the tile
    y += 8;
    // Behind objects (subpriority 0xFF), so the player is drawn over the light.
    spriteId = CreateSprite(&sSkyBeamPoolTemplate, x, y + 2, 0xFF);
    if (spriteId == MAX_SPRITES)
        return;
    gSprites[spriteId].coordOffsetEnabled = TRUE;
    SpriteCB_SkyBeam(&gSprites[spriteId]);
    sSkyBeamSprites[sSkyBeamSpriteCount++] = spriteId;

    spriteId = CreateSprite(&sSkyBeamShaftTemplate, x + BEAM_SHAFT_DX, y + BEAM_SHAFT_DY, 0xFF);
    if (spriteId == MAX_SPRITES)
        return;
    gSprites[spriteId].coordOffsetEnabled = TRUE;
    gSprites[spriteId].oam.matrixNum = sSkyBeamMatrixPlus1 - 1;
    gSprites[spriteId].affineAnimPaused = TRUE;
    SpriteCB_SkyBeam(&gSprites[spriteId]);
    sSkyBeamSprites[sSkyBeamSpriteCount++] = spriteId;
}

void TreyLayer_UpdateSkyBeams(void)
{
    u16 key = ((gSaveBlock1Ptr->location.mapGroup << 8) | gSaveBlock1Ptr->location.mapNum) + 1;
    const struct MapHeaderTrey *trey = gMapHeader.trey;
    u32 i, tx, ty;
    bool32 valid = (key == sSkyBeamMapKey);

    for (i = 0; i < sSkyBeamSpriteCount && valid; i++)
    {
        if (!IsSkyBeamSprite(sSkyBeamSprites[i]))
            valid = FALSE;
    }
    if (valid)
        return;

    DestroySkyBeams();
    sSkyBeamMapKey = key;

    for (i = 0; trey != NULL && trey->layerLinks != NULL && i < trey->layerLinkCount; i++)
    {
        const struct LayerLink *link = &trey->layerLinks[i];
        if (link->type != LAYER_LINK_SKY_UP)
            continue;
        for (ty = 0; ty < link->height; ty++)
        {
            for (tx = 0; tx < link->width && sSkyBeamSpriteCount + 2 <= NUM_BEAM_SPRITES; tx++)
            {
                if (!LoadSkyBeamGfx())
                    return;
                CreateSkyBeam(link->x + tx, link->y + ty);
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Map name popups on layer maps (4a, David 2026-10-13): just the layer, without the place name.
// Sky and underground maps share the location of the ground below (for met locations and the map).
// ---------------------------------------------------------------------------
static const u8 sText_PopupSky[] = _("SKY");
static const u8 sText_PopupUnderground[] = _("UNDERGROUND");

const u8 *TreyLayer_GetPopupName(void)
{
    const struct MapHeaderTrey *trey = gMapHeader.trey;
    u32 i;

    if (gMapHeader.mapType == MAP_TYPE_SKY)
        return sText_PopupSky;
    for (i = 0; trey != NULL && trey->layerLinks != NULL && i < trey->layerLinkCount; i++)
    {
        if (trey->layerLinks[i].type == LAYER_LINK_DIG_UP)
            return sText_PopupUnderground;
    }
    return NULL;
}
