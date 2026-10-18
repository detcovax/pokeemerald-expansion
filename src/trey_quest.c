// TREY (TREY_PLAN.md 5.10, E15, Phase 4 chunk 4f): quest engine, banner and quest log.
//
// Decisions (David, 2026-10-18): a start menu QUESTS log; a small banner when a quest starts, advances or
// completes; each region's story quest is its progress variable; quests stay hidden until started.

#include "global.h"
#include "event_data.h"
#include "event_object_lock.h"
#include "event_object_movement.h"
#include "list_menu.h"
#include "main.h"
#include "malloc.h"
#include "map_name_popup.h"
#include "menu.h"
#include "overworld.h"
#include "script.h"
#include "sound.h"
#include "string_util.h"
#include "task.h"
#include "text.h"
#include "trey_dex.h"
#include "trey_quest.h"
#include "window.h"
#include "constants/songs.h"

#include "data/trey/quests.h"

// Strings live at file scope: a COMPOUND_STRING inside a function is a temporary (see TREY_PLAN.md notes).
static const u8 sText_QuestComplete[] = _("Quest complete: ");
static const u8 sText_NewQuest[] = _("New quest: ");
static const u8 sText_QuestUpdated[] = _("Quest updated: ");
static const u8 sText_LogComplete[] = _("  Complete!");
static const u8 sText_LogNotStarted[] = _("  Not started");
static const u8 sText_LogStep[] = _("  Step ");
static const u8 sText_LogDone[] = _("DONE");
static const u8 sText_LogEmpty[] = _("No quests yet.");

STATIC_ASSERT(QUEST_COUNT <= TREY_QUEST_SLOTS, TreyTooManyQuests);
STATIC_ASSERT(QUEST_COUNT <= QUEST_STAGE_DONE, TreyQuestNumHitsDoneValue);

// ---------------------------------------------------------------------------
// Stages
// ---------------------------------------------------------------------------

static void ShowBanner(u32 quest, u32 oldStage, u32 newStage);

bool32 TreyQuest_IsValid(u32 quest)
{
    return quest < QUEST_COUNT && gTreyQuests[quest].numStages != 0;
}

u8 TreyQuest_GetStage(u32 quest)
{
    if (!TreyQuest_IsValid(quest))
        return QUEST_STAGE_NONE;
    return gSaveBlock3Ptr->trey.questStages[quest];
}

void TreyQuest_SetStage(u32 quest, u32 stage)
{
    u32 old;

    if (!TreyQuest_IsValid(quest))
        return;
    if (stage != QUEST_STAGE_DONE && stage > gTreyQuests[quest].numStages)
        stage = gTreyQuests[quest].numStages;
    old = gSaveBlock3Ptr->trey.questStages[quest];
    gSaveBlock3Ptr->trey.questStages[quest] = stage;
    if (old != stage && stage != QUEST_STAGE_NONE)
        ShowBanner(quest, old, stage);
}

void TreyQuest_Complete(u32 quest)
{
    TreyQuest_SetStage(quest, QUEST_STAGE_DONE);
}

bool32 TreyQuest_IsStarted(u32 quest)
{
    return TreyQuest_GetStage(quest) != QUEST_STAGE_NONE;
}

bool32 TreyQuest_IsDone(u32 quest)
{
    return TreyQuest_GetStage(quest) == QUEST_STAGE_DONE;
}

bool32 TreyQuest_AnyStarted(void)
{
    u32 i;
    for (i = 0; i < QUEST_COUNT; i++)
    {
        if (TreyQuest_IsStarted(i))
            return TRUE;
    }
    return FALSE;
}

const u8 *TreyQuest_GetStageText(u32 quest)
{
    u32 stage = TreyQuest_GetStage(quest);
    if (stage == QUEST_STAGE_NONE)
        return NULL;
    if (stage == QUEST_STAGE_DONE)
        stage = gTreyQuests[quest].numStages;
    return gTreyQuests[quest].stages[stage - 1];
}

// ---------------------------------------------------------------------------
// Script macros: arguments follow the callnative inline (see asm/macros/event.inc). Both may be vars.
// ---------------------------------------------------------------------------

void TreyQuest_Native_SetStage(struct ScriptContext *ctx)
{
    u32 quest = VarGet(ScriptReadHalfword(ctx));
    u32 stage = VarGet(ScriptReadHalfword(ctx));

    Script_RequestEffects(SCREFF_V1 | SCREFF_SAVE | SCREFF_HARDWARE);
    TreyQuest_SetStage(quest, stage);
}

void TreyQuest_Native_Complete(struct ScriptContext *ctx)
{
    u32 quest = VarGet(ScriptReadHalfword(ctx));

    Script_RequestEffects(SCREFF_V1 | SCREFF_SAVE | SCREFF_HARDWARE);
    TreyQuest_Complete(quest);
}

