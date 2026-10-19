# party files are run through trainerproc, which is a tool that converts party data to an output file
# matching the current trainer .h formatting

AUTO_GEN_TARGETS += src/data/trainers.h
AUTO_GEN_TARGETS += src/data/trainers_frlg.h
AUTO_GEN_TARGETS += src/data/battle_partners.h
AUTO_GEN_TARGETS += test/battle/trainer_control.h
AUTO_GEN_TARGETS += test/battle/partner_control.h
AUTO_GEN_TARGETS += src/data/debug_trainers.h

%.h: %.party $(TRAINERPROC)
	$(CPP) $(CPPFLAGS) -traditional-cpp - < $< | $(TRAINERPROC) -o $@ -i $< -

# TREY (5d): every TREY trainer must match its tier (docs/trey/trainer_tiers.csv); the build stops otherwise.
TREY_TRAINER_CHECK_STAMP := $(OBJ_DIR)/trey/trainer_check.stamp
$(TREY_TRAINER_CHECK_STAMP): src/data/trainers.party docs/trey/trainer_tiers.csv include/constants/opponents.h include/config/trey.h tools/trey/check_trainers.py
	@python3 tools/trey/check_trainers.py
	@mkdir -p $(@D)
	@touch $@
src/data/trainers.h: $(TREY_TRAINER_CHECK_STAMP)
