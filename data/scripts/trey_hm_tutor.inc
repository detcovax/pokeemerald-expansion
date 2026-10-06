@ TREY: HM tutor (TREY_PLAN.md 5.3). Not placed on any map yet; the tutorial will use it.
@ It also tells tools/learnset_helpers/make_teachables.py that these moves are teachable, so
@ every species that can learn them (in any game) gets them in its teachable learnset.
@ Call with VAR_0x8005 already set, or use one of the entry points below.

EventScript_TreyHMTutor_Teleport::
	setvar VAR_0x8005, MOVE_TELEPORT
	goto EventScript_TreyHMTutor_Teach
EventScript_TreyHMTutor_Whirlpool::
	setvar VAR_0x8005, MOVE_WHIRLPOOL
	goto EventScript_TreyHMTutor_Teach
EventScript_TreyHMTutor_Defog::
	setvar VAR_0x8005, MOVE_DEFOG
	goto EventScript_TreyHMTutor_Teach
EventScript_TreyHMTutor_RockClimb::
	setvar VAR_0x8005, MOVE_ROCK_CLIMB
	goto EventScript_TreyHMTutor_Teach

EventScript_TreyHMTutor_Teach::
	fadescreen FADE_TO_BLACK
	special ChooseMonForMoveTutor
	waitstate
	release
	end
