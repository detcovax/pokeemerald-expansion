@ TREY: layer link scripts (TREY_PLAN.md 5.3). Used by src/trey_layers.c.

@ 3h: fly up at a sky clearing (light beam). A while standing on it.
EventScript_TreySoarUp::
	lockall
	goto_if_unset FLAG_TREY_HM_FLY, EventScript_TreySoarCantFly
	special TreyLayer_FindSoarMon
	goto_if_eq VAR_RESULT, PARTY_SIZE, EventScript_TreySoarCantFly
	copyvar VAR_0x8004, VAR_RESULT
	bufferpartymonnick STR_VAR_1, VAR_0x8004
	msgbox Text_TreySoarUp, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, EventScript_TreySoarEnd
	special TreyLayer_CheckSoar
	goto_if_eq VAR_RESULT, FALSE, EventScript_TreySoarBlocked
	closemessage
	special TreyLayer_StartSoarFromClearing
	waitstate @ keeps the field controls locked until the warp (the script ending would unlock them)
	end

EventScript_TreySoarCantFly::
	msgbox Text_TreySoarCantFly, MSGBOX_DEFAULT
	goto EventScript_TreySoarEnd

EventScript_TreySoarBlocked::
	msgbox Text_TreySoarBlocked, MSGBOX_DEFAULT
EventScript_TreySoarEnd::
	releaseall
	end

Text_TreySoarUp:
	.string "A beam of light shines down through\n"
	.string "a gap in the clouds.\p"
	.string "Would you like to fly up\n"
	.string "with {STR_VAR_1}?$"

Text_TreySoarCantFly:
	.string "A beam of light shines down through\n"
	.string "a gap in the clouds.\p"
	.string "A Pokémon that can FLY could\n"
	.string "carry you up there.$"

Text_TreySoarBlocked:
	.string "Something is blocking the way\n"
	.string "into the sky right now.$"

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
