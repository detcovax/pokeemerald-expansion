// TREY (5b, TREY_PLAN.md D27): placeholder new-game intro for the vertical slice.
// A new game wakes up in the player's room in Pallet Town (new_game.c), and on the first field frame
// TreyIntro_EventScript_NewGame (data/scripts/trey_intro.inc) asks boy/girl and a name and gives a Mew.
// Replaced by the real TREY intro later (D25).
#include "global.h"
#include "event_data.h"
#include "main.h"
#include "naming_screen.h"
#include "overworld.h"
#include "script.h"
#include "string_util.h"
#include "trey_intro.h"
#include "constants/characters.h"
#include "constants/flags.h"

extern const u8 TreyIntro_EventScript_NewGame[];

static const u8 sText_DefaultNameMale[] = _("RED");
static const u8 sText_DefaultNameFemale[] = _("LEAF");

void TreyIntro_InitNewGame(void)
{
#if TREY_MINIMAL_INTRO
    FlagSet(FLAG_TREY_INTRO_PENDING);
#endif
}

// Called from the field input loop (field_control_avatar.c) before the region arrival scripts.
bool32 TreyIntro_TryRun(void)
{
    if (!FlagGet(FLAG_TREY_INTRO_PENDING))
        return FALSE;
    FlagClear(FLAG_TREY_INTRO_PENDING);
    ScriptContext_SetupScript(TreyIntro_EventScript_NewGame);
    return TRUE;
}

// special: VAR_RESULT 0 = boy, 1 = girl (from the dynmultichoice)
void TreyIntro_SetGender(void)
{
    gSaveBlock2Ptr->playerGender = (gSpecialVar_Result == 1) ? FEMALE : MALE;
}

// special: the naming screen; the script waits with waitstate
void TreyIntro_NamePlayer(void)
{
    DoNamingScreen(NAMING_SCREEN_PLAYER, gSaveBlock2Ptr->playerName, gSaveBlock2Ptr->playerGender, 0, 0, CB2_ReturnToFieldContinueScript);
}

// special: an empty name gets the FRLG default for the chosen gender
void TreyIntro_FinishNaming(void)
{
    if (gSaveBlock2Ptr->playerName[0] == EOS)
        StringCopy(gSaveBlock2Ptr->playerName, gSaveBlock2Ptr->playerGender == FEMALE ? sText_DefaultNameFemale : sText_DefaultNameMale);
}
