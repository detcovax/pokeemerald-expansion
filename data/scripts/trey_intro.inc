@ TREY (5b, TREY_PLAN.md D27): placeholder new-game intro and Kanto's first-arrival script.

@ Runs on the first field frame of a new game (src/trey_intro.c), in the player's room in Pallet Town.
TreyIntro_EventScript_NewGame::
	lockall
	msgbox TreyIntro_Text_Welcome, MSGBOX_DEFAULT
	msgbox TreyIntro_Text_BoyOrGirl, MSGBOX_DEFAULT
	dynmultichoice 0, 0, TRUE, 2, 0, DYN_MULTICHOICE_CB_NONE, gText_Boy, gText_Girl
	special TreyIntro_SetGender
	closemessage
	msgbox TreyIntro_Text_WhatsYourName, MSGBOX_DEFAULT
	closemessage
	fadescreen FADE_TO_BLACK
	special TreyIntro_NamePlayer
	waitstate
	special TreyIntro_FinishNaming
	setrespawn HEAL_LOCATION_PALLET_TOWN
	givemon SPECIES_MEW, TREY_INTRO_MEW_LEVEL
	setflag FLAG_SYS_POKEMON_GET @ shows POKéMON in the start menu (normally set by the starter event)
	playfanfare MUS_OBTAIN_ITEM
	msgbox TreyIntro_Text_ReceivedMew, MSGBOX_DEFAULT
	waitfanfare
	msgbox TreyIntro_Text_GoodLuck, MSGBOX_DEFAULT
	releaseall
	end

@ First arrival in Kanto (src/trey_dex.c, sArrivalScripts). In a new game this runs right after the intro.
TreyKanto_EventScript_Arrival::
	setqueststage QUEST_KANTO_STORY, 1
	end

TreyIntro_Text_Welcome:
	.string "Welcome to the world of POKéMON TREY!\p"
	.string "This is a placeholder intro for the\n"
	.string "vertical slice.$"

TreyIntro_Text_BoyOrGirl:
	.string "Are you a boy or a girl?$"

TreyIntro_Text_WhatsYourName:
	.string "And what is your name?$"

TreyIntro_Text_ReceivedMew:
	.string "{PLAYER} received a MEW!$"

TreyIntro_Text_GoodLuck:
	.string "Your adventure starts here in\n"
	.string "PALLET TOWN. Good luck, {PLAYER}!$"