void TreyQuest_Native_GetStage(struct ScriptContext *ctx)
{
    u32 quest = VarGet(ScriptReadHalfword(ctx));

    Script_RequestEffects(SCREFF_V1 | SCREFF_SAVE);
    gSpecialVar_Result = TreyQuest_GetStage(quest);
}

// ---------------------------------------------------------------------------
// Banner: "New quest: X" / "Quest updated: X" / "Quest complete: X" at the top of the field for a moment.
// Shown only in the overworld (not in battle, menus or tests). Uses BG0 tiles 0x162-0x191, between the
// map name popup (0x107-0x161) and the message box (0x194).
// ---------------------------------------------------------------------------

#define BANNER_FRAMES 150

static EWRAM_DATA u8 sBannerWindowIdPlus1 = 0; // EWRAM must start at 0: store id + 1
static EWRAM_DATA u8 sBannerTaskIdPlus1 = 0;

static const struct WindowTemplate sBannerWindowTemplate =
{
    .bg = 0,
    .tilemapLeft = 3,
    .tilemapTop = 1,
    .width = 24,
    .height = 2,
    .paletteNum = 15,
    .baseBlock = 0x162,
};

static void Task_QuestBanner(u8 taskId);

static bool32 BannerIsShowing(void)
{
    return sBannerTaskIdPlus1 != 0
        && gTasks[sBannerTaskIdPlus1 - 1].isActive
        && gTasks[sBannerTaskIdPlus1 - 1].func == Task_QuestBanner;
}

static void RemoveBanner(void)
{
    if (BannerIsShowing() && sBannerWindowIdPlus1 != 0)
    {
        ClearStdWindowAndFrame(sBannerWindowIdPlus1 - 1, TRUE);
        RemoveWindow(sBannerWindowIdPlus1 - 1);
        DestroyTask(sBannerTaskIdPlus1 - 1);
    }
    sBannerWindowIdPlus1 = 0;
    sBannerTaskIdPlus1 = 0;
}

static void Task_QuestBanner(u8 taskId)
{
    // Leaving the overworld (warp, battle, menu) resets the field windows: just stop.
    if (gMain.callback2 != CB2_Overworld)
    {
        sBannerWindowIdPlus1 = 0;
        sBannerTaskIdPlus1 = 0;
        DestroyTask(taskId);
        return;
    }
    if (--gTasks[taskId].data[0] <= 0)
        RemoveBanner();
}

static void ShowBanner(u32 quest, u32 oldStage, u32 newStage)
{
    const u8 *prefix;
    u8 windowId;

    if (gMain.callback2 != CB2_Overworld)
        return;

    if (newStage == QUEST_STAGE_DONE)
    {
        prefix = sText_QuestComplete;
        PlaySE(SE_SUCCESS);
    }
    else if (oldStage == QUEST_STAGE_NONE)
    {
        prefix = sText_NewQuest;
        PlaySE(SE_PIN);
    }
    else
    {
        prefix = sText_QuestUpdated;
        PlaySE(SE_PIN);
    }

    if (BannerIsShowing())
    {
        windowId = sBannerWindowIdPlus1 - 1;
    }
    else
    {
        HideMapNamePopUpWindow();
        LoadMessageBoxAndBorderGfx();
        windowId = AddWindow(&sBannerWindowTemplate);
        if (windowId == WINDOW_NONE)
            return;
        sBannerWindowIdPlus1 = windowId + 1;
        sBannerTaskIdPlus1 = CreateTask(Task_QuestBanner, 90) + 1;
        DrawStdWindowFrame(windowId, FALSE);
        PutWindowTilemap(windowId);
    }
    gTasks[sBannerTaskIdPlus1 - 1].data[0] = BANNER_FRAMES;

    StringCopy(StringCopy(gStringVar4, prefix), gTreyQuests[quest].name);
    FillWindowPixelBuffer(windowId, PIXEL_FILL(1));
    AddTextPrinterParameterized(windowId, FONT_NORMAL, gStringVar4, 0, 1, TEXT_SKIP_DRAW, NULL);
    CopyWindowToVram(windowId, COPYWIN_FULL);
}

// ---------------------------------------------------------------------------
// Quest log: opened from the start menu (field, no screen change). Started quests grouped by region,
// active before complete; the bottom window shows the selected quest's region, stage and stage line.
// Debug mode (debug menu "TREY: quests"): every quest, A advances its stage (... -> done -> not started).
// ---------------------------------------------------------------------------

#define LOG_ROWS 5

struct QuestLog
{
    struct ListMenuItem items[QUEST_COUNT + TREY_DEX_COUNT];
    u16 count;
    u8 listWindowId;
    u8 infoWindowId;
    u8 listTaskId;
    bool8 debugMode;
};

