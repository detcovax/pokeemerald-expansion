#ifndef GUARD_TREY_QUEST_H
#define GUARD_TREY_QUEST_H

// TREY (TREY_PLAN.md 5.10, E15, Phase 4 chunk 4f): quests.
// Data: docs/trey/quests.csv -> include/constants/trey_quests.h (QUEST_*) + src/data/trey/quests.h.
// Save: one stage byte per quest in SaveBlock3 (QUEST_STAGE_NONE = not started, 1..numStages, QUEST_STAGE_DONE).
// Each region's main story is a quest (QUEST_<REGION>_STORY): its stage is that region's progress.

#include "constants/trey_quests.h"

struct ScriptContext;

struct TreyQuest
{
    u8 region;               // TREY_DEX_* (the quest log groups by it)
    u8 numStages;            // 0 = empty slot
    const u8 *name;
    const u8 *const *stages; // line shown in the log for stage 1..numStages
};

extern const struct TreyQuest gTreyQuests[QUEST_COUNT];

bool32 TreyQuest_IsValid(u32 quest);
u8 TreyQuest_GetStage(u32 quest);
void TreyQuest_SetStage(u32 quest, u32 stage); // shows the banner when the quest starts, advances or completes
void TreyQuest_Complete(u32 quest);
bool32 TreyQuest_IsStarted(u32 quest);         // stage above 0 (done counts as started)
bool32 TreyQuest_IsDone(u32 quest);
bool32 TreyQuest_AnyStarted(void);
const u8 *TreyQuest_GetStageText(u32 quest);   // current stage's line, NULL if not started

// Script macros (asm/macros/event.inc): setqueststage, completequest, checkqueststage, goto_if_quest_*
void TreyQuest_Native_SetStage(struct ScriptContext *ctx);
void TreyQuest_Native_Complete(struct ScriptContext *ctx);
void TreyQuest_Native_GetStage(struct ScriptContext *ctx);

// Quest log (start menu QUESTS). debugMode: every quest, A advances its stage.
void TreyQuestLog_Open(bool32 debugMode);

#endif // GUARD_TREY_QUEST_H
