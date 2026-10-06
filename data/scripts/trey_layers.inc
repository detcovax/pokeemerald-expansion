@ TREY: layer link scripts (TREY_PLAN.md 5.3). Used by src/trey_layers.c.

EventScript_TreyLand::
	lockall
	special TreyLayer_CheckLanding
	goto_if_eq VAR_RESULT, FALSE, EventScript_TreyCantLand
	msgbox Text_TreyLandHere, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, EventScript_TreyLandEnd
	special TreyLayer_StartLanding
	end

EventScript_TreyCantLand::
	msgbox Text_TreyCantLand, MSGBOX_DEFAULT
EventScript_TreyLandEnd::
	releaseall
	end

Text_TreyLandHere:
	.string "Would you like to land here?$"

Text_TreyCantLand:
	.string "There's nowhere to land below.$"
