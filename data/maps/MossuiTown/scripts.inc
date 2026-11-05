@ TREY (6d-3, D51): Mossui Town, hand-built (tools/trey/kitakami_maps.py writes the layout). Story comes later.

MossuiTown_MapScripts::
	.byte 0

MossuiTown_EventScript_TownSign::
	msgbox MossuiTown_Text_TownSign, MSGBOX_SIGN
	end

MossuiTown_EventScript_Signboard::
	msgbox MossuiTown_Text_Signboard, MSGBOX_SIGN
	end

MossuiTown_Text_TownSign:
	.string "MOSSUI TOWN\n"
	.string "A quiet village at the foot of\l"
	.string "ONI MOUNTAIN.$"

MossuiTown_Text_Signboard:
	.string "It's an old signboard. It tells a\n"
	.string "tale of the ogre of ONI MOUNTAIN\l"
	.string "and the LOYAL THREE.$"
