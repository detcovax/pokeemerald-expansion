@ TREY (4f, TREY_PLAN.md 5.10): quest scripts.

@ Debug menu "TREY: test quest step": moves QUEST_TEST_SURVEY one step on with the script macros,
@ so the banner and the goto_if_quest_* macros can be tried in game.
TreyQuest_EventScript_DebugStep::
	goto_if_quest_eq QUEST_TEST_SURVEY, QUEST_STAGE_DONE, TreyQuest_EventScript_DebugReset
	goto_if_quest_ge QUEST_TEST_SURVEY, 3, TreyQuest_EventScript_DebugComplete
	checkqueststage QUEST_TEST_SURVEY
	addvar VAR_RESULT, 1
	setqueststage QUEST_TEST_SURVEY, VAR_RESULT
	releaseall
	end

TreyQuest_EventScript_DebugComplete::
	completequest QUEST_TEST_SURVEY
	releaseall
	end

TreyQuest_EventScript_DebugReset::
	setqueststage QUEST_TEST_SURVEY, QUEST_STAGE_NONE
	msgbox TreyQuest_Text_DebugReset, MSGBOX_DEFAULT
	releaseall
	end

TreyQuest_Text_DebugReset:
	.string "Test quest reset to not started.$"