static EWRAM_DATA struct QuestLog *sQuestLog = NULL;

static const struct WindowTemplate sLogListWindowTemplate =
{
    .bg = 0, .tilemapLeft = 1, .tilemapTop = 1, .width = 18, .height = LOG_ROWS * 2, .paletteNum = 15, .baseBlock = 0x001,
};

static const struct WindowTemplate sLogInfoWindowTemplate =
{
    .bg = 0, .tilemapLeft = 1, .tilemapTop = 13, .width = 28, .height = 6, .paletteNum = 15, .baseBlock = 0x0C0,
};

static void Task_QuestLog(u8 taskId);

static void BuildLogItems(void)
{
    u32 dex, pass, i;

    sQuestLog->count = 0;
    for (dex = TREY_DEX_KANTO; dex < TREY_DEX_COUNT; dex++)
    {
        bool32 header = FALSE;
        for (pass = 0; pass < 2; pass++) // active first, then complete
        {
            for (i = 0; i < QUEST_COUNT; i++)
            {
                if (!TreyQuest_IsValid(i) || gTreyQuests[i].region != dex)
                    continue;
                if (!sQuestLog->debugMode && !TreyQuest_IsStarted(i)) // hidden until started
                    continue;
                if (TreyQuest_IsDone(i) != (pass == 1))
                    continue;
                if (!header)
                {
                    sQuestLog->items[sQuestLog->count].name = TreyDex_GetName(dex);
                    sQuestLog->items[sQuestLog->count].id = LIST_HEADER;
                    sQuestLog->count++;
                    header = TRUE;
                }
                sQuestLog->items[sQuestLog->count].name = gTreyQuests[i].name;
                sQuestLog->items[sQuestLog->count].id = i;
                sQuestLog->count++;
            }
        }
    }
}

static void PrintQuestInfo(s32 quest)
{
    u8 *str;
    u32 stage;
    const u8 *text;

    FillWindowPixelBuffer(sQuestLog->infoWindowId, PIXEL_FILL(1));
    if (quest >= 0 && TreyQuest_IsValid(quest))
    {
        stage = TreyQuest_GetStage(quest);
        str = StringCopy(gStringVar4, TreyDex_GetName(gTreyQuests[quest].region));
        if (stage == QUEST_STAGE_DONE)
        {
            StringCopy(str, sText_LogComplete);
        }
        else if (stage == QUEST_STAGE_NONE)
        {
            StringCopy(str, sText_LogNotStarted);
        }
        else
        {
            str = StringCopy(str, sText_LogStep);
            str = ConvertIntToDecimalStringN(str, stage, STR_CONV_MODE_LEFT_ALIGN, 3);
            *str++ = CHAR_SLASH;
            ConvertIntToDecimalStringN(str, gTreyQuests[quest].numStages, STR_CONV_MODE_LEFT_ALIGN, 3);
        }
        AddTextPrinterParameterized(sQuestLog->infoWindowId, FONT_NORMAL, gStringVar4, 0, 1, TEXT_SKIP_DRAW, NULL);
        text = TreyQuest_GetStageText(quest);
        if (text == NULL)
            text = gTreyQuests[quest].stages[0];
        AddTextPrinterParameterized(sQuestLog->infoWindowId, FONT_NORMAL, text, 0, 17, TEXT_SKIP_DRAW, NULL);
    }
    CopyWindowToVram(sQuestLog->infoWindowId, COPYWIN_GFX);
}

static void LogMoveCursor(s32 itemIndex, bool8 onInit, struct ListMenu *list)
{
    if (!onInit)
        PlaySE(SE_SELECT);
    PrintQuestInfo(itemIndex);
}

// Right-hand status on each row: DONE, or (debug) the stage
static void LogPrintItem(u8 windowId, u32 itemId, u8 y)
{
    u8 text[12];
    u32 stage;

    if ((s32)itemId == LIST_HEADER || !TreyQuest_IsValid(itemId))
        return;
    stage = TreyQuest_GetStage(itemId);
    if (stage == QUEST_STAGE_DONE)
        StringCopy(text, sText_LogDone);
    else if (sQuestLog->debugMode)
        ConvertIntToDecimalStringN(text, stage, STR_CONV_MODE_LEFT_ALIGN, 3);
    else
        return;
    AddTextPrinterParameterized(windowId, FONT_SMALL, text, 18 * 8 - GetStringWidth(FONT_SMALL, text, 0) - 4, y, TEXT_SKIP_DRAW, NULL);
}

