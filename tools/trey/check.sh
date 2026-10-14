#!/usr/bin/env bash
# TREY: `make trey-check` and `make trey-check-fast`.
#   full: builds the game ROM (with the save report) and the test ROM, runs the tests.
#   fast: builds ONLY the test ROM, runs the tests, and prints the save report (which needs no ROM).
#         One build, both reports, but no playable ROM.
# Either way it prints one summary block at the end: ROM memory use (full only), save block use,
# test results, and BUILD OK.
# Builds use all CPU cores unless you already passed -j to make.
# Usage: tools/trey/check.sh "<make>" "<test filter>" [full|fast]
set -o pipefail

MAKE_CMD="${1:-make}"
TESTS="${2:-TREY}"
MODE="${3:-full}"
LOG_DIR=build/trey
mkdir -p "$LOG_DIR"
ROM_LOG="$LOG_DIR/rom.log"
TEST_LOG="$LOG_DIR/test.log"

# Parallel compile inside each build (the two builds still run one after the other: they share
# generated files in the source tree, so running both at once could corrupt them).
JOBS=""
case " ${MAKEFLAGS:-} " in
    *" -j"*|*"jobserver"*) ;;
    *) JOBS="-j$(nproc 2>/dev/null || echo 4)" ;;
esac

ROM_STATUS=0
if [ "$MODE" = "full" ]; then
    $MAKE_CMD --no-print-directory $JOBS trey-save-report 2>&1 | tee "$ROM_LOG"
    ROM_STATUS=$?
else
    : > "$ROM_LOG"
fi

TEST_STATUS=1
if [ $ROM_STATUS -eq 0 ]; then
    $MAKE_CMD --no-print-directory $JOBS check TESTS="$TESTS" 2>&1 | tee "$TEST_LOG"
    TEST_STATUS=$?
    if [ "$MODE" = "fast" ]; then
        # the test build generated every header the report needs
        $MAKE_CMD --no-print-directory trey-save-report-only 2>&1 | tee -a "$ROM_LOG"
    fi
else
    : > "$TEST_LOG"
fi

echo
echo "================================ TREY REPORT ================================"

echo
echo "ROM memory"
if [ "$MODE" = "fast" ]; then
    echo "  (fast mode: game ROM not built)"
elif grep -q "^Memory region" "$ROM_LOG"; then
    grep -A3 "^Memory region" "$ROM_LOG" | grep -v "^--"
elif [ -f pokeemerald.gba ]; then
    echo "  (ROM not relinked this run) pokeemerald.gba is $(stat -c %s pokeemerald.gba) bytes"
fi

echo
echo "Save blocks"
if grep -q "^Block " "$ROM_LOG"; then
    sed -n '/^Block /,/^flags\[\]/p' "$ROM_LOG"
else
    echo "  (no save report: the build failed)"
fi

echo
echo "Tests ($TESTS)"
if grep -qE "^- Tests" "$TEST_LOG"; then
    grep -E "^\[[0-9]+\] " "$TEST_LOG" | sed -E 's/^\[[0-9]+\] //' | sort | sed 's/^/  /'
    echo
    grep -E "^- Tests" "$TEST_LOG"
elif [ $ROM_STATUS -ne 0 ]; then
    echo "  (not run: the ROM build failed)"
else
    echo "  (no test results: the test build failed)"
fi

echo
if [ $ROM_STATUS -eq 0 ] && [ $TEST_STATUS -eq 0 ]; then
    if [ "$MODE" = "fast" ]; then
        echo "BUILD OK (fast: tests + save report only, no playable ROM)"
    else
        echo "BUILD OK"
    fi
    exit 0
fi

if [ $ROM_STATUS -ne 0 ]; then
    echo "BUILD FAILED: game ROM. Errors:"
    grep -E "error|Error" "$ROM_LOG" | tail -n 20 | sed 's/^/  /'
else
    echo "BUILD FAILED: tests. Details:"
    grep -E "FAIL|error|Error" "$TEST_LOG" | tail -n 20 | sed 's/^/  /'
fi
echo "Full logs: $ROM_LOG and $TEST_LOG"
exit 1
