@ TREY (6a, Heart & Soul behaviour MB_HEADBUTT_TREE): A in front of a headbutt tree (field_control_avatar.c).
@ A Pokémon that knows HEADBUTT shakes the tree; a wild Pokémon from the map's "headbutt_mons" table may fall out.
EventScript_TreyHeadbutt::
	lockall
	special TreyHeadbutt_FindPartyMon
	goto_if_eq VAR_RESULT, PARTY_SIZE, EventScript_TreyHeadbuttNoMon
	bufferpartymonnick STR_VAR_1, VAR_RESULT
	msgbox Text_TreyHeadbuttAsk, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, EventScript_TreyHeadbuttEnd
	msgbox Text_TreyHeadbuttUsed, MSGBOX_DEFAULT
	closemessage
	playse SE_M_HEADBUTT
	setvar VAR_0x8004, 1  @ vertical pan
	setvar VAR_0x8005, 0  @ horizontal pan
	setvar VAR_0x8006, 4  @ num shakes
	setvar VAR_0x8007, 3  @ shake delay
	special ShakeCamera
	waitstate
	special TreyHeadbutt_WildEncounter
	goto_if_eq VAR_RESULT, TRUE, EventScript_TreyHeadbuttEnd
	msgbox Text_TreyHeadbuttNothing, MSGBOX_DEFAULT
EventScript_TreyHeadbuttEnd:
	releaseall
	end

EventScript_TreyHeadbuttNoMon:
	msgbox Text_TreyHeadbuttTree, MSGBOX_DEFAULT
	releaseall
	end

Text_TreyHeadbuttTree:
	.string "It's a big tree. A POKéMON may be\n"
	.string "living in it.$"

Text_TreyHeadbuttAsk:
	.string "A POKéMON may be living in this tree.\n"
	.string "Do you want to use HEADBUTT?$"

Text_TreyHeadbuttUsed:
	.string "{STR_VAR_1} used HEADBUTT!$"

Text_TreyHeadbuttNothing:
	.string "Nope. Nothing…$"
