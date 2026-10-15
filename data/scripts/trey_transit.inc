@ TREY: ships and trains, ridden on board (TREY_PLAN.md 5.4, Phase 4 chunk 4c). Runtime: src/trey_transit.c.
@
@ A harbour clerk sets VAR_0x8004 = TRANSIT_SHIP/TRAIN and VAR_0x8005 = this stop, then calls
@ TreyTransit_EventScript_ChooseDestination. It comes back with VAR_0x8006 = the chosen stop, or
@ TRANSIT_STOP_NONE. Lilycove also offers its event islands: set VAR_0x8007 = 1 and they come back as
@ TRANSIT_EVENT_* ids. Then the clerk runs its own boarding animation and warps on board.
@ On board: the ship gets under way, arrives after TRANSIT_STEPS_PER_TRIP steps or a rest in a cabin bed,
@ and the sailor at the exit lets you off.

	.set TRANSIT_EVENT_SOUTHERN_ISLAND, 100
	.set TRANSIT_EVENT_NAVEL_ROCK, 101
	.set TRANSIT_EVENT_BIRTH_ISLAND, 102
	.set TRANSIT_EVENT_FARAWAY_ISLAND, 103
	.set TRANSIT_MENU_CANCEL, 127

TreyTransit_EventScript_ChooseDestination::
	special TreyTransit_CheckPass
	goto_if_eq VAR_RESULT, FALSE, TreyTransit_EventScript_NoPass
	msgbox TreyTransit_Text_MayISeeYourTicket, MSGBOX_DEFAULT
TreyTransit_EventScript_ChooseAgain::
	special TreyTransit_PushDestinations
	copyvar VAR_0x8008, VAR_RESULT
	call_if_eq VAR_0x8007, 1, TreyTransit_EventScript_PushLilycoveEventIslands
	goto_if_eq VAR_0x8008, 0, TreyTransit_EventScript_NoDestinations
	message TreyTransit_Text_WhereTo
	waitmessage
	dynmultipush TreyTransit_Text_Cancel, TRANSIT_MENU_CANCEL
	dynmultistack 14, 1, FALSE, 6, FALSE, 0, NULL
	goto_if_eq VAR_RESULT, MULTI_B_PRESSED, TreyTransit_EventScript_Cancelled
	goto_if_eq VAR_RESULT, TRANSIT_MENU_CANCEL, TreyTransit_EventScript_Cancelled
	copyvar VAR_0x8006, VAR_RESULT
	goto_if_ge VAR_0x8006, TRANSIT_EVENT_SOUTHERN_ISLAND, Common_EventScript_NopReturn
	special TreyTransit_BufferStopName
	msgbox TreyTransit_Text_ItIs, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, TreyTransit_EventScript_ChooseAgain
	return

TreyTransit_EventScript_PushLilycoveEventIslands::
	@ VAR_TEMP_E/D/C/9 are set by the Lilycove clerk's ticket checks (non-zero = the ticket works)
	call_if_ne VAR_TEMP_E, 0, TreyTransit_EventScript_PushSouthernIsland
	call_if_ne VAR_TEMP_9, 0, TreyTransit_EventScript_PushNavelRock
	call_if_ne VAR_TEMP_D, 0, TreyTransit_EventScript_PushBirthIsland
	call_if_ne VAR_TEMP_C, 0, TreyTransit_EventScript_PushFarawayIsland
	return

TreyTransit_EventScript_PushSouthernIsland::
	dynmultipush TreyTransit_Text_SouthernIsland, TRANSIT_EVENT_SOUTHERN_ISLAND
	addvar VAR_0x8008, 1
	return

TreyTransit_EventScript_PushNavelRock::
	dynmultipush TreyTransit_Text_NavelRock, TRANSIT_EVENT_NAVEL_ROCK
	addvar VAR_0x8008, 1
	return

TreyTransit_EventScript_PushBirthIsland::
	dynmultipush TreyTransit_Text_BirthIsland, TRANSIT_EVENT_BIRTH_ISLAND
	addvar VAR_0x8008, 1
	return

TreyTransit_EventScript_PushFarawayIsland::
	dynmultipush TreyTransit_Text_FarawayIsland, TRANSIT_EVENT_FARAWAY_ISLAND
	addvar VAR_0x8008, 1
	return

