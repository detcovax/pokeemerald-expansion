// TREY: layer links at runtime (TREY_PLAN.md 5.2, 5.3). See include/trey_layers.h.

#include "global.h"
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
#include "constants/songs.h"

extern const u8 EventScript_TreyLand[];

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

bool32 TreyLayer_TrySetupLandScript(void)
{
    if (!TreyLayer_IsSoaring())
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
