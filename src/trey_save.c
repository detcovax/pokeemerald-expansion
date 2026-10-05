// TREY: save layout helpers (TREY_PLAN.md Section 4).

#include <stddef.h>
#include "global.h"
#include "save.h"
#include "trey_save.h"
#include "constants/battle_partner.h"
#include "constants/opponents.h"
#include "constants/trainers.h"
#include "constants/region_map_sections.h"
#include "constants/rtc.h"
#include "constants/heal_locations.h"
#include "pokemon.h"

// ---------------------------------------------------------------------------
// Build-time checks
// ---------------------------------------------------------------------------

// The flag and var ranges must not run into the next ID range.
STATIC_ASSERT(FLAGS_COUNT <= SPECIAL_FLAGS_START, TreyFlagsOverlapSpecialFlags);
STATIC_ASSERT(TREY_FLAGS_START <= TREY_FLAGS_END, TreyNoRoomForTreyFlags);
STATIC_ASSERT(VARS_END < SPECIAL_VARS_START, TreyVarsOverlapSpecialVars);
STATIC_ASSERT(TREY_VARS_START <= VARS_END, TreyNoRoomForTreyVars);

// Daily flags are cleared in whole bytes, so they must stay byte-aligned.
STATIC_ASSERT(DAILY_FLAGS_START % 8 == 0, TreyDailyFlagsNotByteAligned);

// Partner trainer IDs sit just above MAX_TRAINERS_COUNT and must not reach the special IDs.
STATIC_ASSERT(TRAINER_PARTNER(PARTNER_COUNT) < TRAINER_UNION_ROOM, TreyPartnerIdsHitUnionRoom);

// Real trainers must never use the special IDs the engine checks without a battle-type test.
// When TRAINERS_COUNT passes one of these, that slot must hold a dummy trainer.
// Remove the matching assert below once the dummy is in place.
STATIC_ASSERT(TRAINERS_COUNT <= TRAINER_FRONTIER_BRAIN, TreyAddDummyTrainerAt1022);
STATIC_ASSERT(TRAINERS_COUNT <= TRAINER_SECRET_BASE, TreyAddDummyTrainerAt1024);
STATIC_ASSERT(TRAINERS_COUNT <= TRAINER_LINK_OPPONENT, TreyAddDummyTrainerAt2048);
STATIC_ASSERT(TRAINERS_COUNT <= MAX_TRAINERS_COUNT, TreyTooManyTrainers);

// Location IDs (TREY_PLAN.md E1/E2): every real MAPSEC must fit in 10 bits and stay below the special METLOC IDs.
STATIC_ASSERT(MAPSEC_COUNT <= METLOC_SPECIAL_EGG, TreyTooManyMapsecs);
STATIC_ASSERT(METLOC_FATEFUL_ENCOUNTER <= MAPSEC_MAX_ID, TreyMetlocOutOfRange);
STATIC_ASSERT(MAPSEC_MAX_ID < (1 << 10), TreyMetLocationIsTenBits);

// Wild encounters (TREY_PLAN.md D22): every time of day has its own explicit table in
// src/data/wild_encounters.json (labels end in _Morning/_Day/_Evening/_Night). There is no fallback:
// a time with no table has no wild Pokémon, and the Pokédex area page shows exactly that.
// A table WITHOUT a time suffix is generated into slot 0 (TIME_MORNING) only, so never add one.
STATIC_ASSERT(OW_TIME_OF_DAY_DISABLE_FALLBACK == TRUE, TreyEncounterFallbackMustBeOff);
STATIC_ASSERT(TIME_OF_DAY_DEFAULT == TIME_MORNING, TreyTimeOfDayDefaultMustBeMorning);

// Heal location IDs are passed around as u8 (SetLastHealLocationWarp etc.). ~150 are planned (TREY_PLAN.md E11).
STATIC_ASSERT(NUM_HEAL_LOCATIONS <= 0xFF, TreyTooManyHealLocations);

// Region badge flags must stay inside the TREY flag range (TREY_PLAN.md E6).
STATIC_ASSERT(TREY_FLAG_BADGES_END <= TREY_FLAGS_END, TreyBadgeFlagsOutOfRange);

// Avatar flag bits must fit the u16 avatar flags (TREY_PLAN.md E8).
STATIC_ASSERT(PLAYER_AVATAR_FLAG_COUNT <= 16, TreyTooManyAvatarFlags);

// The map header layout must match what tools/mapjson emits (header.inc files).
STATIC_ASSERT(sizeof(struct MapHeader) == 0x1C, TreyMapHeaderSizeChanged);
STATIC_ASSERT(offsetof(struct MapHeader, regionMapSectionId) == 0x14, TreyMapHeaderMapsecOffset);
STATIC_ASSERT(offsetof(struct MapHeader, mapType) == 0x18, TreyMapHeaderMapTypeOffset);
STATIC_ASSERT(offsetof(struct MapHeader, battleType) == 0x1B, TreyMapHeaderBattleTypeOffset);

// Reusing the old ribbon bits must not change the Pokémon data size.
STATIC_ASSERT(sizeof(struct PokemonSubstruct3) == 12, TreySubstruct3SizeChanged);
STATIC_ASSERT(sizeof(struct BoxPokemon) == 80, TreyBoxPokemonSizeChanged);

// The TREY data must be the last thing in each save block (see include/trey_save_types.h).
STATIC_ASSERT(offsetof(struct SaveBlock1, treyReserved) + TREY_SB1_RESERVED == sizeof(struct SaveBlock1), TreySB1ReservedNotLast);
STATIC_ASSERT(offsetof(struct SaveBlock2, treyReserved) + TREY_SB2_RESERVED == sizeof(struct SaveBlock2), TreySB2ReservedNotLast);
STATIC_ASSERT(offsetof(struct SaveBlock3, trey) + sizeof(struct TreySaveData) == sizeof(struct SaveBlock3), TreySB3DataNotLast);

// ---------------------------------------------------------------------------
// Save header
// ---------------------------------------------------------------------------

void TreySave_InitNewGame(void)
{
    gSaveBlock2Ptr->treyHeader.magic = TREY_SAVE_MAGIC;
    gSaveBlock2Ptr->treyHeader.version = TREY_SAVE_VERSION;
    gSaveBlock2Ptr->treyHeader.flags = 0;
    memset(gSaveBlock2Ptr->treyReserved, 0, sizeof(gSaveBlock2Ptr->treyReserved));
    memset(gSaveBlock1Ptr->treyReserved, 0, sizeof(gSaveBlock1Ptr->treyReserved));
    memset(&gSaveBlock3Ptr->trey, 0, sizeof(gSaveBlock3Ptr->trey));
}

bool32 TreySave_IsHeaderValid(void)
{
    return gSaveBlock2Ptr->treyHeader.magic == TREY_SAVE_MAGIC
        && gSaveBlock2Ptr->treyHeader.version == TREY_SAVE_VERSION;
}
