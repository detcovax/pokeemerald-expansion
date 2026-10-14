#ifndef GUARD_TREY_LAYERS_H
#define GUARD_TREY_LAYERS_H

// TREY: layer links at runtime (TREY_PLAN.md 5.2, 5.3). Fly/Soar, landing, Dig and Dive between
// the surface, Sky and Underground layers. Data: struct LayerLink (include/global.fieldmap.h),
// written as "trey_layer_links" in map.json.

#include "constants/trey_layers.h"

struct ObjectEvent;

// Finds the link of `type` on the current map whose rectangle contains the player.
const struct LayerLink *TreyLayer_FindAtPlayer(u8 type);

// Sets the warp destination for `type` from the player's position. With requireLandable, the
// destination tile must be free (or a free tile within 2 steps is used). FALSE if not possible.
bool32 TreyLayer_SetWarpFromPlayer(u8 type, bool32 requireLandable);

bool32 TreyLayer_IsSoaring(void);

// Fly from the party menu: TRUE if the player can soar up here (also sets the warp and remembers
// that the next Fly warp lands on a Sky map).
bool32 TreyLayer_PrepareSoar(void);
// TRUE once after a soar warp, so the arrival skips the "land with the bird" animation.
bool32 TreyLayer_ConsumeSoarPending(void);
bool32 TreyLayer_IsSoarPending(void);

// While soaring: A button / Fly from the party menu start the "Land here?" script.
bool32 TreyLayer_TrySetupLandScript(void);
void TreyLayer_FieldCallback_Land(void);

// Dig: TRUE if a Dig layer link exists here (Dig then changes layer instead of escaping).
bool32 TreyLayer_CanDig(void);
void TreyLayer_FieldCallback_Dig(void);

// Soaring mount: a Fly-bird sprite that follows the player (placeholder art).
u8 TreyLayer_CreateSoarBird(u8 playerObjectEventId);

// Sky clearings (3h): the sky is entered and left only at clearings, like Dive. A ground clearing is a
// SKY_UP link tile (with a light-beam sprite); its Sky end is a landing spot with a SKY_DOWN link back.
bool32 TreyLayer_IsOnLandingSpot(void);   // soaring, on a landing spot with a link down
bool32 TreyLayer_IsOnSkyClearing(void);   // on foot or surfing, on a clearing with a link up
bool32 TreyLayer_TrySetupLayerScript(void); // A button: land, or fly up
void TreyLayer_UpdateSkyBeams(void);
// Map name popup on a layer map: "SKY" on Sky maps, "UNDERGROUND" on maps that Dig back up from; else NULL.
const u8 *TreyLayer_GetPopupName(void);      // every overworld frame: keeps the light beams on screen
// Specials used by EventScript_TreySoarUp.
void TreyLayer_FindSoarMon(void);
void TreyLayer_CheckSoar(void);
void TreyLayer_StartSoarFromClearing(void);

// Specials used by EventScript_TreyLand (data/scripts/trey_layers.inc).
void TreyLayer_CheckLanding(void);
void TreyLayer_StartLanding(void);

#endif // GUARD_TREY_LAYERS_H