TreyTransit_EventScript_NoPass::
	msgbox TreyTransit_Text_NeedTicket, MSGBOX_DEFAULT
	setvar VAR_0x8006, TRANSIT_STOP_NONE
	return

TreyTransit_EventScript_NoDestinations::
	msgbox TreyTransit_Text_NoOtherPorts, MSGBOX_DEFAULT
	setvar VAR_0x8006, TRANSIT_STOP_NONE
	return

TreyTransit_EventScript_Cancelled::
	msgbox TreyTransit_Text_AnotherTime, MSGBOX_DEFAULT
	setvar VAR_0x8006, TRANSIT_STOP_NONE
	return

@ On board (S.S. Tidal maps): ON_FRAME when you have just walked on.
TreyTransit_EventScript_Depart::
	special TreyTransit_Depart
	lockall
	playse SE_DING_DONG
	msgbox TreyTransit_Text_Departed, MSGBOX_DEFAULT
	releaseall
	end

@ Started by the step counter (field_control_avatar.c) when the ship comes in.
TreyTransit_EventScript_Arrived::
	lockall
	playse SE_DING_DONG
	msgbox TreyTransit_Text_Arrived, MSGBOX_DEFAULT
	releaseall
	end

@ The cabin bed, during a TREY trip (from SSTidalRooms_EventScript_Bed, after the heal).
TreyTransit_EventScript_BedRest::
	special TreyTransit_ArriveNow
	goto_if_eq VAR_RESULT, FALSE, Common_EventScript_NopReturn
	playse SE_DING_DONG
	msgbox TreyTransit_Text_Arrived, MSGBOX_DEFAULT
	return

@ The sailor at the exit, during a TREY trip.
TreyTransit_EventScript_ExitSailor::
	goto_if_ne VAR_TREY_TRANSIT_STATE, TRANSIT_STATE_ARRIVED, TreyTransit_EventScript_NotYet
	special TreyTransit_BufferDestinationName
	msgbox TreyTransit_Text_WeveArrived, MSGBOX_DEFAULT
	call_if_set FLAG_RECEIVED_TM_SNATCH, SSTidalCorridor_EventScript_HideSnatchGiver
	special TreyTransit_WarpToDestination
	waitstate
	release
	end

TreyTransit_EventScript_NotYet::
	special TreyTransit_BufferDestinationName
	msgbox TreyTransit_Text_NotYet, MSGBOX_DEFAULT
	release
	end

TreyTransit_Text_MayISeeYourTicket:
	.string "May I see your ticket, please?\p"
	.string "Thank you. Where would you like\n"
	.string "to sail to?$"

TreyTransit_Text_WhereTo:
	.string "Where would you like to go?$"

TreyTransit_Text_ItIs:
	.string "{STR_VAR_1}, then?$"

TreyTransit_Text_NeedTicket:
	.string "Welcome aboard... ah, I'm sorry.\n"
	.string "You need an S.S. TICKET to board.$"

TreyTransit_Text_NoOtherPorts:
	.string "Hmm... You haven't been to any of\n"
	.string "our other ports yet.\p"
	.string "Once you've visited one, we'll be\n"
	.string "happy to take you there.$"

TreyTransit_Text_AnotherTime:
	.string "Please sail with us another time.$"

TreyTransit_Text_Departed:
	.string "We have left port. Thank you for\n"
	.string "sailing with us to {STR_VAR_1}.\p"
	.string "Please enjoy the voyage. You may\n"
	.string "rest in your cabin until we arrive.$"

TreyTransit_Text_Arrived:
	.string "We have arrived at {STR_VAR_1}.\n"
	.string "Please make your way to the exit.$"

TreyTransit_Text_WeveArrived:
	.string "We've arrived at {STR_VAR_1}.\n"
	.string "Thank you for sailing with us!$"

TreyTransit_Text_NotYet:
	.string "We're still on our way to\n"
	.string "{STR_VAR_1}.\p"
	.string "Why not rest in your cabin until\n"
	.string "we arrive?$"

TreyTransit_Text_Cancel:
	.string "CANCEL$"

TreyTransit_Text_SouthernIsland:
	.string "SOUTHERN ISLAND$"

TreyTransit_Text_NavelRock:
	.string "NAVEL ROCK$"

TreyTransit_Text_BirthIsland:
	.string "BIRTH ISLAND$"

TreyTransit_Text_FarawayIsland:
	.string "FARAWAY ISLAND$"
