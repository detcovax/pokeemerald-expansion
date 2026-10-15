#ifndef GUARD_TREY_TRANSIT_H
#define GUARD_TREY_TRANSIT_H

// TREY (TREY_PLAN.md 5.4, Phase 4 chunk 4c): ships and trains, ridden on board. A clerk's menu lists the
// stops you have visited; you board, walk around the ship (or train), and arrive after
// TRANSIT_STEPS_PER_TRIP steps or by resting in a cabin bed. Scripts: data/scripts/trey_transit.inc.

#include "constants/trey_transit.h"

bool32 TreyTransit_IsTravelling(void);
u16 TreyTransit_GetFromStopMapsec(void); // location of the stop you departed from (region map while on board)
bool32 TreyTransit_CountStep(void);      // every step: TRUE when this step brings the ship in

// Specials (VAR_0x8004 = mode, VAR_0x8005 = this stop, VAR_0x8006 = chosen stop)
void TreyTransit_CheckPass(void);         // VAR_RESULT = has the ticket/pass for VAR_0x8004
void TreyTransit_PushDestinations(void);  // marks this stop visited, pushes the menu items, VAR_RESULT = count
void TreyTransit_BufferStopName(void);    // gStringVar1 = name of stop VAR_0x8006
void TreyTransit_Board(void);             // starts the trip VAR_0x8005 -> VAR_0x8006
void TreyTransit_Depart(void);            // on board: under way (gStringVar1 = destination)
void TreyTransit_ArriveNow(void);         // cabin bed: VAR_RESULT = TRUE if that brought the ship in
void TreyTransit_BufferDestinationName(void);
void TreyTransit_WarpToDestination(void); // use with waitstate

#endif // GUARD_TREY_TRANSIT_H