static void CreateLogList(u16 scroll, u16 row)
{
    struct ListMenuTemplate t = {0};

    t.items = sQuestLog->items;
    t.moveCursorFunc = LogMoveCursor;
    t.itemPrintFunc = LogPrintItem;
    t.totalItems = sQuestLog->count;
    t.maxShowed = min(sQuestLog->count, LOG_ROWS);
    t.windowId = sQuestLog->listWindowId;
    t.header_X = 0;
    t.item_X = 8;
    t.cursor_X = 0;
    t.upText_Y = 1;
    t.cursorPal = 2;
    t.fillValue = 1;
    t.cursorShadowPal = 3;
    t.lettersSpacing = 0;
    t.itemVerticalPadding = 0;
    t.scrollMultiple = LIST_NO_MULTIPLE_SCROLL;
    t.fontId = FONT_NORMAL;
    t.cursorKind = CURSOR_BLACK_ARROW;
    FillWindowPixelBuffer(sQuestLog->listWindowId, PIXEL_FILL(1));
    sQuestLog->listTaskId = ListMenuInit(&t, scroll, row);
    CopyWindowToVram(sQuestLog->listWindowId, COPYWIN_FULL);
}

void TreyQuestLog_Open(bool32 debugMode)
{
    sQuestLog = AllocZeroed(sizeof(*sQuestLog));
    sQuestLog->debugMode = debugMode;
    BuildLogItems();

    HideMapNamePopUpWindow();
    LoadMessageBoxAndBorderGfx();
    sQuestLog->listWindowId = AddWindow(&sLogListWindowTemplate);
    sQuestLog->infoWindowId = AddWindow(&sLogInfoWindowTemplate);
    DrawStdWindowFrame(sQuestLog->listWindowId, FALSE);
    DrawStdWindowFrame(sQuestLog->infoWindowId, FALSE);
    PutWindowTilemap(sQuestLog->infoWindowId);
    if (sQuestLog->count != 0)
    {
        CreateLogList(0, 1); // row 0 is the first region's header
    }
    else
    {
        // nothing started yet (the start menu only offers QUESTS once one has, but the debug list can be empty too)
        FillWindowPixelBuffer(sQuestLog->listWindowId, PIXEL_FILL(1));
        AddTextPrinterParameterized(sQuestLog->listWindowId, FONT_NORMAL, sText_LogEmpty, 8, 1, TEXT_SKIP_DRAW, NULL);
        PutWindowTilemap(sQuestLog->listWindowId);
        CopyWindowToVram(sQuestLog->listWindowId, COPYWIN_FULL);
        sQuestLog->listTaskId = TASK_NONE;
        PrintQuestInfo(-1);
    }
    CreateTask(Task_QuestLog, 80);
}

static void CloseQuestLog(u8 taskId)
{
    if (sQuestLog->listTaskId != TASK_NONE)
        DestroyListMenuTask(sQuestLog->listTaskId, NULL, NULL);
    ClearStdWindowAndFrame(sQuestLog->listWindowId, FALSE);
    ClearStdWindowAndFrame(sQuestLog->infoWindowId, TRUE);
    RemoveWindow(sQuestLog->listWindowId);
    RemoveWindow(sQuestLog->infoWindowId);
    FREE_AND_SET_NULL(sQuestLog);
    DestroyTask(taskId);
    ScriptUnfreezeObjectEvents();
    UnlockPlayerFieldControls();
}

static void Task_QuestLog(u8 taskId)
{
    s32 input;

    if (sQuestLog->listTaskId == TASK_NONE)
    {
        if (JOY_NEW(A_BUTTON | B_BUTTON | START_BUTTON))
        {
            PlaySE(SE_SELECT);
            CloseQuestLog(taskId);
        }
        return;
    }

    if (JOY_NEW(START_BUTTON))
    {
        PlaySE(SE_SELECT);
        CloseQuestLog(taskId);
        return;
    }
    input = ListMenu_ProcessInput(sQuestLog->listTaskId);
    if (input == LIST_CANCEL)
    {
        PlaySE(SE_SELECT);
        CloseQuestLog(taskId);
    }
    else if (input >= 0 && sQuestLog->debugMode)
    {
        // Debug: advance the stage. No banner here (the log covers the screen top).
        u16 scroll, row;
        u32 stage = TreyQuest_GetStage(input);

        if (stage == QUEST_STAGE_DONE)
            stage = QUEST_STAGE_NONE;
        else if (stage >= gTreyQuests[input].numStages)
            stage = QUEST_STAGE_DONE;
        else
            stage++;
        gSaveBlock3Ptr->trey.questStages[input] = stage;
        PlaySE(SE_PIN);
        ListMenuGetScrollAndRow(sQuestLog->listTaskId, &scroll, &row);
        DestroyListMenuTask(sQuestLog->listTaskId, NULL, NULL);
        CreateLogList(scroll, row);
    }
}
