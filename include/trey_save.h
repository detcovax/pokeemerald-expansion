#ifndef GUARD_TREY_SAVE_H
#define GUARD_TREY_SAVE_H

// TREY: save layout helpers (TREY_PLAN.md Section 4).

// Called from NewGameInitData: stamps the save header and clears TREY reserved space.
void TreySave_InitNewGame(void);

// TRUE if the loaded save was written with the current TREY save layout.
bool32 TreySave_IsHeaderValid(void);

#endif // GUARD_TREY_SAVE_H
