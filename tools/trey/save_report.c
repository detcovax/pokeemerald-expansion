// TREY: save block size probe.
// Not part of the ROM. Compiled on its own by tools/trey/save_report.sh with the
// ROM's compiler and flags, so the sizes match the real build exactly.
// Each array's size equals the size being measured; the script reads them with `nm -S`.

#include "global.h"
#include "save.h"
#include "pokemon_storage_system.h"

#define MEASURE(name, size) u8 gTreyMeasure_##name[size];

// Used bytes
MEASURE(Used_SaveBlock1, sizeof(struct SaveBlock1))
MEASURE(Used_SaveBlock2, sizeof(struct SaveBlock2))
MEASURE(Used_SaveBlock3, sizeof(struct SaveBlock3))
MEASURE(Used_PokemonStorage, sizeof(struct PokemonStorage))

// Limits (same formulas as the STATIC_ASSERTs in src/save.c)
MEASURE(Limit_SaveBlock1, SECTOR_DATA_SIZE * (SECTOR_ID_SAVEBLOCK1_END - SECTOR_ID_SAVEBLOCK1_START + 1))
MEASURE(Limit_SaveBlock2, SECTOR_DATA_SIZE)
MEASURE(Limit_SaveBlock3, SAVE_BLOCK_3_CHUNK_SIZE * NUM_SECTORS_PER_SLOT)
MEASURE(Limit_PokemonStorage, SECTOR_DATA_SIZE * (SECTOR_ID_PKMN_STORAGE_END - SECTOR_ID_PKMN_STORAGE_START + 1))

// Details that the plan tracks
MEASURE(Info_Flags, sizeof(((struct SaveBlock1 *)0)->flags))
MEASURE(Info_Vars, sizeof(((struct SaveBlock1 *)0)->vars))
MEASURE(Info_BoxPokemon, sizeof(struct BoxPokemon))
MEASURE(Info_Time, sizeof(struct Time))
