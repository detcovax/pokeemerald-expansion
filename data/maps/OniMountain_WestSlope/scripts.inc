@ TREY (6d-3, D51): Oni Mountain, west slope, hand-built (tools/trey/kitakami_maps.py writes the layout).
@ The Dreaded Den (14,4) and Ogerpon's hut (28,37) stay closed until their interiors exist (D37).

OniMountain_WestSlope_MapScripts::
	.byte 0

OniMountain_WestSlope_EventScript_Sign::
	msgbox OniMountain_WestSlope_Text_Sign, MSGBOX_SIGN
	end

OniMountain_WestSlope_Text_Sign:
	.string "ONI MOUNTAIN\n"
	.string "South: MOSSUI TOWN$"
