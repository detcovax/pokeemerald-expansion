@ TREY (6a-5): whirlpools on the Johto maps (Heart & Soul's object events with this script).
@ A Pokémon that can use WHIRLPOOL in the field (TREY HM rules, src/trey_hm.c) carries the player
@ three tiles across in the direction they face, as in Heart & Soul.
EventScript_Whirlpool::
	lockall
	treycheckpartymove MOVE_WHIRLPOOL
	goto_if_eq VAR_RESULT, PARTY_SIZE, EventScript_TreyWhirlpoolCant
	bufferpartymonnick STR_VAR_1, VAR_RESULT
	msgbox Text_TreyWhirlpoolAsk, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, EventScript_TreyWhirlpoolEnd
	msgbox Text_TreyWhirlpoolUsed, MSGBOX_DEFAULT
	closemessage
	playse SE_M_WHIRLPOOL
	goto_if_eq VAR_FACING, DIR_NORTH, EventScript_TreyWhirlpoolNorth
	goto_if_eq VAR_FACING, DIR_SOUTH, EventScript_TreyWhirlpoolSouth
	goto_if_eq VAR_FACING, DIR_EAST, EventScript_TreyWhirlpoolEast
	goto_if_eq VAR_FACING, DIR_WEST, EventScript_TreyWhirlpoolWest
EventScript_TreyWhirlpoolEnd:
	releaseall
	end

EventScript_TreyWhirlpoolNorth:
	applymovement OBJ_EVENT_ID_PLAYER, Movement_TreyWhirlpoolNorth
	waitmovement 0
	releaseall
	end

EventScript_TreyWhirlpoolSouth:
	applymovement OBJ_EVENT_ID_PLAYER, Movement_TreyWhirlpoolSouth
	waitmovement 0
	releaseall
	end

EventScript_TreyWhirlpoolEast:
	applymovement OBJ_EVENT_ID_PLAYER, Movement_TreyWhirlpoolEast
	waitmovement 0
	releaseall
	end

EventScript_TreyWhirlpoolWest:
	applymovement OBJ_EVENT_ID_PLAYER, Movement_TreyWhirlpoolWest
	waitmovement 0
	releaseall
	end

EventScript_TreyWhirlpoolCant:
	msgbox Text_TreyWhirlpoolCant, MSGBOX_DEFAULT
	releaseall
	end

Movement_TreyWhirlpoolNorth:
	slide_up
	slide_up
	slide_up
	step_end

Movement_TreyWhirlpoolSouth:
	slide_down
	slide_down
	slide_down
	step_end

Movement_TreyWhirlpoolEast:
	slide_right
	slide_right
	slide_right
	step_end

Movement_TreyWhirlpoolWest:
	slide_left
	slide_left
	slide_left
	step_end

Text_TreyWhirlpoolCant:
	.string "The water is swirling and spinning\n"
	.string "around with a mighty roar.$"

Text_TreyWhirlpoolAsk:
	.string "It's a vicious whirlpool!\p"
	.string "Want to use WHIRLPOOL to cross it?$"

Text_TreyWhirlpoolUsed:
	.string "{STR_VAR_1} used WHIRLPOOL!$"
