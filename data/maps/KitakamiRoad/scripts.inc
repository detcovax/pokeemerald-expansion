@ TREY (6d-3, D51): Kitakami Road, hand-built (tools/trey/kitakami_maps.py writes the layout).
@ The Kitakami bus stop (D48/D50) is the plaza at the south end (data/scripts/trey_transit.inc).

KitakamiRoad_MapScripts::
	.byte 0

KitakamiRoad_EventScript_BusDriver::
	lock
	faceplayer
	setvar VAR_0x8004, TRANSIT_BUS
	setvar VAR_0x8005, TRANSIT_STOP_MOSSUI
	setvar VAR_0x8007, 0
	setvar VAR_0x8009, LOCALID_KITAKAMI_ROAD_BUS
	setvar VAR_0x800A, LOCALID_KITAKAMI_ROAD_BUS_DRIVER
	goto TreyTransit_EventScript_BusDriver

KitakamiRoad_EventScript_RouteSign::
	msgbox KitakamiRoad_Text_RouteSign, MSGBOX_SIGN
	end

KitakamiRoad_Text_RouteSign:
	.string "KITAKAMI ROAD\n"
	.string "North: MOSSUI TOWN$"
