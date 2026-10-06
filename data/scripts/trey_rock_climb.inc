@ TREY: Rock Climb (TREY_PLAN.md 5.3). Started by pressing A at an MB_ROCK_CLIMB tile.

EventScript_TreyRockClimb::
	lockall
	checkpartymove MOVE_ROCK_CLIMB
	goto_if_eq VAR_RESULT, PARTY_SIZE, EventScript_TreyCantRockClimb
	copyvar VAR_0x8004, VAR_RESULT
	bufferpartymonnick STR_VAR_1, VAR_RESULT
	msgbox Text_TreyWantToRockClimb, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, EventScript_TreyRockClimbEnd
	msgbox Text_TreyMonUsedRockClimb, MSGBOX_DEFAULT
	hidefollowernpc
	special TreyRockClimb_Start
	waitstate
	callnative FollowerNPC_WarpSetEnd
	goto EventScript_TreyRockClimbEnd

EventScript_TreyCantRockClimb::
	msgbox Text_TreyCantRockClimb, MSGBOX_DEFAULT
EventScript_TreyRockClimbEnd::
	releaseall
	end

Text_TreyWantToRockClimb:
	.string "It's a rugged rock wall.\n"
	.string "Would you like to use ROCK CLIMB?$"

Text_TreyMonUsedRockClimb:
	.string "{STR_VAR_1} used ROCK CLIMB!$"

Text_TreyCantRockClimb:
	.string "It's a rugged rock wall.\n"
	.string "A POKéMON may be able to climb it.$"
