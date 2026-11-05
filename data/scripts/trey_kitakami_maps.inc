@ TREY (6d-3, D51): Kitakami maps (hand-built, tools/trey/kitakami_maps.py).

@ D37: doors whose interior isn't built yet.
TreyKitakami_EventScript_NotBuiltYet::
	msgbox TreyKitakami_Text_NotBuiltYet, MSGBOX_SIGN
	end

TreyKitakami_Text_NotBuiltYet:
	.string "(Not built yet.)$"

	.include "data/maps/MossuiTown/scripts.inc"
	.include "data/maps/KitakamiRoad/scripts.inc"
	.include "data/maps/OniMountain_WestSlope/scripts.inc"
