@ TREY: sky HMs (TREY_PLAN.md 3f), used while soaring on Sky maps.
@ Gust: storm puffs (OBJ_EVENT_GFX_TREY_STORM_PUFF) are pushed like Strength boulders until the next map load.
@ Whirlwind: cyclone tiles (MB_SKY_CYCLONE) can be flown through until the next map load.
@ Updraft: rising-air columns (MB_SKY_UPDRAFT) are ridden north, like Waterfall.

EventScript_TreyStormPuff::
	lockall
	goto_if_unset FLAG_TREY_HM_GUST, EventScript_TreyCantGust
	goto_if_set FLAG_TREY_USE_GUST, EventScript_TreyGustActive
	checkpartymove MOVE_GUST
	goto_if_eq VAR_RESULT, PARTY_SIZE, EventScript_TreyCantGust
	setfieldeffectargument 0, VAR_RESULT
	msgbox Text_TreyWantToGust, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, EventScript_TreySkyHMCancel
	closemessage
	dofieldeffect FLDEFF_USE_STRENGTH @ shows the Pokémon and buffers its name; nothing Strength-specific
	waitstate
	setflag FLAG_TREY_USE_GUST
	playse SE_M_GUST
	msgbox Text_TreyMonUsedGust, MSGBOX_DEFAULT
	releaseall
	end

EventScript_TreyCantGust::
	msgbox Text_TreyCantGust, MSGBOX_DEFAULT
	releaseall
	end

EventScript_TreyGustActive::
	msgbox Text_TreyGustActive, MSGBOX_DEFAULT
	releaseall
	end

EventScript_TreyWhirlwind::
	lockall
	goto_if_unset FLAG_TREY_HM_WHIRLWIND, EventScript_TreyCantWhirlwind
	checkpartymove MOVE_WHIRLWIND
	goto_if_eq VAR_RESULT, PARTY_SIZE, EventScript_TreyCantWhirlwind
	setfieldeffectargument 0, VAR_RESULT
	msgbox Text_TreyWantToWhirlwind, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, EventScript_TreySkyHMCancel
	closemessage
	dofieldeffect FLDEFF_USE_STRENGTH @ shows the Pokémon and buffers its name
	waitstate
	setflag FLAG_TREY_USE_WHIRLWIND
	playse SE_M_GUST2
	msgbox Text_TreyMonUsedWhirlwind, MSGBOX_DEFAULT
	releaseall
	end

EventScript_TreyCantWhirlwind::
	msgbox Text_TreyCantWhirlwind, MSGBOX_DEFAULT
	releaseall
	end

EventScript_TreyUpdraft::
	lockall
	goto_if_unset FLAG_TREY_HM_UPDRAFT, EventScript_TreyCantUpdraft
	checkpartymove MOVE_UPDRAFT
	goto_if_eq VAR_RESULT, PARTY_SIZE, EventScript_TreyCantUpdraft
	bufferpartymonnick STR_VAR_1, VAR_RESULT
	setfieldeffectargument 0, VAR_RESULT
	msgbox Text_TreyWantToUpdraft, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, EventScript_TreySkyHMCancel
	msgbox Text_TreyMonUsedUpdraft, MSGBOX_DEFAULT
	dofieldeffect FLDEFF_USE_WATERFALL @ the Waterfall ride also follows MB_SKY_UPDRAFT
	releaseall
	end

EventScript_TreyCantUpdraft::
	msgbox Text_TreyCantUpdraft, MSGBOX_DEFAULT
	releaseall
	end

EventScript_TreySkyHMCancel::
	closemessage
	releaseall
	end

Text_TreyWantToGust:
	.string "It's a small storm cloud. A strong\n"
	.string "gust of wind could push it along.\p"
	.string "Would you like to use GUST?$"

Text_TreyMonUsedGust:
	.string "{STR_VAR_1} used GUST!\p"
	.string "{STR_VAR_1}'s wind can push\n"
	.string "storm clouds now.$"

Text_TreyCantGust:
	.string "It's a small storm cloud. A strong\n"
	.string "gust of wind could push it along.$"

Text_TreyGustActive:
	.string "GUST made it possible to push\n"
	.string "storm clouds around.$"

Text_TreyWantToWhirlwind:
	.string "A fierce cyclone is spinning here.\p"
	.string "Would you like to use WHIRLWIND?$"

Text_TreyMonUsedWhirlwind:
	.string "{STR_VAR_1} used WHIRLWIND!\p"
	.string "Now you can ride through\n"
	.string "the cyclones!$"

Text_TreyCantWhirlwind:
	.string "A fierce cyclone is spinning here.\n"
	.string "It's too strong to fly through.$"

Text_TreyWantToUpdraft:
	.string "Warm air is rushing upward here.\p"
	.string "Would you like to use UPDRAFT?$"

Text_TreyMonUsedUpdraft:
	.string "{STR_VAR_1} used UPDRAFT!$"

Text_TreyCantUpdraft:
	.string "Warm air is rushing upward here.\n"
	.string "It's too strong to fly against.$"
